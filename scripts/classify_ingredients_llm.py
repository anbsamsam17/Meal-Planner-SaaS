"""Classification des ingredients par LLM (Gemini 2.5 Flash).

Envoie les noms canoniques des ingredients a Gemini en batches de 50 pour
classifier chaque ingredient dans la bonne categorie de supermarche.

Les ~919 ingredients avec category='other' viennent de TheMealDB sans
categorisation. Ce script les classifie en categories alignees sur le
frontend `IngredientCategory`.

Free tier Gemini : 15 req/min, 1500 req/jour.
~1000 ingredients / 50 par batch = ~20 appels -> largement dans les limites.

Usage :
    set GOOGLE_AI_API_KEY=...
    python scripts/classify_ingredients_llm.py
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter

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
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "classify_ingredients.sql")

BATCH_SIZE = 50
MODEL = "gemini-2.5-flash"

VALID_CATEGORIES = [
    "vegetables",
    "fruits",
    "meat",
    "fish",
    "dairy",
    "grains",
    "legumes",
    "condiments",
    "herbs",
    "other",
]

# ---------------------------------------------------------------------------
# Prompt Gemini
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Tu es un expert en cuisine francaise. Classifie chaque ingredient dans une categorie de supermarche.
Categories possibles : vegetables, fruits, meat, fish, dairy, grains, legumes, condiments, herbs, other.
- vegetables : tous les legumes frais (y compris champignons, ail, oignon, echalote)
- fruits : tous les fruits frais
- meat : viande, volaille, charcuterie
- fish : poisson, fruits de mer, crustaces
- dairy : lait, creme, fromage, beurre, yaourt, oeufs
- grains : pates, riz, farine, sucre, pain, cereales, huile, vinaigre, miel, chocolat, levure
- legumes : legumineuses seches (lentilles, pois chiches, haricots secs)
- condiments : sauces preparees, moutarde, ketchup, sauce soja, concentre de tomate
- herbs : toutes les epices et herbes (fraiches ou seches)
- other : uniquement si impossible a classer

Reponds en JSON : un tableau [{"index": 0, "category": "vegetables"}, ...]"""


def classify_batch(
    client: genai.Client,
    batch: list[dict],
    batch_num: int,
    total_batches: int,
) -> list[dict]:
    """Envoie un batch d'ingredients a Gemini et parse la reponse JSON."""
    lines = []
    for i, ingredient in enumerate(batch):
        lines.append(f"{i}. {ingredient['canonical_name']}")
    prompt = "Classifie ces ingredients :\n\n" + "\n".join(lines)

    print(f"  Batch {batch_num}/{total_batches} ({len(batch)} ingredients)...", end=" ", flush=True)

    # Retry avec backoff en cas de rate limit
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            break
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = 40 * (attempt + 1)
                print(f"rate limit, retry in {wait}s...", end=" ", flush=True)
                time.sleep(wait)
            else:
                raise

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
            # Fallback : tout en other
            results = [{"index": i, "category": "other"} for i in range(len(batch))]

    # Valider et normaliser
    validated = []
    for item in results:
        idx = item.get("index", 0)
        category = item.get("category", "other")

        if category not in VALID_CATEGORIES:
            category = "other"

        validated.append({
            "index": idx,
            "category": category,
        })

    print(f"OK ({len(validated)} resultats)")
    return validated


def main() -> None:
    """Point d'entree principal."""
    # Verifier la cle API
    api_key = os.getenv("GOOGLE_AI_API_KEY", "")
    if not api_key:
        print("ERREUR : GOOGLE_AI_API_KEY non definie.")
        print(
            "Usage : set GOOGLE_AI_API_KEY=... && python scripts/classify_ingredients_llm.py"
        )
        return

    # Connexion DB
    print("Connexion a la DB Docker dev locale...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT id, canonical_name, category FROM ingredients ORDER BY canonical_name")
    ingredients = cur.fetchall()
    print(f"{len(ingredients)} ingredients trouves.\n")

    # Stats avant classification
    before_counts = Counter(row["category"] for row in ingredients)
    print("Repartition actuelle :")
    for cat, count in before_counts.most_common():
        print(f"  {cat}: {count}")
    print()

    cur.close()
    conn.close()

    # Client Gemini
    client = genai.Client(api_key=api_key)

    # Decouper en batches
    batches: list[list[dict]] = []
    for i in range(0, len(ingredients), BATCH_SIZE):
        batches.append(ingredients[i : i + BATCH_SIZE])

    total_batches = len(batches)
    print(f"Classification en {total_batches} batches de {BATCH_SIZE} max")
    print(f"Appels API Gemini : {total_batches} (free tier : 1500/jour)\n")

    # Classifier chaque batch
    all_results: list[tuple[str, str, str]] = []  # (id, canonical_name, category)

    for batch_num, batch in enumerate(batches, 1):
        classified = classify_batch(client, batch, batch_num, total_batches)

        # Mapper les resultats aux ingredients du batch
        for item in classified:
            idx = item["index"]
            if 0 <= idx < len(batch):
                ingredient = batch[idx]
                all_results.append((
                    str(ingredient["id"]),
                    ingredient["canonical_name"],
                    item["category"],
                ))

        # Respecter le rate limit (15 req/min -> 4 secondes entre chaque)
        if batch_num < total_batches:
            time.sleep(4)

    # Generer le SQL
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Classification LLM (Gemini 2.5 Flash) des ingredients\n")
        f.write(f"-- {len(all_results)} ingredients classifies\n")
        f.write("-- Genere par scripts/classify_ingredients_llm.py\n")
        f.write("--\n")
        f.write("-- Categories : vegetables, fruits, meat, fish, dairy,\n")
        f.write("--   grains, legumes, condiments, herbs, other\n\n")
        f.write("BEGIN;\n\n")

        for ingredient_id, canonical_name, category in all_results:
            escaped_name = canonical_name.replace("'", "''")
            f.write(f"-- {escaped_name}\n")
            f.write(
                f"UPDATE ingredients SET category = '{category}' "
                f"WHERE id = '{ingredient_id}';\n\n"
            )

        f.write("COMMIT;\n")

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"\nFichier SQL genere : {OUTPUT_FILE}")
    print(f"Taille : {file_size / 1024:.1f} Ko")

    # Stats apres classification
    after_counts = Counter(r[2] for r in all_results)
    print(f"\nResultats de classification ({len(all_results)} ingredients) :")
    print("-" * 40)
    for cat in VALID_CATEGORIES:
        count = after_counts.get(cat, 0)
        pct = count / len(all_results) * 100 if all_results else 0
        bar = "#" * int(pct / 2)
        print(f"  {cat:12s} : {count:4d} ({pct:5.1f}%) {bar}")
    print("-" * 40)
    print(f"  {'TOTAL':12s} : {len(all_results):4d}")

    # Comparer avant/apres pour 'other'
    other_before = before_counts.get("other", 0)
    other_after = after_counts.get("other", 0)
    reclassified = other_before - other_after
    print(f"\nIngredients reclassifies depuis 'other' : {reclassified}")
    print(f"  Avant : {other_before} en 'other'")
    print(f"  Apres : {other_after} en 'other'")


if __name__ == "__main__":
    main()
