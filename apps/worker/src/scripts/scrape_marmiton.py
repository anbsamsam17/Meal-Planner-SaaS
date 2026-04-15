"""Import de recettes depuis Marmiton.org par scraping HTML + JSON-LD.

Pipeline complet :
1. Parcours des pages de categories Marmiton (plat-principal, entree, dessert, etc.)
2. Extraction des URLs de recettes depuis les pages listing
3. Scraping de chaque recette : JSON-LD (schema.org Recipe) + fallback HTML
4. Parsing robuste des ingredients FR (quantite, unite, nom canonique)
5. Filtrage qualite (photo, >= 3 ingredients, instructions presentes)
6. Insertion DB avec upsert idempotent (ON CONFLICT slug DO NOTHING)

Usage :
    cd apps/worker
    set -a && source ../../.env.local && set +a
    python -m src.scripts.scrape_marmiton

Variables d'environnement :
    DATABASE_URL              Obligatoire -- connexion PostgreSQL async (asyncpg).
    DRY_RUN                   Optionnel -- "true" pour simuler sans ecriture (defaut : false).
    MAX_RECIPES               Optionnel -- nombre max de recettes (defaut : 2000).
    MAX_PAGES_PER_CATEGORY    Optionnel -- pages par categorie (defaut : 50).
    LOG_LEVEL                 Optionnel -- DEBUG/INFO/WARNING (defaut : INFO).
    SCRAPE_DELAY              Optionnel -- delai entre requetes en secondes (defaut : 2.0).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import sys
from typing import Any
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from slugify import slugify
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MARMITON_BASE = "https://www.marmiton.org"

CATEGORIES: list[dict[str, str]] = [
    {"slug": "plat-principal", "tag": "plat-principal"},
    {"slug": "entree", "tag": "entree"},
    {"slug": "dessert", "tag": "dessert"},
    {"slug": "accompagnement", "tag": "accompagnement"},
    {"slug": "boisson", "tag": "boisson"},
    {"slug": "sauce", "tag": "sauce"},
    {"slug": "amuse-gueule", "tag": "amuse-gueule"},
]

# Mapping texte Marmiton -> difficulte numerique (1-5)
DIFFICULTY_MAP: dict[str, int] = {
    "tres facile": 1,
    "très facile": 1,
    "very easy": 1,
    "facile": 2,
    "easy": 2,
    "moyen": 3,
    "moyenne": 3,
    "moyennement difficile": 3,
    "medium": 3,
    "normal": 3,
    "difficile": 4,
    "hard": 4,
    "tres difficile": 5,
    "très difficile": 5,
    "very hard": 5,
}

# Mapping des unites francaises courantes vers une forme canonique
UNIT_MAP: dict[str, str] = {
    # Masse
    "g": "g",
    "gr": "g",
    "gramme": "g",
    "grammes": "g",
    "kg": "kg",
    "kilogramme": "kg",
    "kilogrammes": "kg",
    # Volume liquide
    "ml": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "cl": "cl",
    "centilitre": "cl",
    "centilitres": "cl",
    "dl": "dl",
    "decilitre": "dl",
    "decilitres": "dl",
    "l": "L",
    "litre": "L",
    "litres": "L",
    # Cuilleres
    "c. a soupe": "c. a soupe",
    "c. a cafe": "c. a cafe",
    "c.a.s": "c. a soupe",
    "c.a.s.": "c. a soupe",
    "c.a.c": "c. a cafe",
    "c.a.c.": "c. a cafe",
    "cas": "c. a soupe",
    "cac": "c. a cafe",
    "cuillere a soupe": "c. a soupe",
    "cuilleres a soupe": "c. a soupe",
    "cuillere a cafe": "c. a cafe",
    "cuilleres a cafe": "c. a cafe",
    "cuill. a soupe": "c. a soupe",
    "cuill. a cafe": "c. a cafe",
    # Quantites discretes
    "pincee": "pincee",
    "pincees": "pincee",
    "poignee": "poignee",
    "poignees": "poignee",
    "brin": "brin",
    "brins": "brin",
    "feuille": "feuille",
    "feuilles": "feuille",
    "tranche": "tranche",
    "tranches": "tranche",
    "gousse": "gousse",
    "gousses": "gousse",
    "sachet": "sachet",
    "sachets": "sachet",
    "verre": "verre",
    "verres": "verre",
    "tasse": "tasse",
    "tasses": "tasse",
    "pot": "pot",
    "pots": "pot",
    "boite": "boite",
    "boites": "boite",
    "botte": "botte",
    "bottes": "botte",
    "paquet": "paquet",
    "paquets": "paquet",
    "barquette": "barquette",
    "barquettes": "barquette",
    "morceau": "morceau",
    "morceaux": "morceau",
    "noisette": "noisette",
    "noisettes": "noisette",
    "noix": "noix",
    "filet": "filet",
    "filets": "filet",
    "bloc": "bloc",
    "blocs": "bloc",
    "tablette": "tablette",
    "tablettes": "tablette",
    "baton": "baton",
    "batons": "baton",
    "tige": "tige",
    "tiges": "tige",
    "bouquet": "bouquet",
    "bouquets": "bouquet",
    "zeste": "zeste",
    "zestes": "zeste",
}

# Mots-cles pour detecter les regimes alimentaires dans les tags/keywords Marmiton
DIET_KEYWORDS: dict[str, str] = {
    "vegetarien": "vegetarien",
    "vegetarienne": "vegetarien",
    "vegan": "vegan",
    "vegane": "vegan",
    "sans gluten": "sans-gluten",
    "sans lactose": "sans-lactose",
    "halal": "halal",
    "light": "light",
    "leger": "light",
    "legere": "light",
    "economique": "economique",
    "rapide": "rapide",
    "facile": "facile",
}

# Categorie ingredient par defaut (champ NOT NULL en DB)
INGREDIENT_CATEGORY_DEFAULT = "other"

# Score de qualite pour les recettes Marmiton passant les filtres
QUALITY_SCORE = 0.85

# Nombre minimum d'ingredients pour qu'une recette soit acceptee
MIN_INGREDIENTS = 3

# User-Agent realiste pour le scraping
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Helpers de parsing
# ---------------------------------------------------------------------------


def parse_iso8601_duration(duration: str | None) -> int | None:
    """Convertit une duree ISO 8601 (PT30M, PT1H15M, PT2H) en minutes.

    Gere les formats courants utilises par Marmiton dans le JSON-LD :
    - PT30M        -> 30
    - PT1H         -> 60
    - PT1H15M      -> 75
    - PT2H30M      -> 150
    - PT0M         -> 0

    Returns:
        Nombre de minutes, ou None si le format est invalide/absent.
    """
    if not duration:
        return None

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration, re.IGNORECASE)
    if not match:
        return None

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    total = hours * 60 + minutes + (1 if seconds >= 30 else 0)
    return total


def _strip_accents_for_matching(text: str) -> str:
    """Retire les accents pour les comparaisons (matching d'unites, difficulte).

    Utilise la decomposition Unicode NFKD pour retirer les diacritiques.
    Ne modifie PAS le texte original -- seulement pour les lookups dans les maps.
    """
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_ingredient_name(name: str) -> str:
    """Normalise un nom d'ingredient en forme canonique.

    - Lowercase
    - Retire les articles/prepositions en debut ("de ", "d'", "du ", "des ", "la ", "le ", "les ")
    - Singulier simpliste (retire le 's' final si applicable, sauf mots courts)
    - Tronque a 100 caracteres
    """
    name = name.strip().lower()

    # Retirer les articles et prepositions de debut
    prefixes = [
        "de la ",
        "de l'",
        "de l'",
        "du ",
        "des ",
        "de ",
        "d'",
        "d'",
        "la ",
        "le ",
        "les ",
        "l'",
        "l'",
    ]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    name = name.strip()

    # Singulier simpliste : retirer le 's' final pour les mots de plus de 3 lettres
    # Exceptions : mots se terminant par 's' naturellement (ananas, bras, noix, riz, etc.)
    # On ne touche pas aux mots <= 3 lettres ni ceux finissant en "ss", "us", "is", "os", "as"
    if len(name) > 3 and name.endswith("s") and not name.endswith(("ss", "us", "is", "os", "as")):
        name = name[:-1]

    return name[:100]


def parse_ingredient_line(line: str) -> list[tuple[float, str, str]]:
    """Parse une ligne d'ingredient Marmiton en tuples (quantite, unite, nom).

    Gere les cas courants :
    - "200 g de farine"           -> [(200.0, "g", "farine")]
    - "3 oeufs"                   -> [(3.0, "unite", "oeuf")]
    - "1/2 citron"                -> [(0.5, "unite", "citron")]
    - "sel et poivre"             -> [(1.0, "pincee", "sel"), (1.0, "pincee", "poivre")]
    - "1 c. a soupe d'huile"      -> [(1.0, "c. a soupe", "huile")]
    - "quelques feuilles de basilic" -> [(3.0, "feuille", "basilic")]
    - ""                          -> []

    Returns:
        Liste de tuples (quantity, unit, canonical_name). Peut etre vide.
    """
    line = line.strip()
    if not line:
        return []

    # Detecter "X et Y" pour les condiments simples (sel et poivre, etc.)
    if re.match(r"^[a-zA-ZÀ-ÿ]+\s+et\s+[a-zA-ZÀ-ÿ]+$", line):
        parts = re.split(r"\s+et\s+", line)
        return [(1.0, "pincee", normalize_ingredient_name(p)) for p in parts if p.strip()]

    # Regex pour extraire quantite + unite + nom
    # Groupe 1 : quantite (nombre entier, decimal, fraction)
    # Groupe 2 : unite (optionnel, mot(s) d'unite reconnus)
    # Groupe 3 : nom de l'ingredient (le reste)

    # D'abord, extraire la quantite en debut de ligne
    quantity = 1.0
    rest = line

    # Pattern pour quantite : nombre, fraction, ou mot-quantite
    qty_match = re.match(
        r"^(\d+[.,]\d+|\d+\s*/\s*\d+|\d+)\s*",
        rest,
    )
    if qty_match:
        qty_str = qty_match.group(1).strip()
        rest = rest[qty_match.end() :].strip()

        # Convertir la quantite
        if "/" in qty_str:
            parts = qty_str.split("/")
            try:
                quantity = float(parts[0].strip()) / float(parts[1].strip())
            except (ValueError, ZeroDivisionError):
                quantity = 1.0
        else:
            try:
                quantity = float(qty_str.replace(",", "."))
            except ValueError:
                quantity = 1.0
    elif rest.lower().startswith("quelques"):
        quantity = 3.0
        rest = rest[8:].strip()
    elif rest.lower().startswith("un peu"):
        quantity = 1.0
        rest = rest[6:].strip()
        rest = re.sub(r"^de\s+", "", rest, flags=re.IGNORECASE)

    # La quantite doit etre > 0 (contrainte DB)
    if quantity <= 0:
        quantity = 1.0

    # Extraire l'unite
    unit = "unite"
    rest_lower = _strip_accents_for_matching(rest.lower())

    # Trier les cles d'unite par longueur decroissante pour matcher les plus longues d'abord
    sorted_units = sorted(UNIT_MAP.keys(), key=len, reverse=True)
    for unit_key in sorted_units:
        unit_key_normalized = _strip_accents_for_matching(unit_key)
        # Matcher l'unite en debut de la partie restante
        if rest_lower.startswith(unit_key_normalized):
            unit = UNIT_MAP[unit_key]
            # Avancer dans la chaine d'origine
            rest = rest[len(unit_key) :].strip()
            rest_lower = _strip_accents_for_matching(rest.lower())
            break

    # Retirer les prepositions entre unite et nom : "de", "d'", "du", "des"
    rest = re.sub(
        r"^(de\s+la\s+|de\s+l['']\s*|du\s+|des\s+|de\s+|d['']\s*)", "", rest, flags=re.IGNORECASE
    )
    rest = rest.strip()

    if not rest:
        return []

    canonical = normalize_ingredient_name(rest)
    if not canonical:
        return []

    return [(quantity, unit, canonical)]


def extract_json_ld_recipe(html: str) -> dict[str, Any] | None:
    """Extrait le premier objet JSON-LD de type Recipe depuis le HTML.

    Marmiton inclut toujours un <script type="application/ld+json"> avec un schema.org
    Recipe contenant toutes les donnees structurees de la recette.

    Returns:
        Dict JSON-LD ou None si aucun Recipe trouve.
    """
    soup = BeautifulSoup(html, "lxml")
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        # Le JSON-LD peut etre un objet direct ou un @graph
        candidates: list[dict[str, Any]] = []
        if isinstance(data, list):
            candidates.extend(data)
        elif isinstance(data, dict):
            if "@graph" in data:
                candidates.extend(data["@graph"])
            else:
                candidates.append(data)

        for item in candidates:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", "")
            if isinstance(item_type, list):
                if "Recipe" in item_type:
                    return item
            elif item_type == "Recipe":
                return item

    return None


def map_json_ld_to_recipe(
    json_ld: dict[str, Any],
    source_url: str,
    category_tag: str,
) -> dict[str, Any] | None:
    """Mappe un objet JSON-LD Recipe vers le format DB interne.

    Applique les filtres de qualite :
    - Photo obligatoire
    - Au moins MIN_INGREDIENTS ingredients
    - Instructions presentes

    Returns:
        Dict pret pour l'insertion, ou None si la recette ne passe pas les filtres.
    """
    title = (json_ld.get("name") or "").strip()
    if not title:
        logger.debug("skip_no_title", url=source_url)
        return None

    # Photo
    photo_url = _extract_photo(json_ld)
    if not photo_url:
        logger.debug("skip_no_photo", title=title)
        return None

    # Instructions
    instructions = _extract_instructions(json_ld)
    if not instructions:
        logger.debug("skip_no_instructions", title=title)
        return None

    # Ingredients bruts
    raw_ingredients: list[str] = json_ld.get("recipeIngredient") or []
    if len(raw_ingredients) < MIN_INGREDIENTS:
        logger.debug(
            "skip_few_ingredients",
            title=title,
            count=len(raw_ingredients),
            min_required=MIN_INGREDIENTS,
        )
        return None

    # Description
    description = (json_ld.get("description") or "").strip()[:500]

    # Servings
    servings = _parse_servings(json_ld.get("recipeYield"))

    # Temps
    prep_time = parse_iso8601_duration(json_ld.get("prepTime"))
    cook_time = parse_iso8601_duration(json_ld.get("cookTime"))
    total_time_raw = parse_iso8601_duration(json_ld.get("totalTime"))

    # Si seul totalTime est present, estimer prep/cook
    if total_time_raw and not prep_time and not cook_time:
        prep_time = max(0, total_time_raw // 3)
        cook_time = max(0, total_time_raw - prep_time)

    # S'assurer que les temps sont >= 0 (contrainte DB)
    prep_time = max(0, prep_time) if prep_time is not None else None
    cook_time = max(0, cook_time) if cook_time is not None else None

    # Difficulte
    difficulty = _extract_difficulty(json_ld)

    # Cuisine
    cuisine_type = _extract_cuisine(json_ld)

    # Nutrition
    nutrition = _extract_nutrition(json_ld)

    # Tags
    tags = _build_tags(json_ld, category_tag, prep_time, cook_time)

    # Slug unique avec source_url hash pour eviter les collisions
    slug = slugify(title, max_length=200)
    if not slug:
        slug = f"marmiton-{uuid4().hex[:8]}"

    return {
        "title": title,
        "slug": slug,
        "source": "marmiton",
        "source_url": source_url,
        "description": description,
        "photo_url": photo_url,
        "instructions": instructions,
        "servings": servings,
        "prep_time_min": prep_time,
        "cook_time_min": cook_time,
        "difficulty": difficulty,
        "cuisine_type": cuisine_type,
        "nutrition": nutrition,
        "tags": tags,
        "quality_score": QUALITY_SCORE,
        "raw_ingredients": raw_ingredients,
    }


def _extract_photo(json_ld: dict[str, Any]) -> str | None:
    """Extrait l'URL de la photo en meilleure resolution depuis le JSON-LD."""
    image = json_ld.get("image")
    if not image:
        return None

    if isinstance(image, str):
        return image
    if isinstance(image, list):
        # Prendre la derniere (souvent la plus haute resolution)
        for img in reversed(image):
            if isinstance(img, str):
                return img
            if isinstance(img, dict):
                return img.get("url") or img.get("contentUrl")
        return None
    if isinstance(image, dict):
        return image.get("url") or image.get("contentUrl")

    return None


def _extract_instructions(json_ld: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrait les instructions depuis le JSON-LD au format [{"step": N, "text": "..."}].

    Gere les deux formats courants :
    - Liste de strings : ["Etape 1...", "Etape 2..."]
    - Liste de HowToStep : [{"@type": "HowToStep", "text": "..."}]
    - Liste de HowToSection contenant des HowToStep
    """
    raw = json_ld.get("recipeInstructions")
    if not raw:
        return []

    steps: list[dict[str, Any]] = []

    if isinstance(raw, str):
        # Texte brut : decouper sur les phrases
        sentences = re.split(r"\.\s+|\n", raw)
        for i, sentence in enumerate(sentences):
            text = sentence.strip(" .")
            if text and len(text) > 5:
                steps.append({"step": i + 1, "text": text})
        return steps[:20]

    if not isinstance(raw, list):
        return []

    step_num = 1
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text and len(text) > 5:
                steps.append({"step": step_num, "text": text})
                step_num += 1
        elif isinstance(item, dict):
            item_type = item.get("@type", "")

            if item_type == "HowToSection":
                # Section contenant des sous-etapes
                for sub_item in item.get("itemListElement") or []:
                    if isinstance(sub_item, dict):
                        text = (sub_item.get("text") or "").strip()
                        if text and len(text) > 5:
                            steps.append({"step": step_num, "text": text})
                            step_num += 1
                    elif isinstance(sub_item, str) and len(sub_item.strip()) > 5:
                        steps.append({"step": step_num, "text": sub_item.strip()})
                        step_num += 1
            else:
                # HowToStep ou autre
                text = (item.get("text") or "").strip()
                if text and len(text) > 5:
                    steps.append({"step": step_num, "text": text})
                    step_num += 1

    return steps[:20]


def _parse_servings(raw: Any) -> int:
    """Extrait le nombre de portions depuis recipeYield.

    Formats possibles : "4", "4 personnes", "4-6", ["4 servings"], 4
    """
    if raw is None:
        return 4

    if isinstance(raw, int):
        return max(1, raw)

    if isinstance(raw, list):
        raw = raw[0] if raw else "4"

    if isinstance(raw, str):
        match = re.search(r"(\d+)", raw)
        if match:
            return max(1, int(match.group(1)))

    return 4


def _extract_difficulty(json_ld: dict[str, Any]) -> int:
    """Extrait la difficulte depuis le JSON-LD ou estime depuis le temps total.

    Marmiton n'a pas toujours la difficulte dans le JSON-LD, donc on estime
    a partir du temps total si absent.
    """
    # Tenter d'extraire depuis les donnees structurees
    difficulty_text = (json_ld.get("difficulty") or "").strip().lower()
    if difficulty_text:
        normalized = _strip_accents_for_matching(difficulty_text)
        if normalized in DIFFICULTY_MAP:
            return DIFFICULTY_MAP[normalized]

    # Estimation depuis le temps total
    total_time = parse_iso8601_duration(json_ld.get("totalTime"))
    if total_time is not None:
        if total_time <= 15:
            return 1
        if total_time <= 30:
            return 2
        if total_time <= 60:
            return 3
        if total_time <= 120:
            return 4
        return 5

    # Defaut
    return 2


def _extract_cuisine(json_ld: dict[str, Any]) -> str:
    """Extrait le type de cuisine depuis le JSON-LD. Defaut : 'francaise'."""
    cuisine = json_ld.get("recipeCuisine")
    if not cuisine:
        return "francaise"

    if isinstance(cuisine, list):
        cuisine = cuisine[0] if cuisine else "francaise"

    cuisine_lower = cuisine.strip().lower()
    if "fran" in cuisine_lower:
        return "francaise"
    return cuisine.strip() or "francaise"


def _extract_nutrition(json_ld: dict[str, Any]) -> dict[str, Any]:
    """Extrait les donnees nutritionnelles depuis le JSON-LD.

    Format cible : {"calories": N, "protein_g": N, "fat_g": N, "carbs_g": N}
    """
    nutrition_ld = json_ld.get("nutrition")
    if not nutrition_ld or not isinstance(nutrition_ld, dict):
        return {}

    result: dict[str, Any] = {}

    # Calories : "350 kcal" -> 350
    calories_raw = nutrition_ld.get("calories") or ""
    if calories_raw:
        cal_match = re.search(r"(\d+[.,]?\d*)", str(calories_raw))
        if cal_match:
            result["calories"] = round(float(cal_match.group(1).replace(",", ".")))

    # Proteines
    protein_raw = nutrition_ld.get("proteinContent") or ""
    if protein_raw:
        prot_match = re.search(r"(\d+[.,]?\d*)", str(protein_raw))
        if prot_match:
            result["protein_g"] = round(float(prot_match.group(1).replace(",", ".")), 1)

    # Lipides
    fat_raw = nutrition_ld.get("fatContent") or ""
    if fat_raw:
        fat_match = re.search(r"(\d+[.,]?\d*)", str(fat_raw))
        if fat_match:
            result["fat_g"] = round(float(fat_match.group(1).replace(",", ".")), 1)

    # Glucides
    carbs_raw = nutrition_ld.get("carbohydrateContent") or ""
    if carbs_raw:
        carbs_match = re.search(r"(\d+[.,]?\d*)", str(carbs_raw))
        if carbs_match:
            result["carbs_g"] = round(float(carbs_match.group(1).replace(",", ".")), 1)

    return result


def _build_tags(
    json_ld: dict[str, Any],
    category_tag: str,
    prep_time: int | None,
    cook_time: int | None,
) -> list[str]:
    """Construit la liste de tags depuis le JSON-LD et les metadonnees.

    Sources :
    - category_tag (la categorie Marmiton d'ou provient la recette)
    - recipeCategory du JSON-LD
    - keywords du JSON-LD
    - Temps total (rapide / long)
    - Mots-cles de regime alimentaire detectes
    """
    tags: set[str] = set()

    # Tag de categorie
    if category_tag:
        tags.add(category_tag)

    # recipeCategory
    categories = json_ld.get("recipeCategory") or []
    if isinstance(categories, str):
        categories = [categories]
    for cat in categories:
        cat_slug = slugify(cat.strip())
        if cat_slug:
            tags.add(cat_slug)

    # keywords
    keywords = json_ld.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",")]
    for kw in keywords:
        kw_lower = kw.strip().lower()
        # Verifier si c'est un mot-cle de regime connu
        for diet_key, diet_tag in DIET_KEYWORDS.items():
            if diet_key in _strip_accents_for_matching(kw_lower):
                tags.add(diet_tag)
                break
        else:
            kw_slug = slugify(kw.strip())
            if kw_slug and len(kw_slug) >= 3:
                tags.add(kw_slug)

    # Tags temporels
    total_time = (prep_time or 0) + (cook_time or 0)
    if 0 < total_time <= 30:
        tags.add("rapide")
    elif total_time > 60:
        tags.add("long")

    # Limiter le nombre de tags pour eviter le bruit
    return sorted(tags)[:15]


# ---------------------------------------------------------------------------
# Fonctions de scraping
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    reraise=True,
)
async def fetch_page(client: httpx.AsyncClient, url: str) -> str:
    """Telecharge une page HTML avec retry et backoff exponentiel.

    Leve une exception sur 4xx/5xx apres 3 tentatives.
    """
    response = await client.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return response.text


def extract_recipe_urls_from_listing(html: str) -> list[str]:
    """Extrait les URLs de recettes depuis une page listing Marmiton.

    Cherche les liens vers /recettes/recette_*.aspx ou /recettes/xxx_NNNNN.aspx
    """
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    seen: set[str] = set()

    # Marmiton utilise des liens <a> vers les pages recettes
    for link in soup.find_all("a", href=True):
        href = link["href"]

        # Pattern Marmiton : /recettes/recette_poulet-roti_12345.aspx
        # Ou format plus recent : /recettes/poulet-roti_12345.aspx
        if re.search(r"/recettes/[^/]+_\d+\.aspx", href):
            if href.startswith("/"):
                full_url = MARMITON_BASE + href
            elif href.startswith("http"):
                full_url = href
            else:
                continue

            # Deduplquer
            if full_url not in seen:
                seen.add(full_url)
                urls.append(full_url)

    return urls


async def discover_recipe_urls(
    client: httpx.AsyncClient,
    max_pages_per_category: int,
    max_total: int,
    scrape_delay: float,
) -> list[str]:
    """Parcourt les pages de categories Marmiton pour decouvrir les URLs de recettes.

    Respecte le rate limiting (scrape_delay entre chaque requete).
    S'arrete quand max_total URLs sont collectees ou quand toutes les pages sont epuisees.
    """
    all_urls: list[str] = []
    seen_urls: set[str] = set()

    for category in CATEGORIES:
        if len(all_urls) >= max_total:
            break

        cat_slug = category["slug"]
        logger.info("discover_category_start", category=cat_slug)

        for page_num in range(1, max_pages_per_category + 1):
            if len(all_urls) >= max_total:
                break

            url = f"{MARMITON_BASE}/recettes/index/categorie/{cat_slug}/?page={page_num}"

            try:
                html = await fetch_page(client, url)
                urls = extract_recipe_urls_from_listing(html)

                if not urls:
                    logger.debug(
                        "discover_no_more_pages",
                        category=cat_slug,
                        last_page=page_num,
                    )
                    break

                new_urls = [u for u in urls if u not in seen_urls]
                for u in new_urls:
                    seen_urls.add(u)
                    all_urls.append(u)

                logger.debug(
                    "discover_page_done",
                    category=cat_slug,
                    page=page_num,
                    found=len(urls),
                    new=len(new_urls),
                    total=len(all_urls),
                )

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.debug(
                        "discover_404_end",
                        category=cat_slug,
                        page=page_num,
                    )
                    break
                logger.warning(
                    "discover_page_error",
                    category=cat_slug,
                    page=page_num,
                    status=exc.response.status_code,
                )
            except Exception as exc:
                logger.warning(
                    "discover_page_error",
                    category=cat_slug,
                    page=page_num,
                    error=str(exc),
                )

            # Rate limiting
            await asyncio.sleep(scrape_delay)

        logger.info(
            "discover_category_done",
            category=cat_slug,
            urls_found=len(all_urls),
        )

    logger.info("discover_complete", total_urls=len(all_urls))
    return all_urls[:max_total]


async def scrape_recipe_page(
    client: httpx.AsyncClient,
    url: str,
    category_tag: str,
) -> dict[str, Any] | None:
    """Scrape une page recette Marmiton et retourne les donnees normalisees.

    Returns:
        Dict pret pour l'insertion, ou None si la recette ne passe pas les filtres.
    """
    try:
        html = await fetch_page(client, url)
    except Exception as exc:
        logger.warning("scrape_page_error", url=url, error=str(exc))
        return None

    json_ld = extract_json_ld_recipe(html)
    if not json_ld:
        logger.debug("scrape_no_json_ld", url=url)
        return None

    recipe_data = map_json_ld_to_recipe(json_ld, url, category_tag)
    return recipe_data


# ---------------------------------------------------------------------------
# Fonctions DB
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
    dry_run: bool,
) -> bool:
    """Insere une recette et ses ingredients parses dans la base de donnees.

    Strategie :
    - Verifier le doublon par source_url OU slug avant d'inserer
    - INSERT recipes ON CONFLICT (slug) DO NOTHING
    - Parser chaque ligne d'ingredient brut, upsert dans ingredients, puis INSERT recipe_ingredients

    Returns:
        True si la recette a ete inseree, False si elle existait deja.
    """
    from sqlalchemy import text

    title = recipe_data["title"]
    slug = recipe_data["slug"]
    source_url = recipe_data.get("source_url") or ""

    # Verification doublon par source_url OU slug
    result = await session.execute(
        text(
            """
            SELECT id FROM recipes
            WHERE slug = :slug OR (source_url != '' AND source_url = :source_url)
            LIMIT 1
            """
        ),
        {"slug": slug, "source_url": source_url},
    )
    if result.fetchone():
        logger.debug("recipe_skipped_duplicate", title=title, slug=slug)
        return False

    raw_ingredients: list[str] = recipe_data.pop("raw_ingredients", [])

    if dry_run:
        logger.info(
            "[DRY_RUN] would_insert",
            title=title,
            ingredients=len(raw_ingredients),
            tags=recipe_data["tags"],
        )
        return True

    recipe_id = str(uuid4())
    instructions_json = json.dumps(recipe_data["instructions"], ensure_ascii=False)
    nutrition_json = json.dumps(recipe_data.get("nutrition") or {}, ensure_ascii=False)

    await session.execute(
        text(
            """
            INSERT INTO recipes (
                id, title, slug, source, source_url,
                description, photo_url, nutrition,
                instructions, servings,
                prep_time_min, cook_time_min,
                difficulty, cuisine_type,
                tags, quality_score,
                created_at, updated_at
            ) VALUES (
                :id, :title, :slug, 'marmiton', :source_url,
                :description, :photo_url, CAST(:nutrition AS jsonb),
                CAST(:instructions AS jsonb), :servings,
                :prep_time_min, :cook_time_min,
                :difficulty, :cuisine_type,
                CAST(:tags AS text[]), :quality_score,
                NOW(), NOW()
            )
            ON CONFLICT (slug) DO NOTHING
            """
        ),
        {
            "id": recipe_id,
            "title": title,
            "slug": slug,
            "source_url": source_url,
            "description": recipe_data.get("description") or "",
            "photo_url": recipe_data.get("photo_url") or "",
            "nutrition": nutrition_json,
            "instructions": instructions_json,
            "servings": recipe_data["servings"],
            "prep_time_min": recipe_data.get("prep_time_min"),
            "cook_time_min": recipe_data.get("cook_time_min"),
            "difficulty": recipe_data.get("difficulty") or 2,
            "cuisine_type": recipe_data.get("cuisine_type") or "francaise",
            "tags": recipe_data["tags"],
            "quality_score": QUALITY_SCORE,
        },
    )

    # Verifier que la recette a bien ete inseree
    result = await session.execute(
        text("SELECT id FROM recipes WHERE slug = :slug LIMIT 1"),
        {"slug": slug},
    )
    row = result.fetchone()
    if not row:
        logger.warning("recipe_insert_ignored_conflict", slug=slug)
        return False

    actual_recipe_id = str(row[0])

    # Parser et inserer les ingredients
    for position, ingredient_line in enumerate(raw_ingredients[:30]):
        parsed_items = parse_ingredient_line(ingredient_line)
        for quantity, unit, canonical_name in parsed_items:
            if not canonical_name:
                continue

            try:
                ingredient_id = await _upsert_ingredient(session, canonical_name)
                await session.execute(
                    text(
                        """
                        INSERT INTO recipe_ingredients
                            (recipe_id, ingredient_id, quantity, unit, notes, position)
                        VALUES (:rid, :iid, :qty, :unit, :notes, :pos)
                        ON CONFLICT (recipe_id, ingredient_id) DO NOTHING
                        """
                    ),
                    {
                        "rid": actual_recipe_id,
                        "iid": ingredient_id,
                        "qty": quantity,
                        "unit": unit,
                        "notes": ingredient_line[:200],
                        "pos": position,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "ingredient_error",
                    name=canonical_name[:30],
                    line=ingredient_line[:50],
                    error=str(exc),
                )

    await session.commit()
    logger.info(
        "recipe_inserted",
        title=title,
        recipe_id=actual_recipe_id,
        ingredients_count=len(raw_ingredients),
        tags=recipe_data["tags"],
    )
    return True


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
            "env_var_missing",
            missing="DATABASE_URL",
            hint="DATABASE_URL=postgresql+asyncpg://user:pass@host/db",
        )
        sys.exit(1)
    return db_url


# ---------------------------------------------------------------------------
# Orchestrateur principal
# ---------------------------------------------------------------------------


async def run_scrape(
    database_url: str,
    max_recipes: int = 2000,
    max_pages_per_category: int = 50,
    scrape_delay: float = 2.0,
    dry_run: bool = False,
) -> dict[str, int]:
    """Orchestre le scraping complet de Marmiton vers la base de donnees.

    Appelable directement depuis une tache Celery (await run_scrape(...)).

    Returns:
        Dict avec les compteurs : urls_discovered, scraped, inserted, skipped,
        filtered, errors.
    """
    logger.info(
        "marmiton_scrape_start",
        max_recipes=max_recipes,
        max_pages_per_category=max_pages_per_category,
        scrape_delay=scrape_delay,
        dry_run=dry_run,
    )

    # Creation du moteur SQLAlchemy async
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Compteurs
    urls_discovered = 0
    scraped = 0
    inserted = 0
    skipped = 0
    filtered = 0
    errors = 0

    async with httpx.AsyncClient(
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
            "User-Agent": USER_AGENT,
        },
    ) as http_client:
        # Phase 1 : Decouverte des URLs
        logger.info("phase_1_discovery_start")
        all_urls = await discover_recipe_urls(
            http_client,
            max_pages_per_category=max_pages_per_category,
            max_total=max_recipes,
            scrape_delay=scrape_delay,
        )
        urls_discovered = len(all_urls)

        if not all_urls:
            logger.warning("no_urls_discovered")
            await engine.dispose()
            return {
                "urls_discovered": 0,
                "scraped": 0,
                "inserted": 0,
                "skipped": 0,
                "filtered": 0,
                "errors": 0,
            }

        # Construire un mapping URL -> tag de categorie pour le tagging
        # On attribue un tag par defaut base sur la position dans la decouverte
        url_to_category: dict[str, str] = {}
        urls_per_cat = max(1, max_recipes // len(CATEGORIES))
        for i, url in enumerate(all_urls):
            cat_idx = min(i // urls_per_cat, len(CATEGORIES) - 1)
            url_to_category[url] = CATEGORIES[cat_idx]["tag"]

        # Phase 2 : Scraping des recettes
        logger.info("phase_2_scraping_start", urls_to_scrape=urls_discovered)

        async with session_factory() as session:
            for i, url in enumerate(all_urls):
                category_tag = url_to_category.get(url, "")

                try:
                    recipe_data = await scrape_recipe_page(http_client, url, category_tag)
                    scraped += 1

                    if recipe_data is None:
                        filtered += 1
                        continue

                    was_inserted = await _insert_recipe_with_ingredients(
                        session, recipe_data, dry_run
                    )

                    if was_inserted:
                        inserted += 1
                    else:
                        skipped += 1

                except Exception as exc:
                    logger.error(
                        "recipe_processing_error",
                        url=url,
                        error=str(exc),
                    )
                    errors += 1
                    with contextlib.suppress(Exception):
                        await session.rollback()

                # Log de progression toutes les 50 recettes
                if (i + 1) % 50 == 0:
                    logger.info(
                        "progress",
                        processed=i + 1,
                        total=urls_discovered,
                        inserted=inserted,
                        skipped=skipped,
                        filtered=filtered,
                        errors=errors,
                        pct=round((i + 1) / urls_discovered * 100),
                    )

                # Rate limiting
                await asyncio.sleep(scrape_delay)

    await engine.dispose()

    # Rapport final
    logger.info("=" * 60)
    logger.info("RAPPORT SCRAPING MARMITON")
    logger.info(f"  URLs decouvertes     : {urls_discovered}")
    logger.info(f"  Pages scrapees       : {scraped}")
    logger.info(f"  Inserees             : {inserted}")
    logger.info(f"  Ignorees (doublons)  : {skipped}")
    logger.info(f"  Filtrees (qualite)   : {filtered}")
    logger.info(f"  Erreurs              : {errors}")
    logger.info("=" * 60)

    return {
        "urls_discovered": urls_discovered,
        "scraped": scraped,
        "inserted": inserted,
        "skipped": skipped,
        "filtered": filtered,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Point d'entree CLI
# ---------------------------------------------------------------------------


async def main() -> None:
    """Point d'entree CLI du script."""
    _configure_logging()
    database_url = _validate_env()

    max_recipes = int(os.getenv("MAX_RECIPES", "2000"))
    max_pages = int(os.getenv("MAX_PAGES_PER_CATEGORY", "50"))
    scrape_delay = float(os.getenv("SCRAPE_DELAY", "2.0"))
    dry_run = os.getenv("DRY_RUN", "").lower() == "true"

    stats = await run_scrape(
        database_url=database_url,
        max_recipes=max_recipes,
        max_pages_per_category=max_pages,
        scrape_delay=scrape_delay,
        dry_run=dry_run,
    )

    if stats["errors"] > stats["inserted"]:
        logger.error(
            "too_many_errors",
            errors=stats["errors"],
            inserted=stats["inserted"],
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
