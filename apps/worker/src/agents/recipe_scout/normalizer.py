"""
Normalisation des ingrédients vers un format canonique.

Transforme les lignes brutes d'ingrédients (ex: "200g de farine T55")
en structure normalisée (canonical_name, quantity, unit, category).

Règles de mapping FR pour la v0 :
- Base de données de noms canoniques couvrant les 200 ingrédients les plus courants
- Correspondance par synonymes (ex: "poulet" = "poule" = "volaille entière")
- Unités normalisées (g, kg, cl, ml, l, u, cs, cc)

En Phase 1 mature : enrichir avec Open Food Facts + validation LLM sur les cas ambigus.
"""

import re
from dataclasses import dataclass

from loguru import logger


@dataclass
class NormalizedIngredient:
    """
    Ingrédient normalisé prêt pour l'insertion en base.

    Correspond à la structure de la table `ingredients` du schéma Phase 0.
    """

    canonical_name: str
    quantity: float | None
    unit: str | None
    category: str
    raw_text: str  # Texte original pour audit et debug


# ---- Base de données de normalisation ----

# Mapping des unités brutes vers les unités canoniques
UNIT_MAPPING: dict[str, str] = {
    # Poids
    "g": "g",
    "gr": "g",
    "gramme": "g",
    "grammes": "g",
    "kg": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogramme": "kg",
    "kilogrammes": "kg",
    # Volume liquide
    "ml": "ml",
    "cl": "cl",
    "dl": "dl",
    "l": "l",
    "litre": "l",
    "litres": "l",
    "liter": "l",
    # Cuillères
    "cs": "cs",
    "c.s": "cs",
    "c.à.s": "cs",
    "càs": "cs",
    "cuillère à soupe": "cs",
    "cuillères à soupe": "cs",
    "cuiller à soupe": "cs",
    "cc": "cc",
    "c.c": "cc",
    "c.à.c": "cc",
    "càc": "cc",
    "cuillère à café": "cc",
    "cuillères à café": "cc",
    "cuiller à café": "cc",
    "tbsp": "cs",
    "tsp": "cc",
    # Unités
    "u": "u",
    "unité": "u",
    "unités": "u",
    "pièce": "u",
    "pièces": "u",
    "pc": "u",
    "pcs": "u",
    # Quantités vagues (normalisées vers unité)
    "pincée": "pincée",
    "pincées": "pincée",
    "bouquet": "bouquet",
    "bouquets": "bouquet",
    "tranche": "tranche",
    "tranches": "tranche",
    "brin": "brin",
    "brins": "brin",
    "feuille": "feuille",
    "feuilles": "feuille",
    "gousse": "gousse",
    "gousses": "gousse",
    "tasse": "tasse",
    "tasses": "tasse",
    "verre": "verre",
    "verres": "verre",
}

# Mapping des synonymes d'ingrédients vers le nom canonique
# Format : "synonyme_minuscules": "canonical_name"
INGREDIENT_SYNONYMS: dict[str, str] = {
    # Viandes
    "poulet": "poulet",
    "blanc de poulet": "poulet (blanc)",
    "filet de poulet": "poulet (blanc)",
    "cuisse de poulet": "poulet (cuisse)",
    "poule": "poule",
    "boeuf": "boeuf",
    "viande de boeuf": "boeuf",
    "veau": "veau",
    "porc": "porc",
    "lardons": "lardons",
    "bacon": "bacon",
    "jambon": "jambon",
    "jambon blanc": "jambon (blanc)",
    "jambon cru": "jambon (cru)",
    "saumon": "saumon",
    "saumon fumé": "saumon (fumé)",
    "thon": "thon",
    "crevettes": "crevettes",
    # Légumes
    "oignon": "oignon",
    "oignons": "oignon",
    "echalote": "échalote",
    "échalote": "échalote",
    "ail": "ail",
    "tomate": "tomate",
    "tomates": "tomate",
    "carotte": "carotte",
    "carottes": "carotte",
    "pomme de terre": "pomme de terre",
    "pommes de terre": "pomme de terre",
    "courgette": "courgette",
    "courgettes": "courgette",
    "aubergine": "aubergine",
    "poivron": "poivron",
    "champignon": "champignon",
    "champignons": "champignon",
    "épinard": "épinard",
    "épinards": "épinard",
    "laitue": "salade (laitue)",
    "salade": "salade",
    "brocoli": "brocoli",
    "brocolis": "brocoli",
    # Féculents
    "farine": "farine (T55)",
    "farine de blé": "farine (T55)",
    "farine t55": "farine (T55)",
    "farine t45": "farine (T45)",
    "pâtes": "pâtes",
    "spaghetti": "pâtes (spaghetti)",
    "tagliatelles": "pâtes (tagliatelles)",
    "penne": "pâtes (penne)",
    "riz": "riz",
    "riz basmati": "riz (basmati)",
    "pain": "pain",
    # Produits laitiers
    "beurre": "beurre",
    "crème": "crème fraîche",
    "crème fraîche": "crème fraîche",
    "crème liquide": "crème liquide",
    "lait": "lait",
    "oeuf": "oeuf",
    "oeufs": "oeuf",
    "oeuf entier": "oeuf",
    "fromage": "fromage",
    "gruyère": "gruyère",
    "emmental": "emmental",
    "parmesan": "parmesan",
    "mozzarella": "mozzarella",
    "yaourt": "yaourt",
    "yogourt": "yaourt",
    # Condiments et herbes
    "sel": "sel",
    "poivre": "poivre",
    "huile d'olive": "huile d'olive",
    "huile olive": "huile d'olive",
    "huile": "huile végétale",
    "vinaigre": "vinaigre",
    "vinaigre balsamique": "vinaigre (balsamique)",
    "moutarde": "moutarde",
    "sucre": "sucre",
    "thym": "thym",
    "romarin": "romarin",
    "persil": "persil",
    "basilic": "basilic",
    "laurier": "laurier",
    "origan": "origan",
    "cumin": "cumin",
    "paprika": "paprika",
    "curry": "curry",
    "gingembre": "gingembre",
    "curcuma": "curcuma",
    "cannelle": "cannelle",
    # Liquides
    "eau": "eau",
    "bouillon": "bouillon",
    "bouillon de poulet": "bouillon (poulet)",
    "bouillon de légumes": "bouillon (légumes)",
    "vin blanc": "vin blanc",
    "vin rouge": "vin rouge",
    # Fruits
    "citron": "citron",
    "orange": "orange",
    "pomme": "pomme",
    "poire": "poire",
    "banane": "banane",
    "fraise": "fraise",
    "fraises": "fraise",
}

# Catégories d'ingrédients pour le mapping Open Food Facts (Phase 1)
INGREDIENT_CATEGORIES: dict[str, str] = {
    "poulet": "viandes_volailles",
    "poulet (blanc)": "viandes_volailles",
    "poulet (cuisse)": "viandes_volailles",
    "poule": "viandes_volailles",
    "boeuf": "viandes_rouges",
    "veau": "viandes_rouges",
    "porc": "charcuterie",
    "lardons": "charcuterie",
    "bacon": "charcuterie",
    "jambon": "charcuterie",
    "jambon (blanc)": "charcuterie",
    "jambon (cru)": "charcuterie",
    "saumon": "poissons_fruits_de_mer",
    "saumon (fumé)": "poissons_fruits_de_mer",
    "thon": "poissons_fruits_de_mer",
    "crevettes": "poissons_fruits_de_mer",
    "oignon": "légumes",
    "échalote": "légumes",
    "ail": "légumes",
    "tomate": "légumes",
    "carotte": "légumes",
    "pomme de terre": "légumes",
    "courgette": "légumes",
    "aubergine": "légumes",
    "poivron": "légumes",
    "champignon": "légumes",
    "épinard": "légumes",
    "salade": "légumes",
    "brocoli": "légumes",
    "farine (T55)": "épicerie",
    "farine (T45)": "épicerie",
    "pâtes": "épicerie",
    "riz": "épicerie",
    "pain": "boulangerie",
    "beurre": "produits_laitiers",
    "crème fraîche": "produits_laitiers",
    "crème liquide": "produits_laitiers",
    "lait": "produits_laitiers",
    "oeuf": "oeufs",
    "fromage": "fromages",
    "gruyère": "fromages",
    "emmental": "fromages",
    "parmesan": "fromages",
    "mozzarella": "fromages",
    "yaourt": "produits_laitiers",
    "sel": "épices_condiments",
    "poivre": "épices_condiments",
    "huile d'olive": "huiles",
    "huile végétale": "huiles",
    "sucre": "épicerie",
    "citron": "fruits",
    "orange": "fruits",
    "pomme": "fruits",
    "banane": "fruits",
    "fraise": "fruits",
}


def _extract_quantity_and_unit(text: str) -> tuple[float | None, str | None, str]:
    """
    Extrait la quantité et l'unité d'une chaîne d'ingrédient.

    Exemples :
    - "200g de farine" → (200.0, "g", "farine")
    - "2 oeufs" → (2.0, "u", "oeufs")
    - "1/2 oignon" → (0.5, "u", "oignon")
    - "une pincée de sel" → (None, "pincée", "sel")
    - "sel" → (None, None, "sel")

    Args:
        text: Ligne brute de l'ingrédient.

    Returns:
        Tuple (quantité, unité canonique, reste du texte sans quantité/unité).
    """
    text = text.strip()

    # Supprimer les articles et prépositions communes au début
    text = re.sub(r"^\s*(de |d'|du |des |le |la |les |un |une )", "", text, flags=re.IGNORECASE)

    # Format : "1/2" ou "1/4" → fraction décimale
    fraction_match = re.match(r"^(\d+)\s*/\s*(\d+)\s*(.*)", text)
    if fraction_match:
        qty = int(fraction_match.group(1)) / int(fraction_match.group(2))
        rest = fraction_match.group(3)
        # Essayer d'extraire l'unité du reste
        unit, name = _extract_unit(rest)
        return qty, unit, name

    # Format : "200g" ou "200 g" ou "2,5 kg"
    number_unit_match = re.match(
        r"^(\d+(?:[.,]\d+)?)\s*([a-zA-ZàâéèêëîïôùûüçÀÂÉÈÊËÎÏÔÙÛÜÇ\.]+)?\s*(.*)",
        text,
    )
    if number_unit_match:
        qty_str = number_unit_match.group(1).replace(",", ".")
        unit_raw = (number_unit_match.group(2) or "").strip().rstrip(".")
        rest = number_unit_match.group(3).strip()

        try:
            qty = float(qty_str)
        except ValueError:
            qty = None

        # Normaliser l'unité
        unit_lower = unit_raw.lower()
        canonical_unit = UNIT_MAPPING.get(unit_lower)

        if canonical_unit:
            # L'unité est reconnue, le reste est le nom de l'ingrédient
            name = re.sub(r"^\s*(de |d'|du |des )", "", rest, flags=re.IGNORECASE).strip()
        else:
            # L'unité n'est pas reconnue → probablement un nombre sans unité (ex: "2 oeufs")
            canonical_unit = "u"
            # Reconstituer le nom depuis unit_raw + rest
            name = (unit_raw + " " + rest).strip() if unit_raw else rest.strip()
            # Si le nom correspond à une unité connue dans UNIT_MAPPING, corriger
            for unit_key, unit_val in UNIT_MAPPING.items():
                if name.lower().startswith(unit_key):
                    canonical_unit = unit_val
                    name = name[len(unit_key):].strip()
                    name = re.sub(r"^\s*(de |d'|du |des )", "", name, flags=re.IGNORECASE)
                    break

        return qty, canonical_unit, name

    # Aucune quantité détectée
    return None, None, text


def _extract_unit(text: str) -> tuple[str | None, str]:
    """
    Extrait l'unité en début de texte.

    Args:
        text: Texte après la quantité.

    Returns:
        Tuple (unité canonique ou None, reste du texte).
    """
    text = text.strip()
    text_lower = text.lower()

    # Essayer de matcher chaque unité connue en début de chaîne
    # Trier par longueur décroissante pour éviter les matchs partiels
    sorted_units = sorted(UNIT_MAPPING.keys(), key=len, reverse=True)

    for unit_key in sorted_units:
        if text_lower.startswith(unit_key):
            canonical = UNIT_MAPPING[unit_key]
            rest = text[len(unit_key):].strip()
            rest = re.sub(r"^\s*(de |d'|du |des )", "", rest, flags=re.IGNORECASE).strip()
            return canonical, rest

    return "u", text


def _find_canonical_name(ingredient_text: str) -> tuple[str, str]:
    """
    Trouve le nom canonique d'un ingrédient et sa catégorie.

    Utilise le mapping INGREDIENT_SYNONYMS pour la correspondance.
    Si aucun synonyme ne correspond, retourne le texte nettoyé tel quel.

    Args:
        ingredient_text: Nom de l'ingrédient nettoyé.

    Returns:
        Tuple (canonical_name, category).
    """
    # Nettoyage : minuscules, suppression de la ponctuation
    cleaned = ingredient_text.lower().strip().rstrip(".,;:")

    # Recherche exacte d'abord
    if cleaned in INGREDIENT_SYNONYMS:
        canonical = INGREDIENT_SYNONYMS[cleaned]
        category = INGREDIENT_CATEGORIES.get(canonical, "autres")
        return canonical, category

    # Recherche par inclusion (ex: "blanc de poulet rôti" → "blanc de poulet")
    for synonym, canonical in INGREDIENT_SYNONYMS.items():
        if synonym in cleaned and len(synonym) > 3:  # Éviter les faux positifs courts
            category = INGREDIENT_CATEGORIES.get(canonical, "autres")
            return canonical, category

    # Aucun mapping trouvé : retourner le texte nettoyé avec catégorie "autres"
    logger.debug("ingredient_no_canonical_match", ingredient=cleaned)
    return cleaned, "autres"


def normalize_ingredient_line(raw_line: str) -> NormalizedIngredient:
    """
    Normalise une ligne brute d'ingrédient vers la structure canonique.

    C'est la fonction principale du normalizer, testable unitairement.

    Exemples :
    - "200g de farine T55" → NormalizedIngredient(canonical_name="farine (T55)", quantity=200, unit="g", category="épicerie")
    - "2 gousses d'ail" → NormalizedIngredient(canonical_name="ail", quantity=2, unit="gousse", category="légumes")
    - "sel et poivre" → NormalizedIngredient(canonical_name="sel", quantity=None, unit=None, category="épices_condiments")

    Args:
        raw_line: Ligne brute de l'ingrédient (ex: depuis Marmiton ou Spoonacular).

    Returns:
        NormalizedIngredient avec tous les champs normalisés.
    """
    if not raw_line or not raw_line.strip():
        return NormalizedIngredient(
            canonical_name="inconnu",
            quantity=None,
            unit=None,
            category="autres",
            raw_text=raw_line,
        )

    # Nettoyage initial
    line = raw_line.strip()
    # Supprimer les parenthèses contenant des conseils (ex: "oignon (finement émincé)")
    line = re.sub(r"\([^)]{1,50}\)", "", line).strip()
    # Supprimer les crochets
    line = re.sub(r"\[[^\]]{1,50}\]", "", line).strip()

    # Extraire quantité et unité
    quantity, unit, ingredient_text = _extract_quantity_and_unit(line)

    # Trouver le nom canonique
    canonical_name, category = _find_canonical_name(ingredient_text)

    return NormalizedIngredient(
        canonical_name=canonical_name,
        quantity=quantity,
        unit=unit,
        category=category,
        raw_text=raw_line,
    )


def normalize_recipe_ingredients(raw_lines: list[str]) -> list[NormalizedIngredient]:
    """
    Normalise toutes les lignes d'ingrédients d'une recette.

    Args:
        raw_lines: Liste des lignes brutes d'ingrédients.

    Returns:
        Liste de NormalizedIngredient, dans le même ordre que l'entrée.
    """
    normalized: list[NormalizedIngredient] = []

    for line in raw_lines:
        if not line.strip():
            continue

        ingredient = normalize_ingredient_line(line)
        normalized.append(ingredient)

        if ingredient.canonical_name == "inconnu":
            logger.warning(
                "ingredient_normalization_failed",
                raw_line=line[:100],
            )

    return normalized
