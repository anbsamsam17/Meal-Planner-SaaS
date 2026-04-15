"""Classifie les recettes par course et cuisine_type via mots-cles.

Ce script :
1. Se connecte a la DB Docker dev locale pour lire les titres, tags et IDs
2. Applique des regles de classification basees sur les mots-cles
3. Genere un fichier SQL (scripts/migration/classify_recipes.sql) avec les UPDATE
4. Affiche des stats par categorie

Le fichier SQL genere est ensuite execute manuellement sur Supabase.
Le script ne modifie PAS la DB directement.

Usage :
    python scripts/classify_recipes.py
"""

from __future__ import annotations

import os
import re
from collections import Counter

import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Configuration DB Docker dev locale
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "mealplanner_dev",
    "user": "mealplanner",
    "password": "mealplanner_dev_password",
}

OUTPUT_DIR = "scripts/migration"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "classify_recipes.sql")

# ---------------------------------------------------------------------------
# Regles de classification `course` — par mots-cles dans le titre
# ---------------------------------------------------------------------------
# L'ordre est important : la premiere categorie qui matche gagne.
# "plat_principal" est le defaut si aucune regle ne matche.

COURSE_RULES: dict[str, list[str]] = {
    "dessert": [
        "gâteau",
        "gateau",
        "mousse au chocolat",
        "mousse chocolat",
        "mousse fraise",
        "mousse framboise",
        "mousse mangue",
        "mousse citron",
        "tiramisu",
        "fondant",
        "crème brûlée",
        "creme brulee",
        "crème caramel",
        "creme caramel",
        "crème dessert",
        "creme dessert",
        "flan",
        "clafoutis",
        "brownie",
        "cookie",
        "madeleine",
        "panna cotta",
        "île flottante",
        "ile flottante",
        "charlotte",
        "baba au rhum",
        "baba rhum",
        "éclair",
        "eclair au chocolat",
        "millefeuille",
        "mille-feuille",
        "profiterole",
        "cheesecake",
        "cheese cake",
        "banana bread",
        "bûche",
        "buche",
        "sorbet",
        "glace",
        "tarte au citron",
        "tarte citron",
        "tarte aux pommes",
        "tarte pommes",
        "tarte tatin",
        "tarte au chocolat",
        "tarte chocolat",
        "tarte aux fraises",
        "tarte fraises",
        "tarte aux fruits",
        "tarte amandine",
        "tarte aux poires",
        "tarte à la banane",
        "tarte a la banane",
        "tarte aux abricots",
        "tarte aux cerises",
        "tartelette au citron",
        "tartelette citron",
        "tartelette aux fruits",
        "salade de fruits",
        "crêpes sucrées",
        "crêpe sucrée",
        "crepe sucree",
        "compote",
        "riz au lait",
        "pain perdu",
        "crumble",
        "churros",
    ],
    "boisson": [
        "smoothie",
        "jus de",
        "jus d'",
        "cocktail",
        "limonade",
        "thé glacé",
        "the glace",
        "chocolat chaud",
        "milkshake",
        "milk-shake",
        "mojito",
        "spritz",
        "sangria",
        "lassi",
    ],
    "accompagnement": [
        "frites",
        "purée de",
        "puree de",
        "purée d'",
        "puree d'",
        "riz nature",
        "riz pilaf",
        "riz basmati",
        "gratin dauphinois",
        "ratatouille",
        "haricots verts",
        "pommes de terre sautées",
        "pommes de terre rissolées",
        "pommes de terre au four",
        "carottes vichy",
        "carottes glacées",
        "carottes glacees",
        "légumes rôtis",
        "legumes rotis",
        "légumes grillés",
        "legumes grilles",
        "courgettes sautées",
        "courgettes sautees",
        "champignons sautés",
        "champignons sautes",
        "champignons poêlés",
        "champignons poeles",
        "épinards",
        "epinards",
        "poêlée de légumes",
        "poelee de legumes",
        "gratin de courgettes",
        "gratin de légumes",
        "gratin de chou-fleur",
    ],
    "entree": [
        "soupe",
        "velouté",
        "veloute",
        "potage",
        "salade composée",
        "salade cesar",
        "salade césar",
        "salade niçoise",
        "salade nicoise",
        "carpaccio",
        "tartare de saumon",
        "tartare de bœuf",
        "tartare de boeuf",
        "tartare de thon",
        "bruschetta",
        "gaspacho",
        "gazpacho",
        "terrine",
        "mousse de canard",
        "mousse de foie",
        "houmous",
        "hummus",
        "houmos",
        "verrine",
    ],
    "sauce_condiment": [
        "sauce ",
        "vinaigrette",
        "marinade",
        "pesto",
        "coulis",
        "mayonnaise",
        "mayo maison",
        "aïoli",
        "aioli",
        "béchamel",
        "bechamel",
        "nappage",
        "glaçage",
        "glacage",
        "chutney",
        "confiture",
    ],
    "pain_viennoiserie": [
        "pain ",
        "pain d'",
        "brioche",
        "focaccia",
        "naan",
        "croissant",
        "baguette",
    ],
    "petit_dejeuner": [
        "granola",
        "porridge",
        "pancake",
        "waffle",
        "gaufre",
        "muesli",
        "overnight oats",
        "açaï bowl",
        "acai bowl",
    ],
}

# Mots-cles qui EXCLUENT une classification dessert quand "tarte" est dans le titre
# (ex: "tarte aux poireaux" = plat principal, pas dessert)
TARTE_SALEE_KEYWORDS: list[str] = [
    "poireau",
    "oignon",
    "tomate",
    "saumon",
    "thon",
    "légume",
    "legume",
    "chèvre",
    "chevre",
    "épinard",
    "epinard",
    "courgette",
    "poulet",
    "jambon",
    "lardons",
    "champignon",
    "brocoli",
    "fromage",
    "provençale",
    "provencale",
    "lorraine",
    "maroilles",
    "salée",
    "salee",
]

# ---------------------------------------------------------------------------
# Regles de classification `cuisine_type` — par mots-cles titre + tags
# ---------------------------------------------------------------------------
# "française" est le defaut si aucune regle ne matche.

CUISINE_RULES: dict[str, list[str]] = {
    "italienne": [
        "pasta",
        "risotto",
        "penne",
        "spaghetti",
        "spaghettis",
        "lasagne",
        "lasagnes",
        "gnocchi",
        "ravioli",
        "raviolis",
        "pizza",
        "osso buco",
        "tiramisu",
        "panna cotta",
        "bruschetta",
        "minestrone",
        "focaccia",
        "carbonara",
        "bolognaise",
        "bolognese",
        "pesto",
        "antipasti",
        "tagliatelle",
        "tagliatelles",
        "fettuccine",
        "calzone",
        "arancini",
    ],
    "japonaise": [
        "sushi",
        "ramen",
        "maki",
        "makis",
        "tempura",
        "teriyaki",
        "miso",
        "gyoza",
        "udon",
        "soba",
        "sashimi",
        "tonkatsu",
        "yakitori",
        "edamame",
        "onigiri",
        "katsu",
        "donburi",
    ],
    "mexicaine": [
        "tacos",
        "taco",
        "burrito",
        "enchilada",
        "guacamole",
        "quesadilla",
        "fajita",
        "nachos",
        "chili con carne",
    ],
    "indienne": [
        "curry",
        "tandoori",
        "naan",
        "biryani",
        "tikka",
        "masala",
        "samosa",
        "dal ",
        "dhal",
        "chapati",
        "korma",
        "vindaloo",
        "butter chicken",
    ],
    "thaïlandaise": [
        "pad thaï",
        "pad thai",
        "tom yum",
        "tom kha",
        "satay",
        "curry vert",
        "curry rouge",
        "curry jaune",
        "bo bun",
    ],
    "marocaine": [
        "tajine",
        "tagine",
        "couscous",
        "pastilla",
        "harira",
        "méchoui",
        "mechoui",
        "rfissa",
        "briouate",
    ],
    "libanaise": [
        "houmous",
        "hummus",
        "houmos",
        "taboulé",
        "taboule",
        "falafel",
        "chawarma",
        "shawarma",
        "kebbé",
        "kebbe",
        "fattouch",
        "fattoush",
        "mezze",
    ],
    "chinoise": [
        "wok",
        "chow mein",
        "dim sum",
        "lo mein",
        "sweet and sour",
        "riz cantonais",
        "porc laqué",
        "porc laque",
        "canard laqué",
        "canard laque",
        "bao",
        "chop suey",
        "nouilles chinoises",
        "nouilles sautées",
    ],
    "espagnole": [
        "paella",
        "gazpacho",
        "gaspacho",
        "tortilla española",
        "tortilla espagnole",
        "churros",
        "tapas",
        "croquetas",
    ],
    "américaine": [
        "burger",
        "bagel",
        "pancake",
        "cheesecake",
        "cheese cake",
        "brownie",
        "cookie",
        "hot dog",
        "hotdog",
        "bbq",
        "pulled pork",
        "wings",
        "coleslaw",
        "mac and cheese",
        "mac & cheese",
        "banana bread",
    ],
    "grecque": [
        "moussaka",
        "tzatziki",
        "souvlaki",
        "gyros",
    ],
}


# ---------------------------------------------------------------------------
# Logique de classification
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Normalise un texte pour le matching : minuscule, espaces unifies."""
    return re.sub(r"\s+", " ", text.lower().strip())


def classify_course(title: str) -> str:
    """Determine le `course` d'une recette a partir de son titre.

    Retourne une valeur parmi : plat_principal, accompagnement, dessert,
    boisson, entree, petit_dejeuner, pain_viennoiserie, sauce_condiment.
    """
    t = _normalize(title)

    # Cas special : "tarte" peut etre sucree (dessert) ou salee (plat principal)
    if "tarte" in t:
        is_salee = any(kw in t for kw in TARTE_SALEE_KEYWORDS)
        if is_salee:
            # C'est une tarte salee -> quiche/tarte = plat principal
            return "plat_principal"
        # Sinon on laisse le matching normal qui contient les tartes sucrees

    # Cas special : "crêpe" sans "sucrée" = plat principal (galette)
    if ("crêpe" in t or "crepe" in t) and "sucrée" not in t and "sucree" not in t:
        # Les crepes salees sont des plats principaux (galette complete, etc.)
        # On ne force pas dessert ici
        pass

    # Cas special : "salade" seule sans qualificatif = accompagnement
    # mais "salade composée/niçoise/cesar" = entree (gere par les regles entree)
    # et "salade de fruits" = dessert
    if "salade" in t:
        # "salade de fruits" est un dessert, pas un accompagnement
        if "salade de fruits" in t:
            return "dessert"
        # Verifier d'abord si c'est une salade composee (entree)
        for kw in COURSE_RULES["entree"]:
            if kw in t:
                return "entree"
        # Sinon salade simple = accompagnement
        return "accompagnement"

    for course, keywords in COURSE_RULES.items():
        for kw in keywords:
            if kw in t:
                return course

    return "plat_principal"


def classify_cuisine(title: str, tags: list[str]) -> str:
    """Determine le `cuisine_type` d'une recette a partir du titre et des tags.

    Retourne une valeur parmi les cles de CUISINE_RULES ou "française" par defaut.

    Strategie en 2 passes :
    1. Matcher sur le titre seul (haute confiance)
    2. Matcher sur titre + tags (plus large, mais certains mots-cles ambigus
       comme "curry" sont exclus du matching par tags pour eviter les faux positifs)
    """
    t = _normalize(title)

    # Passe 1 : titre seul — haute confiance
    for cuisine, keywords in CUISINE_RULES.items():
        for kw in keywords:
            if kw in t:
                return cuisine

    # Passe 2 : titre + tags — exclure les mots-cles ambigus quand ils
    # ne sont que dans les tags (ex: "curry" en epice != cuisine indienne)
    # Un tag "curry" seul ne suffit pas pour classifier comme indienne.
    ambiguous_in_tags_only = {"curry", "naan", "wok", "pesto"}
    combined = _normalize(title + " " + " ".join(tags))

    for cuisine, keywords in CUISINE_RULES.items():
        for kw in keywords:
            if kw in combined:
                # Si le keyword n'est que dans les tags (pas le titre),
                # et qu'il est ambigu, on l'ignore
                if kw not in t and kw in ambiguous_in_tags_only:
                    continue
                return cuisine

    return "française"


def sql_escape_str(value: str) -> str:
    """Echappe une string pour SQL (single quotes)."""
    return value.replace("'", "''")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Point d'entree principal."""
    print("Connexion a la DB Docker dev locale...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Lire toutes les recettes
    cur.execute("""
        SELECT id, title, cuisine_type, tags
        FROM recipes
        ORDER BY title
    """)
    recipes = cur.fetchall()
    print(f"{len(recipes)} recettes trouvees.\n")

    cur.close()
    conn.close()

    # Classifier chaque recette
    course_counts: Counter[str] = Counter()
    cuisine_counts: Counter[str] = Counter()
    sql_lines: list[str] = []

    for r in recipes:
        recipe_id = str(r["id"])
        title = r["title"] or ""
        tags = r["tags"] or []
        new_course = classify_course(title)
        new_cuisine = classify_cuisine(title, tags)

        course_counts[new_course] += 1
        cuisine_counts[new_cuisine] += 1

        # Generer le UPDATE SQL
        escaped_course = sql_escape_str(new_course)
        escaped_cuisine = sql_escape_str(new_cuisine)
        escaped_title = sql_escape_str(title)

        sql_lines.append(
            f"-- {escaped_title}\n"
            f"UPDATE recipes SET course = '{escaped_course}', "
            f"cuisine_type = '{escaped_cuisine}' "
            f"WHERE id = '{recipe_id}';"
        )

    # Ecrire le fichier SQL
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Classification des recettes : course + cuisine_type\n")
        f.write("-- Genere par scripts/classify_recipes.py\n")
        f.write(f"-- {len(recipes)} recettes classifiees\n")
        f.write("--\n")
        f.write("-- Valeurs course : plat_principal, accompagnement, dessert,\n")
        f.write("--   boisson, entree, petit_dejeuner, pain_viennoiserie, sauce_condiment\n")
        f.write("--\n")
        f.write("-- A executer APRES la migration 0009 (ajout colonne course)\n")
        f.write("-- et sur Supabase manuellement.\n\n")
        f.write("BEGIN;\n\n")
        for line in sql_lines:
            f.write(line + "\n\n")
        f.write("COMMIT;\n")

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"Fichier SQL genere : {OUTPUT_FILE}")
    print(f"Taille : {file_size / 1024:.1f} Ko")
    print(f"Nombre d'UPDATE : {len(sql_lines)}")

    # Stats
    print("\n--- STATS course ---")
    for course, count in course_counts.most_common():
        pct = count / len(recipes) * 100
        print(f"  {course:25s} : {count:4d} ({pct:5.1f}%)")

    print("\n--- STATS cuisine_type ---")
    for cuisine, count in cuisine_counts.most_common():
        pct = count / len(recipes) * 100
        print(f"  {cuisine:25s} : {count:4d} ({pct:5.1f}%)")

    print("\nTermine. Executez le SQL sur Supabase apres la migration 0009.")


if __name__ == "__main__":
    main()
