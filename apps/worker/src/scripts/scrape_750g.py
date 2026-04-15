"""Scraper de recettes depuis 750g.com et Allrecipes FR vers PostgreSQL Supabase.

Extraction des recettes via parsing JSON-LD (schema.org Recipe), normalisation
et insertion idempotente dans le schema DB (recipes / ingredients / recipe_ingredients).

Pipeline :
1. Decouverte des URLs de recettes (sitemap XML ou pagination par categorie)
2. Extraction JSON-LD schema.org Recipe pour chaque page
3. Parsing des ingredients FR ("200 g de farine" -> qty=200, unit="g", name="farine")
4. Tags automatiques (regime, categorie, budget)
5. Insertion DB avec upsert sur slug / source_url

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://... \\
    uv run python -m src.scripts.scrape_750g

Variables d'environnement :
    DATABASE_URL    Obligatoire -- connexion PostgreSQL async (asyncpg).
    DRY_RUN         Optionnel -- "true" pour simuler sans ecriture en base.
    MAX_RECIPES     Optionnel -- nombre max de recettes a importer (defaut : 2000).
    LOG_LEVEL       Optionnel -- DEBUG/INFO/WARNING (defaut : INFO).
    SCRAPE_DELAY    Optionnel -- delai entre chaque requete en secondes (defaut : 2.0).
    SOURCE_SITES    Optionnel -- sites a scraper, separes par virgule (defaut : "750g").
                    Valeurs : "750g", "allrecipes", "750g,allrecipes".
"""

import asyncio
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from typing import Any
from uuid import uuid4

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

QUALITY_SCORE_DEFAULT = 0.85
INGREDIENT_CATEGORY_DEFAULT = "other"

# Headers HTTP realistes pour eviter le blocage par les sites
DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}

# ---------------------------------------------------------------------------
# Configuration des sites
# ---------------------------------------------------------------------------

SITE_CONFIGS: dict[str, dict[str, Any]] = {
    "750g": {
        "base_url": "https://www.750g.com",
        "source_name": "750g",
        "sitemap_urls": [
            "https://www.750g.com/sitemap-recipes.xml",
            "https://www.750g.com/sitemap.xml",
        ],
        "categories": [
            "/recettes_plats.htm",
            "/recettes_entrees.htm",
            "/recettes_desserts.htm",
            "/recettes_soupes.htm",
            "/recettes_salades.htm",
            "/recettes_aperitifs.htm",
            "/recettes_accompagnements.htm",
            "/recettes_boissons.htm",
            "/recettes_sauces.htm",
            "/recettes_patisseries.htm",
            "/recettes_pains.htm",
            "/recettes_brunch.htm",
            "/recettes_petit_dejeuner.htm",
        ],
        "pagination_param": "page",
        "max_pages_per_category": 50,
    },
    "allrecipes": {
        "base_url": "https://www.allrecipes.com",
        "source_name": "allrecipes",
        "sitemap_urls": [
            "https://www.allrecipes.com/sitemap.xml",
        ],
        "categories": [
            "/recipes/17562/lunch/",
            "/recipes/17561/lunch/main-dishes/",
            "/recipes/76/appetizers-and-snacks/",
            "/recipes/79/desserts/",
            "/recipes/94/soups-stews-and-chili/",
            "/recipes/96/salad/",
            "/recipes/1642/everyday-cooking/quick-and-easy/",
            "/recipes/86/world-cuisine/european/french/",
            "/recipes/233/world-cuisine/european/italian/",
            "/recipes/15436/world-cuisine/asian/japanese/",
        ],
        "pagination_param": "page",
        "max_pages_per_category": 30,
    },
}

# Mapping des categories de page vers les tags
CATEGORY_TAG_MAP: dict[str, str] = {
    "plats": "plat",
    "entrees": "entree",
    "desserts": "dessert",
    "soupes": "soupe",
    "salades": "salade",
    "aperitifs": "aperitif",
    "accompagnements": "accompagnement",
    "patisseries": "dessert",
    "pains": "accompagnement",
    "brunch": "brunch",
    "petit_dejeuner": "petit-dejeuner",
    "main-dishes": "plat",
    "appetizers": "entree",
    "snacks": "aperitif",
    "soups": "soupe",
    "quick-and-easy": "rapide",
    "french": "cuisine-francaise",
    "italian": "cuisine-italienne",
    "japanese": "cuisine-japonaise",
}


# ---------------------------------------------------------------------------
# Helpers -- Slugify et HTML
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convertit un titre en slug URL-safe.

    Exemple : "Poulet roti a l'ail" -> "poulet-roti-a-l-ail"
    """
    slug = text.lower()
    accent_map: dict[str, str] = {
        "\u00e9": "e",
        "\u00e8": "e",
        "\u00ea": "e",
        "\u00eb": "e",
        "\u00e0": "a",
        "\u00e2": "a",
        "\u00e4": "a",
        "\u00f9": "u",
        "\u00fb": "u",
        "\u00fc": "u",
        "\u00f4": "o",
        "\u00f6": "o",
        "\u00ee": "i",
        "\u00ef": "i",
        "\u00e7": "c",
        "\u0153": "oe",
        "\u00e6": "ae",
    }
    for char, replacement in accent_map.items():
        slug = slug.replace(char, replacement)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:120]


def _strip_html(text: str) -> str:
    """Retire les balises HTML et normalise les espaces."""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    clean = clean.replace("&nbsp;", " ").replace("&eacute;", "\u00e9")
    clean = clean.replace("&egrave;", "\u00e8").replace("&agrave;", "\u00e0")
    return " ".join(clean.split()).strip()


# ---------------------------------------------------------------------------
# Parsing des ingredients FR
# ---------------------------------------------------------------------------

# Unites francaises reconnues (singulier et pluriel)
_FR_UNITS: dict[str, str] = {
    "g": "g",
    "gr": "g",
    "gramme": "g",
    "grammes": "g",
    "kg": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogramme": "kg",
    "kilogrammes": "kg",
    "mg": "mg",
    "milligramme": "mg",
    "milligrammes": "mg",
    "l": "l",
    "litre": "l",
    "litres": "l",
    "dl": "dl",
    "decilitre": "dl",
    "decilitres": "dl",
    "cl": "cl",
    "centilitre": "cl",
    "centilitres": "cl",
    "ml": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "c.": "cas",
    "cs": "cas",
    "c.s": "cas",
    "c.s.": "cas",
    "cuillere a soupe": "cas",
    "cuilleres a soupe": "cas",
    "cuill\u00e8re \u00e0 soupe": "cas",
    "cuill\u00e8res \u00e0 soupe": "cas",
    "c.c": "cac",
    "c.c.": "cac",
    "cc": "cac",
    "cuillere a cafe": "cac",
    "cuilleres a cafe": "cac",
    "cuill\u00e8re \u00e0 caf\u00e9": "cac",
    "cuill\u00e8res \u00e0 caf\u00e9": "cac",
    "tasse": "tasse",
    "tasses": "tasse",
    "verre": "verre",
    "verres": "verre",
    "pincee": "pinc\u00e9e",
    "pinc\u00e9e": "pinc\u00e9e",
    "pincees": "pinc\u00e9e",
    "pinc\u00e9es": "pinc\u00e9e",
    "sachet": "sachet",
    "sachets": "sachet",
    "paquet": "paquet",
    "paquets": "paquet",
    "tranche": "tranche",
    "tranches": "tranche",
    "feuille": "feuille",
    "feuilles": "feuille",
    "botte": "botte",
    "bottes": "botte",
    "branche": "branche",
    "branches": "branche",
    "gousse": "gousse",
    "gousses": "gousse",
    "brin": "brin",
    "brins": "brin",
    "pot": "pot",
    "pots": "pot",
    "bo\u00eete": "bo\u00eete",
    "boite": "bo\u00eete",
    "bo\u00eetes": "bo\u00eete",
    "morceau": "morceau",
    "morceaux": "morceau",
    "noix": "noix",
    "filet": "filet",
    "filets": "filet",
    "bouquet": "bouquet",
    "bouquets": "bouquet",
    "barquette": "barquette",
    "barquettes": "barquette",
}

# Regex pour extraire la quantite numerique en debut de ligne
# Capture : entiers, decimaux (virgule ou point), fractions, fractions unicode
_LEADING_QTY_RE = re.compile(
    r"^([\d\u00bc\u00bd\u00be\u2153\u2154]+(?:[,./]\d+)?(?:\s+\d+/\d+)?)\s*"
)

# Articles FR a retirer entre l'unite et le nom de l'ingredient
_ARTICLE_RE = re.compile(
    r"^(?:de\s+|d['\u2019]\s*|du\s+|des\s+|la\s+|le\s+|les\s+|l['\u2019]\s*)",
    re.IGNORECASE,
)

# Construire une liste d'unites triees par longueur decroissante pour match greedy
_FR_UNITS_SORTED: list[tuple[str, str]] = sorted(
    _FR_UNITS.items(), key=lambda x: len(x[0]), reverse=True
)

# Fractions unicode
_FRACTION_MAP: dict[str, float] = {
    "\u00bd": 0.5,  # 1/2
    "\u2153": 0.333,  # 1/3
    "\u2154": 0.667,  # 2/3
    "\u00bc": 0.25,  # 1/4
    "\u00be": 0.75,  # 3/4
}


def _parse_fraction(text: str) -> float:
    """Parse une quantite qui peut contenir des fractions.

    Exemples :
        "200"     -> 200.0
        "1/2"     -> 0.5
        "1 1/2"   -> 1.5
        "0,5"     -> 0.5
    """
    text = text.strip()

    # Fractions unicode
    for fchar, fval in _FRACTION_MAP.items():
        if fchar in text:
            prefix = text.replace(fchar, "").strip()
            if prefix:
                try:
                    return float(prefix.replace(",", ".")) + fval
                except ValueError:
                    return fval
            return fval

    # Virgule decimale francaise
    text = text.replace(",", ".")

    # Fraction textuelle : "1/2", "3/4"
    frac_match = re.match(r"^(\d+)\s+(\d+)/(\d+)$", text)
    if frac_match:
        whole = int(frac_match.group(1))
        return whole + float(Fraction(int(frac_match.group(2)), int(frac_match.group(3))))

    frac_simple = re.match(r"^(\d+)/(\d+)$", text)
    if frac_simple:
        return float(Fraction(int(frac_simple.group(1)), int(frac_simple.group(2))))

    try:
        return float(text)
    except ValueError:
        return 1.0


def parse_ingredient_line(line: str) -> tuple[float, str, str]:
    """Parse une ligne d'ingredient francais en (quantity, unit, canonical_name).

    Exemples :
        "200 g de farine"     -> (200.0, "g", "farine")
        "3 oeufs"             -> (3.0, "piece", "oeuf")
        "1/2 citron"          -> (0.5, "piece", "citron")
        "sel, poivre"         -> (1.0, "piece", "sel, poivre")
    """
    line = line.strip()
    if not line:
        return 1.0, "pi\u00e8ce", "ingr\u00e9dient inconnu"

    # Retirer les annotations entre parentheses a la fin
    line_clean = re.sub(r"\s*\([^)]*\)\s*$", "", line).strip()
    if not line_clean:
        line_clean = line

    # Etape 1 : Extraire la quantite numerique en debut de ligne
    qty_match = _LEADING_QTY_RE.match(line_clean)
    if not qty_match:
        # Pas de quantite detectable -- l'ingredient entier est le nom
        return 1.0, "pi\u00e8ce", _normalize_ingredient_name(line_clean)

    qty_str = qty_match.group(1).strip()
    quantity = _parse_fraction(qty_str)
    if quantity <= 0:
        quantity = 1.0

    # Le reste apres la quantite
    remainder = line_clean[qty_match.end() :].strip()
    if not remainder:
        return quantity, "pi\u00e8ce", "ingr\u00e9dient inconnu"

    # Etape 2 : Tenter de matcher une unite connue au debut du remainder
    unit = "pi\u00e8ce"
    remainder_lower = remainder.lower()

    for known_unit, canonical_unit in _FR_UNITS_SORTED:
        if remainder_lower.startswith(known_unit):
            # Verifier que c'est un mot complet (suivi d'espace, fin de chaine, ou ponctuation)
            after = remainder_lower[len(known_unit) :]
            if not after or after[0] in (" ", ".", ",", ";", "\t"):
                unit = canonical_unit
                remainder = remainder[len(known_unit) :].strip()
                break

    # Etape 3 : Retirer les articles FR entre l'unite et le nom
    remainder = _ARTICLE_RE.sub("", remainder).strip()

    canonical_name = _normalize_ingredient_name(remainder)
    if not canonical_name:
        canonical_name = "ingr\u00e9dient inconnu"

    return quantity, unit, canonical_name


def _normalize_ingredient_name(name: str) -> str:
    """Normalise un nom d'ingredient (minuscule, espaces, nettoyage)."""
    name = name.lower().strip()
    # Retirer les articles en debut
    name = re.sub(r"^(de\s+|d['\u2019]\s*|du\s+|des\s+|la\s+|le\s+|les\s+|l['\u2019]\s*)", "", name)
    # Retirer la ponctuation finale
    name = name.rstrip(".,;:")
    # Normaliser les espaces
    name = " ".join(name.split())
    return name[:100]


# ---------------------------------------------------------------------------
# Extraction JSON-LD (schema.org Recipe)
# ---------------------------------------------------------------------------


def extract_jsonld_recipe(html: str) -> dict[str, Any] | None:
    """Extrait la premiere structure JSON-LD de type Recipe d'une page HTML.

    Compatible avec le standard schema.org/Recipe utilise par 750g, Allrecipes,
    Marmiton et la plupart des sites de recettes.

    Returns:
        Dict JSON-LD de la recette ou None si non trouve.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        # Peut etre un objet unique ou une liste
        candidates: list[dict[str, Any]] = []
        if isinstance(data, list):
            candidates.extend(data)
        elif isinstance(data, dict):
            # Peut etre un @graph
            if "@graph" in data:
                candidates.extend(data["@graph"])
            else:
                candidates.append(data)

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            schema_type = candidate.get("@type", "")
            # @type peut etre une string ou une liste
            if isinstance(schema_type, list):
                if "Recipe" in schema_type:
                    return candidate
            elif schema_type == "Recipe":
                return candidate

    return None


def _parse_iso_duration(duration: str | None) -> int:
    """Parse une duree ISO 8601 (PT30M, PT1H15M) en minutes.

    Exemples :
        "PT30M"    -> 30
        "PT1H15M"  -> 75
        "PT2H"     -> 120
        "PT45S"    -> 1
    """
    if not duration:
        return 0

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration, re.IGNORECASE)
    if not match or not any(match.groups()):
        # Essayer le format "1h30", "1h30min", "30 min", "2h"
        hm_match = re.match(r"(\d+)\s*h\s*(\d+)", duration, re.IGNORECASE)
        if hm_match:
            return int(hm_match.group(1)) * 60 + int(hm_match.group(2))
        hours_match = re.search(r"(\d+)\s*h", duration, re.IGNORECASE)
        mins_match = re.search(r"(\d+)\s*(?:min|mn)", duration, re.IGNORECASE)
        total = 0
        if hours_match:
            total += int(hours_match.group(1)) * 60
        if mins_match:
            total += int(mins_match.group(1))
        return total

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 60 + minutes + (1 if seconds > 0 else 0)


def _extract_instructions_from_jsonld(
    recipe_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extrait les instructions depuis le JSON-LD au format interne.

    Gere les formats schema.org courants :
    - Liste de strings
    - Liste de HowToStep objects
    - Liste de HowToSection avec HowToStep imbriques
    - String unique
    """
    instructions: list[dict[str, Any]] = []
    raw = recipe_data.get("recipeInstructions")

    if not raw:
        return instructions

    if isinstance(raw, str):
        # Texte brut -- decouper sur les points ou retours a la ligne
        clean = _strip_html(raw)
        sentences = re.split(r"(?:\.\s+|\n+)", clean)
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip(" .")
            if sentence and len(sentence) > 5:
                instructions.append({"step": i + 1, "text": sentence})
        return instructions[:15]

    if isinstance(raw, list):
        step_num = 0
        for item in raw:
            if isinstance(item, str):
                clean = _strip_html(item).strip()
                if clean and len(clean) > 3:
                    step_num += 1
                    instructions.append({"step": step_num, "text": clean})
            elif isinstance(item, dict):
                item_type = item.get("@type", "")
                if item_type == "HowToSection":
                    # Section contenant des sous-etapes
                    sub_items = item.get("itemListElement") or []
                    for sub in sub_items:
                        text = ""
                        if isinstance(sub, str):
                            text = _strip_html(sub).strip()
                        elif isinstance(sub, dict):
                            text = _strip_html(sub.get("text") or "").strip()
                        if text and len(text) > 3:
                            step_num += 1
                            instructions.append({"step": step_num, "text": text})
                else:
                    # HowToStep ou objet generique
                    text = _strip_html(item.get("text") or "").strip()
                    if text and len(text) > 3:
                        step_num += 1
                        instructions.append({"step": step_num, "text": text})

    return instructions[:15]


def _extract_ingredients_from_jsonld(
    recipe_data: dict[str, Any],
) -> list[str]:
    """Extrait la liste brute des ingredients depuis le JSON-LD.

    Returns:
        Liste de strings brutes ("200 g de farine", "3 oeufs", etc.).
    """
    raw = recipe_data.get("recipeIngredient") or []
    if isinstance(raw, str):
        return [raw]
    return [_strip_html(str(item)).strip() for item in raw if item]


def _extract_image_url(recipe_data: dict[str, Any]) -> str:
    """Extrait la meilleure URL d'image depuis le JSON-LD."""
    image = recipe_data.get("image")
    if not image:
        return ""
    if isinstance(image, str):
        return image
    if isinstance(image, list):
        # Prendre la plus grande image (souvent la derniere)
        return str(image[-1]) if image else ""
    if isinstance(image, dict):
        return image.get("url") or image.get("contentUrl") or ""
    return ""


def _extract_servings(recipe_data: dict[str, Any]) -> int:
    """Extrait le nombre de portions depuis le JSON-LD."""
    yield_val = recipe_data.get("recipeYield")
    if not yield_val:
        return 4
    if isinstance(yield_val, int):
        return max(1, yield_val)
    if isinstance(yield_val, list):
        yield_val = yield_val[0] if yield_val else "4"
    yield_str = str(yield_val)
    # Extraire le premier nombre
    match = re.search(r"(\d+)", yield_str)
    if match:
        return max(1, int(match.group(1)))
    return 4


def _extract_nutrition_jsonld(recipe_data: dict[str, Any]) -> dict[str, Any] | None:
    """Extrait les donnees nutritionnelles depuis le JSON-LD si presentes."""
    nutrition = recipe_data.get("nutrition")
    if not nutrition or not isinstance(nutrition, dict):
        return None

    def _parse_value(key: str) -> float | None:
        val = nutrition.get(key)
        if val is None:
            return None
        val_str = str(val)
        match = re.search(r"([\d.,]+)", val_str)
        if match:
            return float(match.group(1).replace(",", "."))
        return None

    result: dict[str, Any] = {}
    cal = _parse_value("calories")
    if cal is not None:
        result["calories"] = round(cal)
    protein = _parse_value("proteinContent")
    if protein is not None:
        result["protein_g"] = round(protein, 1)
    fat = _parse_value("fatContent")
    if fat is not None:
        result["fat_g"] = round(fat, 1)
    carbs = _parse_value("carbohydrateContent")
    if carbs is not None:
        result["carbs_g"] = round(carbs, 1)
    fiber = _parse_value("fiberContent")
    if fiber is not None:
        result["fiber_g"] = round(fiber, 1)
    sugar = _parse_value("sugarContent")
    if sugar is not None:
        result["sugar_g"] = round(sugar, 1)
    sodium = _parse_value("sodiumContent")
    if sodium is not None:
        result["sodium_mg"] = round(sodium, 1)

    return result if result else None


# ---------------------------------------------------------------------------
# Normalisation recipe JSON-LD -> schema DB
# ---------------------------------------------------------------------------


def map_difficulty_from_time_and_steps(prep_min: int, cook_min: int, nb_steps: int) -> int:
    """Calcule la difficulte 1-5 basee sur le temps total et le nombre d'etapes."""
    total = prep_min + cook_min
    if total <= 15 and nb_steps <= 3:
        return 1
    if total <= 30 and nb_steps <= 5:
        return 2
    if total <= 60:
        return 3
    if total <= 120:
        return 4
    return 5


def build_tags_from_jsonld(
    recipe_data: dict[str, Any],
    category_hint: str = "",
) -> list[str]:
    """Construit les tags depuis les metadonnees JSON-LD et la categorie de page."""
    tags: list[str] = []

    # Categorie schema.org
    category = recipe_data.get("recipeCategory")
    if category:
        if isinstance(category, list):
            for cat in category:
                cat_lower = str(cat).lower()
                if "dessert" in cat_lower:
                    tags.append("dessert")
                elif "entr" in cat_lower or "starter" in cat_lower:
                    tags.append("entree")
                elif "plat" in cat_lower or "main" in cat_lower:
                    tags.append("plat")
                elif "soupe" in cat_lower or "soup" in cat_lower:
                    tags.append("soupe")
        elif isinstance(category, str):
            cat_lower = category.lower()
            if "dessert" in cat_lower:
                tags.append("dessert")
            elif "entr" in cat_lower or "starter" in cat_lower:
                tags.append("entree")
            elif "plat" in cat_lower or "main" in cat_lower:
                tags.append("plat")
            elif "soupe" in cat_lower or "soup" in cat_lower:
                tags.append("soupe")

    # Keywords schema.org
    keywords = recipe_data.get("keywords")
    if keywords:
        if isinstance(keywords, str):
            kw_list = [k.strip().lower() for k in keywords.split(",")]
        elif isinstance(keywords, list):
            kw_list = [str(k).strip().lower() for k in keywords]
        else:
            kw_list = []

        for kw in kw_list:
            if "vegan" in kw:
                tags.append("vegan")
            if "v\u00e9g\u00e9tarien" in kw or "vegetarian" in kw:
                tags.append("v\u00e9g\u00e9tarien")
            if "sans gluten" in kw or "gluten-free" in kw or "gluten free" in kw:
                tags.append("sans-gluten")
            if "sans lactose" in kw or "dairy-free" in kw or "dairy free" in kw:
                tags.append("sans-lactose")
            if "rapide" in kw or "quick" in kw or "express" in kw:
                tags.append("rapide")
            if "facile" in kw or "easy" in kw:
                tags.append("facile")
            if "\u00e9conomique" in kw or "budget" in kw or "pas cher" in kw:
                tags.append("\u00e9conomique")

    # Tag depuis la categorie de la page source
    if category_hint:
        for pattern, tag in CATEGORY_TAG_MAP.items():
            if pattern in category_hint.lower() and tag not in tags:
                tags.append(tag)

    # Temps
    prep = _parse_iso_duration(recipe_data.get("prepTime"))
    cook = _parse_iso_duration(recipe_data.get("cookTime"))
    total_time = _parse_iso_duration(recipe_data.get("totalTime")) or (prep + cook)
    if 0 < total_time <= 30 and "rapide" not in tags:
        tags.append("rapide")

    # Suit le pattern de recipe_data.get("suitableForDiet")
    diets = recipe_data.get("suitableForDiet") or []
    if isinstance(diets, str):
        diets = [diets]
    for diet in diets:
        diet_lower = str(diet).lower()
        if "vegan" in diet_lower and "vegan" not in tags:
            tags.append("vegan")
        if "vegetarian" in diet_lower and "v\u00e9g\u00e9tarien" not in tags:
            tags.append("v\u00e9g\u00e9tarien")
        if "gluten" in diet_lower and "sans-gluten" not in tags:
            tags.append("sans-gluten")

    # Categorie par defaut si aucune n'a ete trouvee
    if not any(
        t in tags
        for t in (
            "plat",
            "dessert",
            "entree",
            "soupe",
            "salade",
            "aperitif",
            "accompagnement",
            "petit-dejeuner",
            "brunch",
        )
    ):
        tags.append("plat")

    tags.append("quotidien")

    return list(set(tags))


def normalize_jsonld_recipe(
    recipe_data: dict[str, Any],
    source_name: str,
    source_url: str,
    category_hint: str = "",
) -> dict[str, Any]:
    """Normalise une recette JSON-LD schema.org vers le schema DB interne.

    Ne leve jamais d'exception -- les champs manquants sont remplaces
    par des valeurs par defaut securisees.
    """
    title = _strip_html(str(recipe_data.get("name") or "Recette sans titre")).strip()
    slug_base = _slugify(title)
    # Ajouter un hash court de l'URL source pour garantir l'unicite
    url_hash = hex(abs(hash(source_url)))[-8:]
    slug = f"{slug_base}-{url_hash}" if slug_base else f"recette-{url_hash}"

    description = ""
    desc_raw = recipe_data.get("description") or ""
    if desc_raw:
        description = _strip_html(str(desc_raw))[:500]

    prep_time = _parse_iso_duration(recipe_data.get("prepTime"))
    cook_time = _parse_iso_duration(recipe_data.get("cookTime"))
    total_time = _parse_iso_duration(recipe_data.get("totalTime"))

    # Si seulement totalTime est fourni, repartir en prep/cook
    if total_time > 0 and prep_time == 0 and cook_time == 0:
        prep_time = total_time // 3
        cook_time = total_time - prep_time
    elif prep_time == 0 and cook_time == 0:
        cook_time = 30  # Defaut raisonnable

    instructions = _extract_instructions_from_jsonld(recipe_data)
    servings = _extract_servings(recipe_data)
    tags = build_tags_from_jsonld(recipe_data, category_hint)
    nutrition = _extract_nutrition_jsonld(recipe_data)

    # Cuisine -- defaut "francaise" pour les sites FR
    cuisine_type = "fran\u00e7aise"
    cuisine_raw = recipe_data.get("recipeCuisine")
    if cuisine_raw:
        if isinstance(cuisine_raw, list):
            cuisine_raw = cuisine_raw[0] if cuisine_raw else ""
        cuisine_lower = str(cuisine_raw).lower()
        cuisine_map: dict[str, str] = {
            "french": "fran\u00e7aise",
            "fran\u00e7aise": "fran\u00e7aise",
            "italian": "italienne",
            "italienne": "italienne",
            "japanese": "japonaise",
            "japonaise": "japonaise",
            "mexican": "mexicaine",
            "mexicaine": "mexicaine",
            "indian": "indienne",
            "indienne": "indienne",
            "thai": "tha\u00eflandaise",
            "tha\u00eflandaise": "tha\u00eflandaise",
            "chinese": "chinoise",
            "chinoise": "chinoise",
            "mediterranean": "m\u00e9diterran\u00e9enne",
            "m\u00e9diterran\u00e9enne": "m\u00e9diterran\u00e9enne",
            "korean": "cor\u00e9enne",
            "cor\u00e9enne": "cor\u00e9enne",
            "moroccan": "marocaine",
            "marocaine": "marocaine",
            "spanish": "espagnole",
            "espagnole": "espagnole",
            "greek": "grecque",
            "grecque": "grecque",
            "lebanese": "libanaise",
            "libanaise": "libanaise",
            "american": "am\u00e9ricaine",
            "am\u00e9ricaine": "am\u00e9ricaine",
        }
        for pattern, mapped in cuisine_map.items():
            if pattern in cuisine_lower:
                cuisine_type = mapped
                break

    # Difficulte
    difficulty = map_difficulty_from_time_and_steps(prep_time, cook_time, len(instructions))

    return {
        "title": title,
        "slug": slug,
        "source": source_name,
        "source_url": source_url,
        "description": description,
        "photo_url": _extract_image_url(recipe_data),
        "servings": servings,
        "prep_time_min": prep_time,
        "cook_time_min": cook_time,
        "difficulty": difficulty,
        "cuisine_type": cuisine_type,
        "tags": tags,
        "quality_score": QUALITY_SCORE_DEFAULT,
        "instructions": instructions,
        "nutrition": nutrition,
        "language": "fr",
    }


# ---------------------------------------------------------------------------
# Filtrage qualite
# ---------------------------------------------------------------------------


def passes_quality_filter(recipe_data: dict[str, Any], normalized: dict[str, Any]) -> bool:
    """Rejette les recettes qui ne respectent pas nos criteres de qualite.

    Criteres :
    - Titre non vide et > 3 caracteres
    - Au moins 2 ingredients
    - Au moins 1 etape d'instruction
    - Photo presente (optionnel mais prefere)
    """
    if len(normalized["title"]) < 4:
        return False

    ingredients = _extract_ingredients_from_jsonld(recipe_data)
    if len(ingredients) < 2:
        return False

    return bool(normalized["instructions"])


# ---------------------------------------------------------------------------
# Decouverte des URLs de recettes
# ---------------------------------------------------------------------------


async def discover_urls_from_sitemap(
    client: httpx.AsyncClient,
    sitemap_url: str,
    max_urls: int,
    scrape_delay: float,
) -> list[str]:
    """Tente de decouvrir les URLs de recettes via un sitemap XML.

    Gere les sitemaps index (contenant d'autres sitemaps) et les sitemaps finaux.

    Returns:
        Liste d'URLs de recettes trouvees.
    """
    urls: list[str] = []

    try:
        response = await client.get(sitemap_url, timeout=30)
        if response.status_code != 200:
            logger.debug("sitemap_not_found", url=sitemap_url, status=response.status_code)
            return urls

        content = response.text
        root = ET.fromstring(content)

        # Namespace XML de sitemap
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Verifier si c'est un sitemap index
        sitemap_refs = root.findall(".//sm:sitemap/sm:loc", ns)
        if sitemap_refs:
            logger.info("sitemap_index_found", count=len(sitemap_refs), url=sitemap_url)
            for ref in sitemap_refs:
                if len(urls) >= max_urls:
                    break
                ref_url = (ref.text or "").strip()
                if not ref_url:
                    continue
                # Filtrer les sitemaps de recettes
                if "recipe" in ref_url.lower() or "recette" in ref_url.lower():
                    await asyncio.sleep(scrape_delay)
                    sub_urls = await discover_urls_from_sitemap(
                        client, ref_url, max_urls - len(urls), scrape_delay
                    )
                    urls.extend(sub_urls)
            return urls[:max_urls]

        # Sitemap final -- extraire les URLs
        loc_elements = root.findall(".//sm:url/sm:loc", ns)
        for loc in loc_elements:
            if len(urls) >= max_urls:
                break
            url = (loc.text or "").strip()
            if url and _is_recipe_url(url):
                urls.append(url)

        logger.info("sitemap_urls_found", count=len(urls), source=sitemap_url)

    except ET.ParseError:
        logger.warning("sitemap_parse_error", url=sitemap_url)
    except httpx.HTTPError as exc:
        logger.warning("sitemap_http_error", url=sitemap_url, error=str(exc))
    except Exception as exc:
        logger.warning("sitemap_error", url=sitemap_url, error=str(exc))

    return urls[:max_urls]


def _is_recipe_url(url: str) -> bool:
    """Heuristique pour detecter si une URL est une page de recette individuelle."""
    url_lower = url.lower()
    # 750g : les recettes ont un format type /poulet-roti_12345.htm
    if "750g.com" in url_lower:
        return bool(re.search(r"_\d+\.htm", url_lower))
    # Allrecipes : /recipe/12345/
    if "allrecipes.com" in url_lower:
        return "/recipe/" in url_lower or "/recette/" in url_lower
    # Generique
    return "recette" in url_lower or "recipe" in url_lower


async def discover_urls_from_categories(
    client: httpx.AsyncClient,
    site_config: dict[str, Any],
    max_urls: int,
    scrape_delay: float,
) -> list[str]:
    """Decouvre les URLs de recettes en parcourant les categories paginées.

    Parcourt chaque categorie configuree page par page et extrait les liens
    vers les pages de recettes individuelles.

    Returns:
        Liste d'URLs de recettes uniques.
    """
    from bs4 import BeautifulSoup

    base_url = site_config["base_url"]
    categories = site_config["categories"]
    max_pages = site_config.get("max_pages_per_category", 50)
    pagination_param = site_config.get("pagination_param", "page")

    seen_urls: set[str] = set()
    urls: list[str] = []

    for category_path in categories:
        if len(urls) >= max_urls:
            break

        for page_num in range(1, max_pages + 1):
            if len(urls) >= max_urls:
                break

            # Construire l'URL de listing paginee
            if page_num == 1:
                listing_url = f"{base_url}{category_path}"
            else:
                separator = "&" if "?" in category_path else "?"
                listing_url = f"{base_url}{category_path}{separator}{pagination_param}={page_num}"

            await asyncio.sleep(scrape_delay)

            try:
                response = await client.get(listing_url, timeout=30, follow_redirects=True)
                if response.status_code != 200:
                    logger.debug(
                        "listing_page_error",
                        url=listing_url,
                        status=response.status_code,
                    )
                    break  # Plus de pages

                soup = BeautifulSoup(response.text, "html.parser")
                page_urls: list[str] = []

                # Extraire tous les liens de la page
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    # Convertir en URL absolue
                    if href.startswith("/"):
                        href = f"{base_url}{href}"
                    elif not href.startswith("http"):
                        continue

                    # Verifier si c'est une URL de recette et si on ne l'a pas deja vue
                    if _is_recipe_url(href) and href not in seen_urls:
                        seen_urls.add(href)
                        page_urls.append(href)
                        urls.append(href)

                logger.debug(
                    "listing_page_scraped",
                    url=listing_url,
                    recipes_found=len(page_urls),
                    total=len(urls),
                )

                # Si aucune recette trouvee sur cette page, passer a la categorie suivante
                if not page_urls:
                    break

            except httpx.HTTPError as exc:
                logger.warning("listing_http_error", url=listing_url, error=str(exc))
                break
            except Exception as exc:
                logger.warning("listing_error", url=listing_url, error=str(exc))
                break

        logger.info(
            "category_scraped",
            category=category_path,
            total_urls=len(urls),
        )

    return urls[:max_urls]


# ---------------------------------------------------------------------------
# Scraping d'une recette individuelle
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    reraise=True,
)
async def fetch_recipe_page(
    client: httpx.AsyncClient,
    url: str,
) -> str:
    """Telecharge le HTML d'une page de recette avec retry sur erreurs reseau.

    Raises:
        httpx.HTTPStatusError pour les codes 4xx/5xx apres 3 tentatives.
    """
    response = await client.get(url, timeout=30, follow_redirects=True)

    if response.status_code == 429:
        logger.warning("rate_limited", url=url)
        # Attente longue sur 429
        await asyncio.sleep(30)
        response = await client.get(url, timeout=30, follow_redirects=True)

    response.raise_for_status()
    return response.text


async def scrape_single_recipe(
    client: httpx.AsyncClient,
    url: str,
    source_name: str,
    category_hint: str = "",
) -> tuple[dict[str, Any], list[str]] | None:
    """Scrape une page de recette et retourne les donnees normalisees.

    Returns:
        Tuple (normalized_recipe_dict, raw_ingredient_lines) ou None si echec.
    """
    try:
        html = await fetch_recipe_page(client, url)
    except httpx.HTTPStatusError as exc:
        logger.warning("page_fetch_error", url=url, status=exc.response.status_code)
        return None
    except Exception as exc:
        logger.warning("page_fetch_error", url=url, error=str(exc))
        return None

    jsonld = extract_jsonld_recipe(html)
    if not jsonld:
        logger.debug("no_jsonld_found", url=url)
        return None

    normalized = normalize_jsonld_recipe(jsonld, source_name, url, category_hint)
    ingredient_lines = _extract_ingredients_from_jsonld(jsonld)

    if not passes_quality_filter(jsonld, normalized):
        logger.debug("quality_filter_rejected", url=url, title=normalized["title"])
        return None

    return normalized, ingredient_lines


# ---------------------------------------------------------------------------
# Insertion en base de donnees
# ---------------------------------------------------------------------------


async def _upsert_ingredient(session: Any, canonical_name: str) -> str:
    """Insere ou recupere un ingredient canonique.

    Utilise ON CONFLICT DO NOTHING + SELECT pour gerer les race conditions.

    Returns:
        UUID de l'ingredient sous forme de chaine.
    """
    from sqlalchemy import text

    ingredient_id = str(uuid4())
    await session.execute(
        text(
            """
            INSERT INTO ingredients (id, canonical_name, category, created_at)
            VALUES (:id, :name, :category, NOW())
            ON CONFLICT (canonical_name) DO NOTHING
            """
        ),
        {
            "id": ingredient_id,
            "name": canonical_name,
            "category": INGREDIENT_CATEGORY_DEFAULT,
        },
    )

    result = await session.execute(
        text("SELECT id FROM ingredients WHERE canonical_name = :name LIMIT 1"),
        {"name": canonical_name},
    )
    row = result.fetchone()
    if row is None:
        raise RuntimeError(
            f"Impossible de retrouver l'ingredient apres INSERT : {canonical_name!r}"
        )
    return str(row[0])


async def _insert_recipe_with_ingredients(
    session: Any,
    recipe_data: dict[str, Any],
    ingredient_lines: list[str],
    dry_run: bool,
) -> bool:
    """Insere une recette et ses ingredients dans la base de donnees.

    Strategie :
    - Verifier le doublon par source_url OU slug avant d'inserer.
    - INSERT recipes ON CONFLICT (slug) DO NOTHING.
    - Pour chaque ingredient, parser la ligne FR, upsert dans ingredients,
      puis INSERT recipe_ingredients.

    Returns:
        True si la recette a ete inseree, False si elle existait deja.
    """
    from sqlalchemy import text

    title = recipe_data["title"]
    slug = recipe_data["slug"]
    source_url = recipe_data.get("source_url") or ""

    # Verification doublon par source_url OU slug
    check_query = text(
        """
        SELECT id FROM recipes
        WHERE slug = :slug OR (source_url != '' AND source_url = :source_url)
        LIMIT 1
        """
    )
    result = await session.execute(check_query, {"slug": slug, "source_url": source_url})
    existing = result.fetchone()
    if existing:
        logger.debug("recipe_skipped_duplicate", title=title, slug=slug)
        return False

    if dry_run:
        logger.info("[DRY_RUN] would_insert", title=title, ingredients=len(ingredient_lines))
        return True

    recipe_id = str(uuid4())
    instructions_json = json.dumps(recipe_data["instructions"], ensure_ascii=False)
    nutrition_json = (
        json.dumps(recipe_data["nutrition"], ensure_ascii=False)
        if recipe_data.get("nutrition")
        else None
    )

    await session.execute(
        text(
            """
            INSERT INTO recipes (
                id, title, slug, source, source_url,
                description, photo_url, nutrition,
                instructions, servings,
                prep_time_min, cook_time_min,
                difficulty, cuisine_type,
                tags, quality_score, language,
                created_at, updated_at
            ) VALUES (
                :id, :title, :slug, :source, :source_url,
                :description, :photo_url, :nutrition::jsonb,
                :instructions::jsonb, :servings,
                :prep_time_min, :cook_time_min,
                :difficulty, :cuisine_type,
                :tags::text[], :quality_score, :language,
                NOW(), NOW()
            )
            ON CONFLICT (slug) DO NOTHING
            """
        ),
        {
            "id": recipe_id,
            "title": title,
            "slug": slug,
            "source": recipe_data["source"],
            "source_url": source_url,
            "description": recipe_data.get("description") or "",
            "photo_url": recipe_data.get("photo_url") or "",
            "nutrition": nutrition_json,
            "instructions": instructions_json,
            "servings": recipe_data["servings"],
            "prep_time_min": recipe_data["prep_time_min"],
            "cook_time_min": recipe_data["cook_time_min"],
            "difficulty": recipe_data["difficulty"],
            "cuisine_type": recipe_data["cuisine_type"],
            "tags": recipe_data["tags"],
            "quality_score": recipe_data["quality_score"],
            "language": recipe_data.get("language") or "fr",
        },
    )

    # Verifier que la recette a bien ete inseree (ON CONFLICT peut avoir ignore)
    result = await session.execute(
        text("SELECT id FROM recipes WHERE slug = :slug LIMIT 1"),
        {"slug": slug},
    )
    row = result.fetchone()
    if row is None:
        logger.warning("recipe_insert_ignored_conflict", slug=slug)
        return False

    actual_recipe_id = str(row[0])

    # Insertion des ingredients avec parsing FR + upsert + liaison recipe_ingredients
    for position, ingredient_line in enumerate(ingredient_lines):
        try:
            quantity, unit, canonical_name = parse_ingredient_line(ingredient_line)
        except Exception as exc:
            logger.warning(
                "ingredient_parse_error",
                line=ingredient_line[:80],
                error=str(exc),
            )
            continue

        if not canonical_name or canonical_name == "ingr\u00e9dient inconnu":
            continue

        try:
            ingredient_id = await _upsert_ingredient(session, canonical_name)
        except Exception as exc:
            logger.warning(
                "ingredient_upsert_error",
                canonical_name=canonical_name[:50],
                error=str(exc),
            )
            continue

        await session.execute(
            text(
                """
                INSERT INTO recipe_ingredients
                    (recipe_id, ingredient_id, quantity, unit, notes, position)
                VALUES
                    (:recipe_id, :ingredient_id, :quantity, :unit, :notes, :position)
                ON CONFLICT (recipe_id, ingredient_id) DO NOTHING
                """
            ),
            {
                "recipe_id": actual_recipe_id,
                "ingredient_id": ingredient_id,
                "quantity": quantity,
                "unit": unit,
                "notes": ingredient_line[:200],
                "position": position,
            },
        )

    await session.commit()
    logger.info(
        "recipe_inserted",
        title=title,
        recipe_id=actual_recipe_id,
        source=recipe_data["source"],
        ingredients_count=len(ingredient_lines),
        tags=recipe_data["tags"],
    )
    return True


# ---------------------------------------------------------------------------
# Orchestration d'un site
# ---------------------------------------------------------------------------


async def scrape_site(
    site_key: str,
    site_config: dict[str, Any],
    session_factory: Any,
    max_recipes: int,
    scrape_delay: float,
    dry_run: bool,
) -> dict[str, int]:
    """Orchestre le scraping complet d'un site.

    Etapes :
    1. Tenter la decouverte via sitemap XML
    2. Si pas assez d'URLs, completer via pagination des categories
    3. Scraper chaque URL de recette
    4. Inserer en base avec idempotence

    Returns:
        Dict avec les compteurs : urls_found, scraped, inserted, skipped, quality_rejected, errors.
    """
    source_name = site_config["source_name"]

    stats: dict[str, int] = {
        "urls_found": 0,
        "scraped": 0,
        "inserted": 0,
        "skipped": 0,
        "quality_rejected": 0,
        "errors": 0,
    }

    logger.info(
        "site_scrape_start",
        site=site_key,
        source=source_name,
        max_recipes=max_recipes,
    )

    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=5, max_keepalive_connections=3),
    ) as http_client:
        # Etape 1 : Decouverte des URLs via sitemap
        all_urls: list[str] = []
        for sitemap_url in site_config.get("sitemap_urls", []):
            if len(all_urls) >= max_recipes * 2:
                break
            logger.info("trying_sitemap", url=sitemap_url)
            sitemap_urls = await discover_urls_from_sitemap(
                http_client, sitemap_url, max_recipes * 2, scrape_delay
            )
            all_urls.extend(sitemap_urls)

        logger.info("sitemap_discovery_done", urls_found=len(all_urls), site=site_key)

        # Etape 2 : Completer via categories si besoin
        if len(all_urls) < max_recipes:
            logger.info(
                "falling_back_to_categories",
                current_urls=len(all_urls),
                needed=max_recipes,
                site=site_key,
            )
            category_urls = await discover_urls_from_categories(
                http_client, site_config, max_recipes * 2 - len(all_urls), scrape_delay
            )
            # Deduplication
            existing = set(all_urls)
            for url in category_urls:
                if url not in existing:
                    all_urls.append(url)
                    existing.add(url)

        # Limiter le nombre d'URLs a traiter
        all_urls = all_urls[: max_recipes * 2]
        stats["urls_found"] = len(all_urls)
        logger.info("url_discovery_complete", total_urls=len(all_urls), site=site_key)

        if dry_run and all_urls:
            logger.info("[DRY_RUN] Apercu des 5 premieres URLs :")
            for url in all_urls[:5]:
                logger.info(f"  [DRY_RUN] {url}")

        # Etape 3 : Scraper et inserer chaque recette
        for i, url in enumerate(all_urls):
            if stats["inserted"] >= max_recipes:
                logger.info("max_recipes_reached", count=stats["inserted"])
                break

            await asyncio.sleep(scrape_delay)

            # Extraire un hint de categorie depuis l'URL
            category_hint = url.split("/")[-1].split("?")[0] if "/" in url else ""

            result = await scrape_single_recipe(http_client, url, source_name, category_hint)

            if result is None:
                stats["quality_rejected"] += 1
                continue

            normalized, ingredient_lines = result
            stats["scraped"] += 1

            # Insertion en base
            try:
                async with session_factory() as session:
                    was_inserted = await _insert_recipe_with_ingredients(
                        session, normalized, ingredient_lines, dry_run
                    )
                    if was_inserted:
                        stats["inserted"] += 1
                    else:
                        stats["skipped"] += 1
            except Exception as exc:
                logger.error(
                    "recipe_insert_error",
                    url=url,
                    title=normalized.get("title", "?"),
                    error=str(exc),
                )
                stats["errors"] += 1

            # Progression periodique
            if (i + 1) % 50 == 0:
                logger.info(
                    "scrape_progress",
                    site=site_key,
                    processed=i + 1,
                    total_urls=len(all_urls),
                    inserted=stats["inserted"],
                    skipped=stats["skipped"],
                    errors=stats["errors"],
                )

    return stats


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _configure_logging() -> None:
    """Configure loguru avec sortie console structuree."""
    logger.remove()
    logger.add(
        sys.stdout,
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> -- {message}"
        ),
        serialize=False,
    )


def _validate_env() -> str:
    """Verifie que DATABASE_URL est definie.

    Returns:
        database_url.

    Raises:
        SystemExit si la variable obligatoire est manquante.
    """
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error(
            "env_vars_missing",
            missing=["DATABASE_URL"],
            hint="Exemple : DATABASE_URL=postgresql+asyncpg://user:pass@host/db",
        )
        sys.exit(1)
    return db_url


# ---------------------------------------------------------------------------
# Point d'entree principal
# ---------------------------------------------------------------------------


async def run_scrape(
    database_url: str,
    source_sites: list[str] | None = None,
    max_recipes: int = 2000,
    scrape_delay: float = 2.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Orchestre le scraping complet depuis un ou plusieurs sites vers la base de donnees.

    Appelable directement depuis une tache Celery (await run_scrape(...)).

    Returns:
        Dict avec les compteurs par site et le total global.
    """
    if source_sites is None:
        source_sites = ["750g"]

    # Valider les sites demandes
    valid_sites: list[str] = []
    for site in source_sites:
        site = site.strip().lower()
        if site in SITE_CONFIGS:
            valid_sites.append(site)
        else:
            logger.warning("unknown_site", site=site, available=list(SITE_CONFIGS.keys()))

    if not valid_sites:
        logger.error("no_valid_sites", requested=source_sites)
        return {"error": "Aucun site valide configure"}

    logger.info(
        "scrape_start",
        sites=valid_sites,
        max_recipes=max_recipes,
        scrape_delay=scrape_delay,
        dry_run=dry_run,
    )

    # Moteur SQLAlchemy async
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Repartir le max_recipes entre les sites
    recipes_per_site = max_recipes // len(valid_sites)

    all_stats: dict[str, dict[str, int]] = {}
    global_totals: dict[str, int] = {
        "urls_found": 0,
        "scraped": 0,
        "inserted": 0,
        "skipped": 0,
        "quality_rejected": 0,
        "errors": 0,
    }

    for site_key in valid_sites:
        site_config = SITE_CONFIGS[site_key]

        site_stats = await scrape_site(
            site_key=site_key,
            site_config=site_config,
            session_factory=session_factory,
            max_recipes=recipes_per_site,
            scrape_delay=scrape_delay,
            dry_run=dry_run,
        )

        all_stats[site_key] = site_stats
        for key in global_totals:
            global_totals[key] += site_stats.get(key, 0)

    await engine.dispose()

    # Rapport final
    logger.info("=" * 60)
    logger.info("RAPPORT SCRAPING RECETTES")
    logger.info("=" * 60)
    for site_key, site_stats in all_stats.items():
        logger.info(f"--- {site_key} ---")
        for key, val in site_stats.items():
            logger.info(f"  {key}: {val}")
    logger.info("--- TOTAL ---")
    for key, val in global_totals.items():
        logger.info(f"  {key}: {val}")
    logger.info("=" * 60)

    return {"sites": all_stats, "totals": global_totals}


async def main() -> None:
    """Point d'entree CLI du script."""
    _configure_logging()
    database_url = _validate_env()

    max_recipes = int(os.getenv("MAX_RECIPES", "2000"))
    scrape_delay = float(os.getenv("SCRAPE_DELAY", "2.0"))
    dry_run = os.getenv("DRY_RUN", "").lower() == "true"

    source_sites_env = os.getenv("SOURCE_SITES", "750g")
    source_sites = [s.strip() for s in source_sites_env.split(",") if s.strip()]

    result = await run_scrape(
        database_url=database_url,
        source_sites=source_sites,
        max_recipes=max_recipes,
        scrape_delay=scrape_delay,
        dry_run=dry_run,
    )

    total_errors = 0
    if isinstance(result.get("totals"), dict):
        total_errors = result["totals"].get("errors", 0)

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
