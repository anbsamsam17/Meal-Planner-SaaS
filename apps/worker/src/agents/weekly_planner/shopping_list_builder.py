"""
ShoppingListBuilder — consolidation des ingrédients en liste de courses.

Ce module agrège les ingrédients de toutes les recettes sélectionnées,
les consolide (somme des quantités pour les ingrédients communs),
et les organise par rayon pour une expérience de shopping optimale.

Architecture v0 :
- Consolidation par canonical_name (pas de dedup sémantique)
- Conversion d'unités basique (g + g = g, mais pas g + kg automatique)
- Groupement par ingredient.category (rayon supermarché)
- Exclusion simple des ingrédients du frigo (intersection exacte)

Groupes de rayons (alignés avec la présentation dans l'app) :
1. fruits_legumes : fruits, légumes, herbes fraîches
2. viandes_poissons : viandes, poissons, charcuterie
3. produits_laitiers : lait, fromage, œufs, beurre
4. epicerie_seche : pâtes, riz, conserves, huile, épices
5. surgeles : légumes surgelés, glaces
6. autres : tout ce qui ne rentre pas dans les catégories précédentes
"""

from collections import defaultdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ---- Constantes de groupement par rayon ----

CATEGORY_TO_RAYON: dict[str, str] = {
    # Fruits et légumes
    "fruits": "fruits_legumes",
    "légumes": "fruits_legumes",
    "herbes": "fruits_legumes",
    "aromates": "fruits_legumes",
    "champignons": "fruits_legumes",
    # Viandes et poissons
    "viande": "viandes_poissons",
    "viandes": "viandes_poissons",
    "poisson": "viandes_poissons",
    "poissons": "viandes_poissons",
    "charcuterie": "viandes_poissons",
    "volaille": "viandes_poissons",
    # Produits laitiers (BOF)
    "laitier": "produits_laitiers",
    "fromage": "produits_laitiers",
    "lait": "produits_laitiers",
    "œufs": "produits_laitiers",
    "beurre": "produits_laitiers",
    "crème": "produits_laitiers",
    # Épicerie sèche
    "épicerie": "epicerie_seche",
    "pâtes": "epicerie_seche",
    "riz": "epicerie_seche",
    "céréales": "epicerie_seche",
    "conserves": "epicerie_seche",
    "huile": "epicerie_seche",
    "épices": "epicerie_seche",
    "condiments": "epicerie_seche",
    "farine": "epicerie_seche",
    "sucre": "epicerie_seche",
    # Surgelés
    "surgelé": "surgeles",
    "surgelés": "surgeles",
}

RAYON_ORDER = [
    "fruits_legumes",
    "viandes_poissons",
    "produits_laitiers",
    "epicerie_seche",
    "surgeles",
    "autres",
]


# ---- Conversions d'unités simples ----

# Facteurs de conversion : 1 unité_source = N unité_base
# Lecture : "1 kg = 1000 g", "1 cl = 10 ml", "1 l = 1000 ml"
UNIT_CONVERSIONS: dict[tuple[str, str], float] = {
    # Masse → grammes (unité de base : g)
    ("kg", "g"): 1000.0,
    ("mg", "g"): 0.001,
    # Volume → millilitres (unité de base : ml)
    ("cl", "ml"): 10.0,
    ("l", "ml"): 1000.0,
    ("dl", "ml"): 100.0,
}

# Unité de base pour chaque groupe de mesure
UNIT_BASE: dict[str, str] = {
    "g": "g",
    "kg": "g",
    "mg": "g",
    "ml": "ml",
    "cl": "ml",
    "l": "ml",
    "dl": "ml",
}


def _normalize_unit(quantity: Decimal, unit: str) -> tuple[Decimal, str]:
    """
    Normalise une quantité vers l'unité de base de son groupe.

    Exemples :
    - (500, 'g') → (500, 'g')
    - (1.5, 'kg') → (1500, 'g')
    - (25, 'cl') → (250, 'ml')
    - (2, 'l') → (2000, 'ml')

    Args:
        quantity: Quantité brute.
        unit: Unité brute (insensible à la casse).

    Returns:
        Tuple (quantité normalisée, unité de base).
    """
    unit_lower = unit.lower().strip()
    base_unit = UNIT_BASE.get(unit_lower)

    if base_unit is None:
        # Unité inconnue → conserver telle quelle
        return quantity, unit

    if base_unit == unit_lower:
        # Déjà dans l'unité de base — pas de conversion nécessaire
        return quantity, unit

    # Facteur de conversion : 1 unit_lower = factor * base_unit
    factor = UNIT_CONVERSIONS.get((unit_lower, base_unit), 1.0)
    return Decimal(str(float(quantity) * factor)), base_unit


def _denormalize_quantity(quantity: Decimal, unit: str) -> str:
    """
    Reformate une quantité pour l'affichage.

    Exemples :
    - (1500, 'g') → '1.5 kg' si >= 1000g
    - (250, 'ml') → '25 cl'

    Args:
        quantity: Quantité normalisée.
        unit: Unité de base.

    Returns:
        Chaîne lisible pour l'affichage.
    """
    qty_float = float(quantity)

    if unit == "g" and qty_float >= 1000:
        return f"{qty_float / 1000:.2g} kg"
    if unit == "ml" and qty_float >= 1000:
        return f"{qty_float / 100:.2g} cl" if qty_float < 10000 else f"{qty_float / 1000:.2g} l"

    # Arrondi intelligent
    if qty_float == int(qty_float):
        return f"{int(qty_float)} {unit}"
    return f"{qty_float:.1f} {unit}"


def _get_rayon(category: str | None) -> str:
    """
    Mappe une catégorie d'ingrédient vers un rayon de supermarché.

    Args:
        category: Catégorie de l'ingrédient (depuis la table ingredients).

    Returns:
        Identifiant du rayon.
    """
    if not category:
        return "autres"

    category_lower = category.lower().strip()

    # Recherche exacte
    if category_lower in CATEGORY_TO_RAYON:
        return CATEGORY_TO_RAYON[category_lower]

    # Recherche partielle
    for key, rayon in CATEGORY_TO_RAYON.items():
        if key in category_lower or category_lower in key:
            return rayon

    return "autres"


async def build_shopping_list(
    session: AsyncSession,
    recipe_ids: list[str],
    household_id: UUID,
    num_persons: int = 4,
    include_fridge_exclusion: bool = True,
) -> list[dict[str, Any]]:
    """
    Construit la liste de courses consolidée depuis les recettes sélectionnées.

    Pipeline :
    1. Charge tous les ingrédients des recettes (avec quantités)
    2. Normalise les unités
    3. Consolide (somme) les ingrédients identiques
    4. Exclut les ingrédients présents dans le frigo (si include_fridge_exclusion)
    5. Groupe par rayon
    6. Retourne la liste triée par rayon (ordre logique supermarché)

    Args:
        session: Session SQLAlchemy async.
        recipe_ids: UUIDs des recettes sélectionnées.
        household_id: UUID du foyer (pour l'accès frigo).
        num_persons: Nombre de personnes (pour le scaling des portions).
        include_fridge_exclusion: True pour exclure les ingrédients déjà en stock.

    Returns:
        Liste de dicts structurée pour shopping_lists.items.
    """
    if not recipe_ids:
        return []

    # ---- Étape 1 : Chargement des ingrédients ----
    result = await session.execute(
        text(
            """
            SELECT
                i.id::text AS ingredient_id,
                i.canonical_name,
                i.category,
                i.off_id,
                ri.quantity,
                ri.unit,
                ri.recipe_id::text,
                r.servings AS recipe_servings
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            JOIN recipes r ON r.id = ri.recipe_id
            WHERE ri.recipe_id::text = ANY(:recipe_ids)
            ORDER BY i.canonical_name
            """
        ),
        {"recipe_ids": recipe_ids},
    )
    ingredient_rows = result.mappings().all()

    # ---- Étape 2 : Consolidation avec scaling des portions ----
    # Structure : {canonical_name: {unit_base: quantité_totale}}
    consolidated: dict[str, dict] = {}

    for row in ingredient_rows:
        canonical_name = row["canonical_name"]
        quantity_raw = Decimal(str(row["quantity"] or 0))
        unit = str(row["unit"] or "unité")
        recipe_servings = int(row["recipe_servings"] or 1)
        category = row.get("category")
        ingredient_id = row["ingredient_id"]
        off_id = row.get("off_id")

        # Scaling : adapter la quantité au nombre de personnes du foyer
        if recipe_servings > 0:
            scaling_factor = Decimal(str(num_persons)) / Decimal(str(recipe_servings))
            quantity_scaled = quantity_raw * scaling_factor
        else:
            quantity_scaled = quantity_raw

        # Normalisation de l'unité
        quantity_normalized, unit_base = _normalize_unit(quantity_scaled, unit)

        if canonical_name not in consolidated:
            consolidated[canonical_name] = {
                "ingredient_id": ingredient_id,
                "canonical_name": canonical_name,
                "category": category,
                "off_id": off_id,
                "quantities": defaultdict(Decimal),
            }

        consolidated[canonical_name]["quantities"][unit_base] += quantity_normalized

    # ---- Étape 3 : Exclusion des ingrédients du frigo ----
    fridge_exclusions: set[str] = set()
    if include_fridge_exclusion:
        fridge_result = await session.execute(
            text(
                """
                SELECT i.canonical_name
                FROM fridge_items fi
                JOIN ingredients i ON i.id = fi.ingredient_id
                WHERE fi.household_id = :household_id
                """
            ),
            {"household_id": str(household_id)},
        )
        fridge_items = fridge_result.fetchall()
        fridge_exclusions = {row[0] for row in fridge_items}

        if fridge_exclusions:
            logger.info(
                "shopping_list_fridge_exclusion",
                household_id=str(household_id),
                excluded_count=len(fridge_exclusions),
            )

    # ---- Étape 4 : Construction de la liste finale ----
    shopping_items: list[dict[str, Any]] = []

    for canonical_name, data in consolidated.items():
        # Exclusion frigo (mode anti-gaspi)
        if canonical_name in fridge_exclusions:
            logger.debug(
                "shopping_list_item_excluded_fridge",
                ingredient=canonical_name,
            )
            continue

        category = data.get("category")
        rayon = _get_rayon(category)

        # Formatage des quantités par unité
        quantities_display: list[dict] = []
        for unit_base, total_qty in data["quantities"].items():
            quantities_display.append(
                {
                    "quantity_display": _denormalize_quantity(total_qty, unit_base),
                    "quantity_value": float(total_qty),
                    "unit": unit_base,
                }
            )

        shopping_items.append(
            {
                "ingredient_id": data["ingredient_id"],
                "canonical_name": canonical_name,
                "category": category,
                "rayon": rayon,
                "off_id": data.get("off_id"),
                "quantities": quantities_display,
                "in_fridge": False,  # Ceux exclus ne sont pas dans la liste
                "checked": False,  # État de la liste partagée en temps réel
            }
        )

    # ---- Étape 5 : Tri par rayon (ordre logique supermarché) ----
    rayon_index = {rayon: i for i, rayon in enumerate(RAYON_ORDER)}
    shopping_items.sort(
        key=lambda item: (
            rayon_index.get(item["rayon"], len(RAYON_ORDER)),
            item["canonical_name"],
        )
    )

    logger.info(
        "shopping_list_built",
        household_id=str(household_id),
        total_items=len(shopping_items),
        recipes_count=len(recipe_ids),
        fridge_excluded=len(fridge_exclusions),
    )

    return shopping_items
