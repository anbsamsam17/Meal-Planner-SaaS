"""Estimation nutritionnelle locale des recettes par composition d'ingredients.

Utilise la classification par mots-cles (identique a classify_ingredients_local.py)
pour determiner la categorie de chaque ingredient, puis estime les macronutriments
par portion et classifie le style (proteine, leger, gourmand).

Aucune API externe requise -- fonctionne 100% hors ligne.

Usage :
    python scripts/estimate_nutrition_local.py
"""

from __future__ import annotations

import json
import os
from collections import Counter

import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "mealplanner_dev",
    "user": "mealplanner",
    "password": "mealplanner_dev_password",
}

OUTPUT_DIR = "scripts/migration"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "estimate_nutrition.sql")

# Tags de style (avec accents, alignes sur _STYLE_NORMALIZE dans plans.py)
TAG_PROTEINE = "protéiné"
TAG_LEGER = "léger"
TAG_GOURMAND = "gourmand"

# ---------------------------------------------------------------------------
# Mots-cles pour classifier les ingredients (copie de classify_ingredients_local.py)
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "herbs": [
        "sel", "poivre", "cumin", "paprika", "cannelle", "origan", "curry",
        "curcuma", "muscade", "clou de girofle", "cardamome", "coriandre",
        "piment", "safran", "vanille", "anis", "gingembre moulu",
        "herbes de provence", "ras el hanout", "cinq épices", "za'atar",
        "sumac", "fenugrec", "quatre-épices", "baies roses", "épice",
        "basilic", "thym", "romarin", "persil", "aneth", "ciboulette",
        "estragon", "sauge", "menthe", "cerfeuil", "laurier",
        "salt", "pepper", "cinnamon", "oregano", "basil", "thyme",
        "rosemary", "parsley", "chili", "turmeric", "nutmeg", "clove",
        "cardamom", "dill", "bay leaf", "saffron", "mint", "tarragon",
        "sage", "fennel seed", "mustard seed", "star anise", "allspice",
        "garni",
    ],
    "fish": [
        "saumon", "thon", "crevette", "moule", "cabillaud", "sardine",
        "truite", "lotte", "dorade", "sole", "colin",
        "anchois", "calmar", "poulpe", "huître", "homard", "crabe",
        "gambas", "langoustine", "coquille saint-jacques", "palourde",
        "merlu", "rouget", "maquereau", "espadon", "flétan",
        "salmon", "tuna", "shrimp", "prawn", "cod", "fish", "anchovy",
        "crab", "lobster", "mussel", "clam", "oyster", "squid", "octopus",
        "mackerel", "trout", "sea bass", "haddock",
    ],
    "meat": [
        "poulet", "boeuf", "bœuf", "porc", "agneau", "dinde", "canard",
        "jambon", "lardons", "lardon", "chorizo", "saucisse", "steak",
        "veau", "lapin", "merguez", "andouillette", "boudin", "chipolata",
        "escalope", "filet mignon", "gigot", "entrecôte",
        "tournedos", "rôti", "magret", "pintade", "caille",
        "foie", "gésier", "rillettes", "pâté", "coppa",
        "pancetta", "bresaola", "bacon", "saucisson",
        "mortadelle", "viande", "pilon",
        "chicken", "beef", "pork", "lamb", "turkey", "sausage",
        "mince", "veal", "duck", "ham", "salami", "prosciutto",
    ],
    "dairy": [
        "lait", "crème", "creme", "fromage", "beurre", "yaourt", "yogourt",
        "oeuf", "œuf", "oeufs", "œufs", "mascarpone", "ricotta",
        "mozzarella", "parmesan", "feta", "brie", "camembert", "gruyère",
        "gruyere", "comté", "comte", "emmental", "roquefort", "chèvre",
        "chevre", "crème fraîche", "creme fraiche", "reblochon",
        "raclette", "cream cheese", "gouda", "cheddar", "pecorino",
        "gorgonzola", "burrata", "halloumi",
        "milk", "cream", "cheese", "butter", "yogurt", "egg",
        "jaune d'oeuf", "blanc d'oeuf",
    ],
    "fruits": [
        "pomme", "banane", "orange", "citron", "poire", "fraise",
        "framboise", "raisin", "melon", "mangue", "ananas", "pêche",
        "peche", "prune", "cerise", "kiwi", "abricot", "figue",
        "myrtille", "mûre", "mure", "cassis", "groseille",
        "mandarine", "pamplemousse", "pastèque", "nectarine",
        "datte", "cranberry",
        "apple", "banana", "lemon", "strawberry", "blueberry",
        "raspberry", "grape", "mango", "pineapple", "peach",
        "plum", "cherry", "kiwi",
    ],
    "vegetables": [
        "carotte", "tomate", "oignon", "ail", "poireau", "poivron",
        "laitue", "concombre", "épinard", "epinard", "brocoli",
        "champignon", "céleri", "celeri", "gingembre", "avocat",
        "haricot vert", "haricots verts", "petit pois", "petits pois",
        "maïs", "courgette", "aubergine", "chou", "échalote",
        "echalote", "radis", "navet", "betterave", "asperge", "artichaut",
        "courge", "pomme de terre", "patate", "fenouil", "endive",
        "roquette", "cresson", "blette", "panais",
        "butternut", "potiron", "potimarron",
        "chou-fleur", "chou fleur",
        "olive", "câpre", "cornichon", "salade",
        "potato", "carrot", "onion", "garlic", "tomato", "pepper",
        "lettuce", "cucumber", "spinach", "broccoli", "mushroom",
        "avocado", "corn", "zucchini", "eggplant", "cabbage", "leek",
        "celery", "ginger", "pumpkin", "squash", "asparagus",
        "turnip", "beetroot", "radish",
    ],
    "legumes": [
        "lentille", "pois chiche", "haricot sec", "haricots secs",
        "haricot blanc", "haricots blancs", "haricot rouge",
        "haricots rouges", "flageolet", "fève", "feve", "pois cassé",
        "pois casse", "soja",
        "lentil", "chickpea", "bean", "black bean",
    ],
    "condiments": [
        "sauce", "moutarde", "ketchup", "mayonnaise", "sauce soja",
        "tabasco", "harissa", "sriracha",
        "concentré de tomate", "concentre de tomate",
        "nuoc mam", "vinaigre", "pesto",
        "soy sauce", "mustard", "worcestershire",
    ],
    "grains": [
        "farine", "sucre", "riz", "pâtes", "pates", "nouille",
        "pain", "huile", "miel", "sirop", "levure", "cacao",
        "chocolat", "lait de coco", "couscous", "semoule", "maïzena",
        "maizena", "chapelure", "panko", "tortilla",
        "pâte feuilletée", "pâte brisée", "pâte sablée",
        "bouillon", "fond de veau", "amande", "noix",
        "noisette", "pistache", "cacahuète",
        "sésame", "sesame", "polenta", "fécule", "fecule",
        "flocon", "avoine",
        "spaghetti", "penne", "fusilli", "tagliatelle", "linguine",
        "farfalle", "rigatoni", "macaroni", "lasagne", "gnocchi",
        "ravioli", "udon", "soba", "ramen", "vermicelle", "conchiglioni",
        "eau", "vin", "bière", "biere",
        "flour", "sugar", "rice", "pasta", "noodle", "bread", "oil",
        "honey", "syrup", "baking", "yeast", "cocoa",
        "chocolate", "coconut milk", "couscous", "semolina",
        "cornflour", "breadcrumb", "tortilla", "wrap", "water", "wine",
    ],
}


def classify_ingredient(name: str) -> str:
    """Classifie un ingredient par mots-cles."""
    n = name.lower().strip()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in n:
                return category
    return "other"


# ---------------------------------------------------------------------------
# Profils nutritionnels moyens par categorie (pour 100g)
# Sources : tables CIQUAL, USDA, moyennes arrondies
# ---------------------------------------------------------------------------
NUTRITION_PER_100G: dict[str, dict[str, float]] = {
    "meat":       {"calories": 180, "protein_g": 24.0, "fat_g":  9.0, "carbs_g":  0.0, "fiber_g": 0.0},
    "fish":       {"calories": 120, "protein_g": 21.0, "fat_g":  4.0, "carbs_g":  0.0, "fiber_g": 0.0},
    "dairy":      {"calories": 130, "protein_g":  8.0, "fat_g":  9.0, "carbs_g":  4.0, "fiber_g": 0.0},
    "vegetables": {"calories":  30, "protein_g":  1.5, "fat_g":  0.3, "carbs_g":  5.0, "fiber_g": 2.0},
    "fruits":     {"calories":  55, "protein_g":  0.8, "fat_g":  0.3, "carbs_g": 12.0, "fiber_g": 2.0},
    "grains":     {"calories": 300, "protein_g":  7.0, "fat_g":  3.0, "carbs_g": 60.0, "fiber_g": 3.0},
    "legumes":    {"calories": 130, "protein_g":  9.0, "fat_g":  0.5, "carbs_g": 20.0, "fiber_g": 7.0},
    "herbs":      {"calories":   5, "protein_g":  0.3, "fat_g":  0.1, "carbs_g":  0.5, "fiber_g": 0.2},
    "condiments": {"calories":  60, "protein_g":  1.0, "fat_g":  3.0, "carbs_g":  7.0, "fiber_g": 0.5},
    "other":      {"calories":  50, "protein_g":  1.5, "fat_g":  2.0, "carbs_g":  6.0, "fiber_g": 0.5},
}

# Poids moyen par unite (en grammes) — adapte a la cuisine francaise
UNIT_TO_GRAMS: dict[str, float] = {
    "g": 1.0,
    "kg": 1000.0,
    "ml": 1.0,
    "cl": 10.0,
    "l": 1000.0,
    "piece": 120.0,
    "pièce": 120.0,
    "pieces": 120.0,
    "pièces": 120.0,
    "unite": 120.0,
    "unité": 120.0,
    "unit": 120.0,
    "tranche": 30.0,
    "tranches": 30.0,
    "slice": 30.0,
    "cas": 15.0,              # cuillere a soupe
    "c. a soupe": 15.0,
    "cuillere a soupe": 15.0,
    "cuillère à soupe": 15.0,
    "cs": 15.0,
    "tbsp": 15.0,
    "tablespoon": 15.0,
    "c. a cafe": 5.0,
    "cuillere a cafe": 5.0,
    "cuillère à café": 5.0,
    "cc": 5.0,
    "tsp": 5.0,
    "teaspoon": 5.0,
    "cup": 240.0,
    "tasse": 240.0,
    "verre": 200.0,
    "pincee": 1.0,
    "pincée": 1.0,
    "pinch": 1.0,
    "gousse": 5.0,
    "brin": 2.0,
    "branche": 10.0,
    "feuille": 1.0,
    "feuilles": 1.0,
    "botte": 100.0,
    "bouquet": 30.0,
    "boite": 400.0,
    "boîte": 400.0,
    "can": 400.0,
    "sachet": 10.0,
    "paquet": 250.0,
    "filet": 150.0,
    "oz": 28.35,
    "lb": 453.6,
    "pound": 453.6,
    "poignee": 30.0,
    "poignée": 30.0,
    "cube": 10.0,
    "cubes": 10.0,
}

# Poids specifiques par categorie + unite "piece/unite"
# Ex: 1 unite de poulet (pilon) = 200g, 1 unite de tomate = 150g
CATEGORY_PIECE_WEIGHT: dict[str, float] = {
    "meat": 200.0,       # pilon, escalope, steak
    "fish": 150.0,       # filet de poisson
    "dairy": 60.0,       # oeuf, yaourt
    "vegetables": 150.0, # tomate, oignon, carotte
    "fruits": 130.0,     # pomme, orange
    "grains": 100.0,     # portion de pates, pain
    "legumes": 100.0,
    "herbs": 3.0,        # gousse d'ail, brin de thym
    "condiments": 15.0,  # cuillere de sauce
    "other": 50.0,
}


def quantity_to_grams(quantity: float, unit: str, category: str) -> float:
    """Convertit une quantite + unite en grammes, adapte a la categorie."""
    unit_lower = unit.lower().strip()

    # Si l'unite est "unite" ou "piece", utiliser le poids par categorie
    if unit_lower in ("unite", "unité", "unit", "piece", "pièce", "pieces", "pièces"):
        return quantity * CATEGORY_PIECE_WEIGHT.get(category, 80.0)

    factor = UNIT_TO_GRAMS.get(unit_lower, 50.0)
    return quantity * factor


def estimate_recipe_nutrition(
    ingredients: list[dict],
    servings: int,
) -> dict:
    """Estime les macronutriments par portion pour une recette."""
    total = {"calories": 0.0, "protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0, "fiber_g": 0.0}

    for ing in ingredients:
        category = ing["_category"]  # classification par mots-cles
        grams = quantity_to_grams(float(ing["quantity"]), ing["unit"], category)
        profile = NUTRITION_PER_100G.get(category, NUTRITION_PER_100G["other"])

        ratio = grams / 100.0
        for key in total:
            total[key] += profile[key] * ratio

    # Par portion
    servings = max(1, servings)
    return {
        "calories": round(total["calories"] / servings),
        "protein_g": round(total["protein_g"] / servings, 1),
        "fat_g": round(total["fat_g"] / servings, 1),
        "carbs_g": round(total["carbs_g"] / servings, 1),
        "fiber_g": round(total["fiber_g"] / servings, 1),
    }


def classify_style(
    ingredients: list[dict],
    nutrition: dict,
) -> dict[str, bool]:
    """Classifie le style de la recette."""
    categories = Counter(ing["_category"] for ing in ingredients)

    has_meat = categories.get("meat", 0) > 0
    has_fish = categories.get("fish", 0) > 0
    has_legumes = categories.get("legumes", 0) > 0
    veggie_count = categories.get("vegetables", 0) + categories.get("fruits", 0)
    dairy_count = categories.get("dairy", 0)

    protein_g = nutrition.get("protein_g", 0)
    calories = nutrition.get("calories", 0)
    fat_g = nutrition.get("fat_g", 0)

    # proteine : protein >= 20g/portion ET source de proteine identifiee
    is_proteine = protein_g >= 20 and (has_meat or has_fish or has_legumes)

    # leger : pas de viande, calories raisonnables, riche en legumes
    is_leger = (
        not has_meat
        and calories <= 500
        and fat_g <= 20
        and veggie_count >= 2
    )

    # gourmand : riche en lipides OU calories elevees avec viande
    is_gourmand = (
        (fat_g >= 20 and dairy_count >= 2)
        or (calories >= 550 and has_meat)
        or fat_g >= 25
    )

    return {
        "is_proteine": is_proteine,
        "is_leger": is_leger,
        "is_gourmand": is_gourmand,
    }


def main() -> None:
    """Point d'entree principal."""
    print("Connexion a la DB Docker dev locale...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 1. Charger les recettes
    print("Chargement des recettes (quality >= 0.6)...")
    cur.execute("""
        SELECT id, title, servings, tags
        FROM recipes
        WHERE quality_score >= 0.6
        ORDER BY title
    """)
    recipes = cur.fetchall()
    print(f"{len(recipes)} recettes trouvees.\n")

    # 2. Charger tous les ingredients en une requete
    recipe_ids = [str(r["id"]) for r in recipes]
    cur.execute("""
        SELECT
            ri.recipe_id,
            i.canonical_name,
            i.category,
            ri.quantity,
            ri.unit,
            ri.position
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = ANY(%s::uuid[])
        ORDER BY ri.recipe_id, ri.position
    """, (recipe_ids,))
    ingredient_rows = cur.fetchall()

    # Grouper par recipe_id + classifier par mots-cles
    ingredients_by_recipe: dict[str, list[dict]] = {}
    category_override_count = 0
    for row in ingredient_rows:
        rid = str(row["recipe_id"])
        if rid not in ingredients_by_recipe:
            ingredients_by_recipe[rid] = []

        d = dict(row)
        # Classifier par mots-cles (ignore la categorie DB qui peut etre "other")
        kw_category = classify_ingredient(d["canonical_name"])
        if kw_category != "other":
            d["_category"] = kw_category
            if d["category"] == "other":
                category_override_count += 1
        else:
            d["_category"] = d["category"]  # garder la categorie DB si mots-cles echouent

        ingredients_by_recipe[rid].append(d)

    cur.close()
    conn.close()

    recipes_with = sum(1 for r in recipes if str(r["id"]) in ingredients_by_recipe)
    print(f"Recettes avec ingredients : {recipes_with}")
    print(f"Recettes sans ingredients : {len(recipes) - recipes_with}")
    print(f"Ingredients reclassifies par mots-cles : {category_override_count}\n")

    # 3. Estimer nutrition + style
    all_results: list[dict] = []
    style_counts = Counter()

    for recipe in recipes:
        rid = str(recipe["id"])
        ingredients = ingredients_by_recipe.get(rid, [])

        if not ingredients:
            all_results.append({
                "id": rid,
                "title": recipe["title"],
                "tags": recipe["tags"] or [],
                "nutrition": {},
                "is_proteine": False,
                "is_leger": False,
                "is_gourmand": False,
            })
            continue

        nutrition = estimate_recipe_nutrition(ingredients, recipe["servings"])
        style = classify_style(ingredients, nutrition)

        if style["is_proteine"]:
            style_counts["protéiné"] += 1
        if style["is_leger"]:
            style_counts["léger"] += 1
        if style["is_gourmand"]:
            style_counts["gourmand"] += 1

        all_results.append({
            "id": rid,
            "title": recipe["title"],
            "tags": recipe["tags"] or [],
            "nutrition": nutrition,
            **style,
        })

    # 4. Generer le SQL
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Estimation nutritionnelle locale (categories ingredients + mots-cles)\n")
        f.write(f"-- {len(all_results)} recettes estimees\n")
        f.write("-- Genere par scripts/estimate_nutrition_local.py\n")
        f.write("--\n")
        f.write("-- Nutrition JSONB : calories, protein_g, carbs_g, fat_g, fiber_g\n")
        f.write(f"-- Tags de style : {TAG_PROTEINE}, {TAG_LEGER}, {TAG_GOURMAND}\n\n")
        f.write("BEGIN;\n\n")

        for result in all_results:
            title = result["title"].replace("'", "''")
            recipe_id = result["id"]

            if result["nutrition"]:
                nutrition_json = json.dumps(result["nutrition"], ensure_ascii=False)
                escaped = nutrition_json.replace("'", "''")
                f.write(f"-- {title}\n")
                f.write(f"UPDATE recipes SET nutrition = '{escaped}' WHERE id = '{recipe_id}';\n")

                style_tags = []
                if result["is_proteine"]:
                    style_tags.append(TAG_PROTEINE)
                if result["is_leger"]:
                    style_tags.append(TAG_LEGER)
                if result["is_gourmand"]:
                    style_tags.append(TAG_GOURMAND)

                for tag in style_tags:
                    f.write(
                        f"UPDATE recipes SET tags = array_cat(tags, ARRAY['{tag}']) "
                        f"WHERE id = '{recipe_id}' AND NOT ('{tag}' = ANY(tags));\n"
                    )
                f.write("\n")

        f.write("COMMIT;\n")

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"Fichier SQL genere : {OUTPUT_FILE}")
    print(f"Taille : {file_size / 1024:.1f} Ko\n")

    # 5. Stats
    estimated = sum(1 for r in all_results if r["nutrition"])
    print(f"--- RESULTATS ({len(all_results)} recettes) ---")
    print(f"  Avec nutrition estimee : {estimated}")
    print(f"  Sans ingredients (skip): {len(all_results) - estimated}\n")

    print("--- CLASSIFICATION STYLE ---")
    for style_name in ["protéiné", "léger", "gourmand"]:
        count = style_counts.get(style_name, 0)
        pct = count / estimated * 100 if estimated else 0
        bar = "#" * int(pct / 2)
        print(f"  {style_name:12s} : {count:4d} ({pct:5.1f}%) {bar}")

    # Stats nutrition moyennes
    if estimated > 0:
        avg_cal = sum(r["nutrition"].get("calories", 0) for r in all_results if r["nutrition"]) / estimated
        avg_prot = sum(r["nutrition"].get("protein_g", 0) for r in all_results if r["nutrition"]) / estimated
        avg_fat = sum(r["nutrition"].get("fat_g", 0) for r in all_results if r["nutrition"]) / estimated

        print(f"\n--- MOYENNES PAR PORTION ---")
        print(f"  Calories  : {avg_cal:.0f} kcal")
        print(f"  Proteines : {avg_prot:.1f} g")
        print(f"  Lipides   : {avg_fat:.1f} g")

    # Exemples
    print(f"\n--- EXEMPLES ---")
    for style_key, label in [("is_proteine", "PROTEINE"), ("is_leger", "LEGER"), ("is_gourmand", "GOURMAND")]:
        examples = [r for r in all_results if r.get(style_key) and r["nutrition"]][:5]
        print(f"\n  {label} ({style_counts.get(TAG_PROTEINE if style_key == 'is_proteine' else TAG_LEGER if style_key == 'is_leger' else TAG_GOURMAND, 0)}):")
        for ex in examples:
            n = ex["nutrition"]
            print(f"    - {ex['title']} ({n['calories']} kcal, {n['protein_g']}g prot, {n['fat_g']}g fat)")

    # Contre-exemples : recettes NON proteine avec viande/poisson dans le titre
    print(f"\n  NON-PROTEINE avec viande dans le titre (verification) :")
    for r in all_results:
        title_lower = r["title"].lower()
        has_meat_word = any(w in title_lower for w in ["poulet", "boeuf", "porc", "agneau", "saumon", "thon"])
        if has_meat_word and not r.get("is_proteine") and r["nutrition"]:
            n = r["nutrition"]
            print(f"    ! {r['title']} ({n['calories']} kcal, {n['protein_g']}g prot)")


if __name__ == "__main__":
    main()
