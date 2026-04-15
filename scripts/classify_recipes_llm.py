"""Classification des recettes par LLM (Gemini 2.0 Flash).

Envoie les titres des recettes à Gemini en batches de 30 pour classifier
chaque recette dans la bonne catégorie `course` et `cuisine_type`.

Avantages vs mots-clés :
- Comprend le contexte (tarte aux poireaux = plat, tarte au citron = dessert)
- Distingue salé/sucré, sauce autonome vs plat en sauce
- Gère les ambiguïtés (crêpe = plat ou dessert selon le contexte)

Free tier Gemini : 15 req/min, 1500 req/jour.
338 recettes / 30 par batch = ~12 appels → largement dans les limites.

Usage :
    set GOOGLE_AI_API_KEY=...
    python scripts/classify_recipes_llm.py
"""

from __future__ import annotations

import json
import os
import time

import psycopg2
import psycopg2.extras
from google import genai
from google.genai import types

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
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "classify_recipes.sql")

BATCH_SIZE = 30
MODEL = "gemini-2.5-flash"

VALID_COURSES = [
    "plat_principal",
    "accompagnement",
    "dessert",
    "boisson",
    "entree",
    "petit_dejeuner",
    "pain_viennoiserie",
    "sauce_condiment",
]

VALID_CUISINES = [
    "française", "italienne", "espagnole", "grecque", "méditerranéenne",
    "japonaise", "chinoise", "thaïlandaise", "indienne", "mexicaine",
    "américaine", "britannique", "allemande", "marocaine", "libanaise",
    "vietnamienne", "coréenne", "turque", "brésilienne",
    "internationale",
]

# ---------------------------------------------------------------------------
# Prompt Gemini
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Tu es un expert culinaire français. Tu dois classifier des recettes.

Pour chaque recette, détermine :
1. `course` — le type de plat. Valeurs EXACTES autorisées :
   - plat_principal : un vrai repas complet (viande/poisson/plat végétarien avec accompagnement intégré, quiche, pizza, gratin complet, pâtes, curry, etc.)
   - accompagnement : un plat qui accompagne un plat principal (frites, riz, purée, légumes seuls, gratin de légumes seul)
   - dessert : tout ce qui est sucré en fin de repas (gâteau, tarte sucrée, mousse chocolat, crème, glace, fruit préparé, crêpe sucrée)
   - boisson : smoothie, jus, cocktail, chocolat chaud, thé, café
   - entree : soupe, velouté, salade composée, carpaccio, tartare, bruschetta, verrine
   - petit_dejeuner : granola, porridge, pancake, gaufre, overnight oats
   - pain_viennoiserie : pain, brioche, focaccia, naan, croissant
   - sauce_condiment : sauce, vinaigrette, pesto, coulis, mayonnaise, confiture, chutney

2. `cuisine_type` — l'origine culinaire. Valeurs autorisées :
   française, italienne, espagnole, grecque, méditerranéenne, japonaise, chinoise, thaïlandaise, indienne, mexicaine, américaine, britannique, allemande, marocaine, libanaise, vietnamienne, coréenne, turque, brésilienne, internationale

Règles :
- Une tarte aux légumes/viande = plat_principal, une tarte aux fruits/chocolat = dessert
- Une crêpe sans précision ou salée = plat_principal, une crêpe sucrée = dessert
- Un gratin avec viande/poisson = plat_principal, un gratin de légumes seul = accompagnement
- "Poulet sauce tomate" = plat_principal (pas sauce_condiment)
- La plupart des recettes françaises classiques (blanquette, boeuf bourguignon, pot-au-feu) = plat_principal + française
- Si la cuisine n'est pas clairement identifiable comme étrangère = française (c'est une base de recettes françaises)

Réponds UNIQUEMENT en JSON : un tableau d'objets avec les champs "index", "course", "cuisine_type".
Exemple : [{"index": 0, "course": "plat_principal", "cuisine_type": "française"}, ...]"""


def classify_batch(
    client: genai.Client,
    batch: list[dict],
    batch_num: int,
    total_batches: int,
) -> list[dict]:
    """Envoie un batch de recettes à Gemini et parse la réponse JSON."""
    # Construire la liste numérotée
    lines = []
    for i, recipe in enumerate(batch):
        lines.append(f"{i}. {recipe['title']}")
    prompt = "Classifie ces recettes :\n\n" + "\n".join(lines)

    print(f"  Batch {batch_num}/{total_batches} ({len(batch)} recettes)...", end=" ", flush=True)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    # Parser le JSON
    raw_text = response.text.strip()
    try:
        results = json.loads(raw_text)
    except json.JSONDecodeError:
        # Tenter d'extraire le JSON du texte
        start = raw_text.find("[")
        end = raw_text.rfind("]") + 1
        if start >= 0 and end > start:
            results = json.loads(raw_text[start:end])
        else:
            print(f"ERREUR JSON batch {batch_num}")
            # Fallback : tout en plat_principal/française
            results = [
                {"index": i, "course": "plat_principal", "cuisine_type": "française"}
                for i in range(len(batch))
            ]

    # Valider et normaliser
    validated = []
    for item in results:
        idx = item.get("index", 0)
        course = item.get("course", "plat_principal")
        cuisine = item.get("cuisine_type", "française")

        # Valider les valeurs
        if course not in VALID_COURSES:
            course = "plat_principal"
        if cuisine not in VALID_CUISINES:
            cuisine = "française"

        validated.append({
            "index": idx,
            "course": course,
            "cuisine_type": cuisine,
        })

    print(f"OK ({len(validated)} résultats)")
    return validated


def main() -> None:
    """Point d'entrée principal."""
    # Vérifier la clé API
    api_key = os.getenv("GOOGLE_AI_API_KEY", "")
    if not api_key:
        print("ERREUR : GOOGLE_AI_API_KEY non définie.")
        print("Usage : set GOOGLE_AI_API_KEY=... && python scripts/classify_recipes_llm.py")
        return

    # Connexion DB
    print("Connexion à la DB Docker dev locale...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT id, title FROM recipes ORDER BY title")
    recipes = cur.fetchall()
    print(f"{len(recipes)} recettes trouvées.\n")

    cur.close()
    conn.close()

    # Client Gemini
    client = genai.Client(api_key=api_key)

    # Découper en batches
    batches = []
    for i in range(0, len(recipes), BATCH_SIZE):
        batches.append(recipes[i : i + BATCH_SIZE])

    total_batches = len(batches)
    print(f"Classification en {total_batches} batches de {BATCH_SIZE} max")
    print(f"Appels API Gemini : {total_batches} (free tier : 1500/jour)\n")

    # Classifier chaque batch
    all_results: list[tuple[str, str, str, str]] = []  # (id, title, course, cuisine)

    for batch_num, batch in enumerate(batches, 1):
        classified = classify_batch(client, batch, batch_num, total_batches)

        # Mapper les résultats aux recettes du batch
        for item in classified:
            idx = item["index"]
            if 0 <= idx < len(batch):
                recipe = batch[idx]
                all_results.append((
                    str(recipe["id"]),
                    recipe["title"],
                    item["course"],
                    item["cuisine_type"],
                ))

        # Respecter le rate limit (15 req/min → 4 secondes entre chaque)
        if batch_num < total_batches:
            time.sleep(4)

    # Générer le SQL
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Classification LLM (Gemini 2.0 Flash) des recettes\n")
        f.write(f"-- {len(all_results)} recettes classifiées\n")
        f.write("-- Généré par scripts/classify_recipes_llm.py\n")
        f.write("--\n")
        f.write("-- Valeurs course : plat_principal, accompagnement, dessert,\n")
        f.write("--   boisson, entree, petit_dejeuner, pain_viennoiserie, sauce_condiment\n\n")
        f.write("BEGIN;\n\n")

        for recipe_id, title, course, cuisine in all_results:
            escaped_title = title.replace("'", "''")
            escaped_cuisine = cuisine.replace("'", "''")
            f.write(f"-- {escaped_title}\n")
            f.write(
                f"UPDATE recipes SET course = '{course}', "
                f"cuisine_type = '{escaped_cuisine}' "
                f"WHERE id = '{recipe_id}';\n\n"
            )

        f.write("COMMIT;\n")

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"\nFichier SQL généré : {OUTPUT_FILE}")
    print(f"Taille : {file_size / 1024:.1f} Ko")

    # Stats
    from collections import Counter

    course_counts = Counter(r[2] for r in all_results)
    cuisine_counts = Counter(r[3] for r in all_results)

    print(f"\n--- STATS course ({len(all_results)} recettes) ---")
    for course, count in course_counts.most_common():
        pct = count / len(all_results) * 100
        print(f"  {course:25s} : {count:4d} ({pct:5.1f}%)")

    print(f"\n--- STATS cuisine_type ---")
    for cuisine, count in cuisine_counts.most_common():
        pct = count / len(all_results) * 100
        print(f"  {cuisine:25s} : {count:4d} ({pct:5.1f}%)")

    print("\nTerminé. Exécutez le SQL sur Supabase après vérification.")


if __name__ == "__main__":
    main()
