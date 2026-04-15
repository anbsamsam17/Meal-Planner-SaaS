"""Classification locale des ingrédients par mots-clés français.

Alternative au script LLM quand le quota Gemini est épuisé.
Utilise les mêmes mots-clés français que _smart_rayon() dans plans.py.

Usage :
    python scripts/classify_ingredients_local.py
"""

from __future__ import annotations

import os
from collections import Counter

import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "mealplanner_dev",
    "user": "mealplanner",
    "password": "mealplanner_dev_password",
}

OUTPUT_DIR = "scripts/migration"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "classify_ingredients.sql")

# ---------------------------------------------------------------------------
# Mots-clés français pour classifier les ingrédients
# Rayon → category mapping : Fruits & legumes→vegetables, etc.
# L'ORDRE est important : les catégories les plus spécifiques d'abord
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "herbs": [
        # Épices sèches
        "sel", "poivre", "cumin", "paprika", "cannelle", "origan", "curry",
        "curcuma", "muscade", "clou de girofle", "cardamome", "coriandre",
        "piment", "safran", "vanille", "anis", "gingembre moulu",
        "herbes de provence", "ras el hanout", "cinq épices", "za'atar",
        "sumac", "fenugrec", "quatre-épices", "baies roses",
        # Herbes fraîches
        "basilic", "thym", "romarin", "persil", "aneth", "ciboulette",
        "estragon", "sauge", "menthe", "cerfeuil", "laurier", "origan frais",
        # Anglais (TheMealDB)
        "salt", "pepper", "cumin", "paprika", "cinnamon", "oregano",
        "basil", "thyme", "rosemary", "parsley", "chili", "turmeric",
        "nutmeg", "clove", "cardamom", "coriander", "dill", "bay leaf",
        "saffron", "vanilla", "mint", "tarragon", "sage", "fennel seed",
        "mustard seed", "star anise", "allspice",
    ],
    "fish": [
        "saumon", "thon", "crevette", "moule", "cabillaud", "sardine",
        "truite", "lotte", "bar ", "dorade", "sole", "lieu ", "colin",
        "anchois", "calmar", "poulpe", "huître", "homard", "crabe",
        "gambas", "langoustine", "coquille saint-jacques", "palourde",
        "encornet", "bulot", "bigorneau", "merlu", "rouget", "maquereau",
        "espadon", "flétan",
        # Anglais
        "salmon", "tuna", "shrimp", "prawn", "cod", "fish", "anchovy",
        "crab", "lobster", "mussel", "clam", "oyster", "squid", "octopus",
        "sardine", "mackerel", "trout", "sea bass", "haddock",
    ],
    "meat": [
        "poulet", "bœuf", "boeuf", "porc", "agneau", "dinde", "canard",
        "jambon", "lardons", "lardon", "chorizo", "saucisse", "steak",
        "veau", "lapin", "merguez", "andouillette", "boudin", "chipolata",
        "escalope", "filet mignon", "gigot", "côte ", "entrecôte",
        "tournedos", "rôti", "magret", "pintade", "caille", "sanglier",
        "chevreuil", "foie", "gésier", "rillettes", "pâté", "coppa",
        "pancetta", "bresaola", "bacon", "saucisson", "cervelas",
        "mortadelle", "viande hachée", "viande",
        # Anglais
        "chicken", "beef", "pork", "lamb", "turkey", "bacon", "sausage",
        "mince", "veal", "duck", "ham", "salami", "prosciutto",
    ],
    "dairy": [
        "lait", "crème", "creme", "fromage", "beurre", "yaourt", "yogourt",
        "oeuf", "œuf", "oeufs", "œufs", "mascarpone", "ricotta",
        "mozzarella", "parmesan", "feta", "brie", "camembert", "gruyère",
        "gruyere", "comté", "comte", "emmental", "roquefort", "chèvre",
        "chevre", "crème fraîche", "creme fraiche", "faisselle",
        "petit-suisse", "reblochon", "beaufort", "saint-nectaire",
        "cantal", "mimolette", "raclette", "munster", "maroilles",
        "pont-l'évêque", "cream cheese", "gouda", "cheddar", "pecorino",
        "gorgonzola", "burrata", "halloumi", "cottage cheese",
        # Anglais
        "milk", "cream", "cheese", "butter", "yogurt", "egg",
    ],
    "fruits": [
        "pomme", "banane", "orange", "citron", "poire", "fraise",
        "framboise", "raisin", "melon", "mangue", "ananas", "pêche",
        "peche", "prune", "cerise", "kiwi", "abricot", "figue",
        "grenade", "litchi", "fruit de la passion", "papaye", "goyave",
        "myrtille", "mûre", "mure", "cassis", "groseille", "clémentine",
        "mandarine", "pamplemousse", "pastèque", "pasteque", "nectarine",
        "coing", "rhubarbe", "datte", "cranberry",
        # Anglais
        "apple", "banana", "orange", "lemon", "strawberry", "blueberry",
        "raspberry", "grape", "melon", "mango", "pineapple", "peach",
        "plum", "cherry", "kiwi",
    ],
    "vegetables": [
        "carotte", "tomate", "oignon", "ail", "poireau", "poivron",
        "laitue", "concombre", "épinard", "epinard", "brocoli",
        "champignon", "céleri", "celeri", "gingembre", "avocat",
        "haricot vert", "haricots verts", "petit pois", "petits pois",
        "maïs", "mais", "courgette", "aubergine", "chou", "échalote",
        "echalote", "radis", "navet", "betterave", "asperge", "artichaut",
        "courge", "pomme de terre", "patate", "fenouil", "endive",
        "mâche", "mache", "roquette", "cresson", "blette", "panais",
        "topinambour", "rutabaga", "butternut", "potiron", "potimarron",
        "chou-fleur", "chou fleur", "chou rouge", "chou vert",
        "chou de bruxelles", "bette", "cèpe", "cepe", "girolle",
        "pleurote", "shiitake", "olive", "câpre", "capre", "cornichon",
        "poivron rouge", "poivron vert", "salade", "laitue",
        # Anglais
        "potato", "carrot", "onion", "garlic", "tomato", "pepper",
        "lettuce", "cucumber", "spinach", "broccoli", "mushroom",
        "avocado", "corn", "zucchini", "eggplant", "cabbage", "leek",
        "celery", "ginger", "pumpkin", "squash", "asparagus", "artichoke",
        "turnip", "beetroot", "radish",
    ],
    "legumes": [
        "lentille", "pois chiche", "haricot sec", "haricots secs",
        "haricot blanc", "haricots blancs", "haricot rouge",
        "haricots rouges", "flageolet", "fève", "feve", "pois cassé",
        "pois casse", "mogette", "azuki", "mungo", "soja",
        # Anglais
        "lentil", "chickpea", "bean", "black bean",
    ],
    "condiments": [
        "sauce", "moutarde", "ketchup", "mayonnaise", "sauce soja",
        "sauce worcestershire", "tabasco", "harissa", "sriracha",
        "concentré de tomate", "concentre de tomate", "pâte de curry",
        "nuoc mam", "sauce hoisin", "sauce teriyaki", "vinaigre",
        "sauce barbecue", "sauce piquante", "tapenade",
        "sauce tomate", "coulis", "pesto",
        # Anglais
        "soy sauce", "ketchup", "mustard", "worcestershire",
    ],
    "grains": [
        "farine", "sucre", "riz", "pâtes", "pates", "nouille",
        "pain", "huile", "miel", "sirop", "levure", "cacao",
        "chocolat", "lait de coco", "couscous", "semoule", "maïzena",
        "maizena", "chapelure", "panko", "tortilla", "pâte feuilletée",
        "pate feuilletee", "pâte brisée", "pâte sablée", "fond de veau",
        "bouillon", "gélatine", "gelatine", "agar", "amande", "noix",
        "noisette", "pistache", "cacahuète", "cacahuete", "noix de cajou",
        "noix de coco", "sésame", "sesame", "graine de lin", "chia",
        "polenta", "arrow-root", "fécule", "fecule", "tapioca",
        "flocon d'avoine", "flocons d'avoine", "avoine", "müesli",
        "muesli", "corn flakes", "biscuit", "brioche", "croûton",
        "crouton", "cracker", "wrap", "galette de riz", "vermicelle",
        "spaghetti", "penne", "fusilli", "tagliatelle", "linguine",
        "farfalle", "rigatoni", "macaroni", "lasagne", "gnocchi",
        "ravioli", "udon", "soba", "ramen",
        "eau", "vin", "bière", "biere", "rhum", "cognac", "calvados",
        "grand marnier", "amaretto", "marsala", "porto", "cidre",
        # Anglais
        "flour", "sugar", "rice", "pasta", "noodle", "bread", "oil",
        "vinegar", "honey", "syrup", "baking", "yeast", "cocoa",
        "chocolate", "coconut milk", "couscous", "semolina",
        "cornflour", "breadcrumb", "tortilla", "wrap", "water", "wine",
    ],
}


def classify_ingredient(name: str) -> str:
    """Classifie un ingrédient par son nom canonique."""
    n = name.lower().strip()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in n:
                return category

    return "other"


def main() -> None:
    """Point d'entrée principal."""
    print("Connexion à la DB Docker dev locale...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT id, canonical_name, category FROM ingredients ORDER BY canonical_name")
    ingredients = cur.fetchall()
    print(f"{len(ingredients)} ingrédients trouvés.\n")

    # Stats avant
    before_counts = Counter(row["category"] for row in ingredients)
    print("Répartition AVANT :")
    for cat, count in before_counts.most_common():
        print(f"  {cat}: {count}")
    print()

    cur.close()
    conn.close()

    # Classifier chaque ingrédient
    results: list[tuple[str, str, str]] = []
    for ing in ingredients:
        new_cat = classify_ingredient(ing["canonical_name"])
        results.append((str(ing["id"]), ing["canonical_name"], new_cat))

    # Générer le SQL
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Classification locale des ingrédients (mots-clés français)\n")
        f.write(f"-- {len(results)} ingrédients classifiés\n")
        f.write("-- Généré par scripts/classify_ingredients_local.py\n\n")
        f.write("BEGIN;\n\n")

        for ingredient_id, name, category in results:
            escaped_name = name.replace("'", "''")
            f.write(f"-- {escaped_name}\n")
            f.write(
                f"UPDATE ingredients SET category = '{category}' "
                f"WHERE id = '{ingredient_id}';\n\n"
            )

        f.write("COMMIT;\n")

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"Fichier SQL généré : {OUTPUT_FILE}")
    print(f"Taille : {file_size / 1024:.1f} Ko\n")

    # Stats après
    after_counts = Counter(r[2] for r in results)
    valid_cats = ["vegetables", "fruits", "meat", "fish", "dairy", "grains",
                  "legumes", "condiments", "herbs", "other"]
    print(f"Résultats ({len(results)} ingrédients) :")
    print("-" * 45)
    for cat in valid_cats:
        count = after_counts.get(cat, 0)
        pct = count / len(results) * 100
        bar = "#" * int(pct / 2)
        print(f"  {cat:12s} : {count:4d} ({pct:5.1f}%) {bar}")
    print("-" * 45)

    other_before = before_counts.get("other", 0)
    other_after = after_counts.get("other", 0)
    print(f"\n  'other' avant : {other_before} -> apres : {other_after}")
    print(f"  Reclassifiés  : {other_before - other_after}")

    # Montrer les "other" restants
    remaining_other = [r[1] for r in results if r[2] == "other"]
    if remaining_other:
        print(f"\n  Ingrédients restant en 'other' ({len(remaining_other)}) :")
        for name in remaining_other[:30]:
            print(f"    - {name}")
        if len(remaining_other) > 30:
            print(f"    ... et {len(remaining_other) - 30} autres")


if __name__ == "__main__":
    main()
