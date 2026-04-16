"""Estimation nutritionnelle des recettes par LLM (Gemini 2.5 Flash).

Envoie les recettes (titre + liste d'ingredients) a Gemini en batches de 20
pour estimer les valeurs nutritionnelles par portion et classifier le style
(proteine, leger, gourmand).

Le script genere un fichier SQL avec :
- UPDATE nutrition JSONB pour chaque recette
- UPDATE tags TEXT[] pour ajouter les tags de style

Seules les recettes plat_principal avec quality_score >= 0.6 sont traitees.

Free tier Gemini 2.5 Flash : 20 req/jour -> batches de 20 recettes.

Usage :
    set GOOGLE_AI_API_KEY=...
    python scripts/estimate_nutrition_llm.py
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
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "estimate_nutrition.sql")

BATCH_SIZE = 40
MODEL = "gemini-2.5-flash"

# Tags de style ajoutes aux recettes selon la classification Gemini
TAG_PROTEINE = "protéiné"
TAG_LEGER = "léger"
TAG_GOURMAND = "gourmand"

# ---------------------------------------------------------------------------
# Prompt Gemini
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Tu es un nutritionniste expert. Pour chaque recette avec ses ingredients, estime les valeurs nutritionnelles PAR PORTION.

Reponds en JSON : un tableau d'objets avec les champs :
- index (int) : numero de la recette dans la liste
- calories (int) : estimation kcal par portion
- protein_g (float) : grammes de proteines par portion (1 decimale)
- carbs_g (float) : grammes de glucides par portion (1 decimale)
- fat_g (float) : grammes de lipides par portion (1 decimale)
- fiber_g (float) : grammes de fibres par portion (1 decimale)
- is_proteine (bool) : true si la recette est riche en proteines (>= 25g/portion ET les proteines sont le focus principal)
- is_leger (bool) : true si la recette est legere et healthy (<= 500 kcal, riche en legumes)
- is_gourmand (bool) : true si la recette est gourmande (riche, cremeuse, fromage, beurre)

Regles :
- Base tes estimations sur les quantites d'ingredients donnees
- Si pas de quantite claire, utilise des portions standards francaises
- "Pates a la Norma" : ~450 kcal, ~15g prot -> NOT proteine, IS leger si portions normales
- "Poulet grille" : ~350 kcal, ~40g prot -> IS proteine, IS leger
- "Gratin dauphinois" : ~450 kcal, ~15g prot, ~25g fat -> IS gourmand, NOT leger
- Une recette peut etre a la fois proteinee et legere (ex: poisson grille aux legumes)"""


def fetch_recipes_with_ingredients(
    cur: psycopg2.extras.RealDictCursor,
) -> list[dict]:
    """Charge les recettes plat_principal (quality >= 0.6) avec leurs ingredients."""
    # Charger les recettes
    cur.execute(
        """
        SELECT id, title, servings, tags
        FROM recipes
        WHERE quality_score >= 0.6
        ORDER BY title
        """
    )
    recipes = cur.fetchall()

    # Charger les ingredients pour chaque recette en une seule requete
    recipe_ids = [str(r["id"]) for r in recipes]
    if not recipe_ids:
        return []

    cur.execute(
        """
        SELECT
            ri.recipe_id,
            i.canonical_name,
            ri.quantity,
            ri.unit
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = ANY(%s::uuid[])
        ORDER BY ri.recipe_id, ri.position
        """,
        (recipe_ids,),
    )
    ingredient_rows = cur.fetchall()

    # Grouper les ingredients par recipe_id
    ingredients_by_recipe: dict[str, list[dict]] = {}
    for row in ingredient_rows:
        rid = str(row["recipe_id"])
        if rid not in ingredients_by_recipe:
            ingredients_by_recipe[rid] = []
        ingredients_by_recipe[rid].append({
            "canonical_name": row["canonical_name"],
            "quantity": float(row["quantity"]),
            "unit": row["unit"],
        })

    # Assembler les recettes avec leurs ingredients
    enriched = []
    for recipe in recipes:
        rid = str(recipe["id"])
        enriched.append({
            "id": rid,
            "title": recipe["title"],
            "servings": recipe["servings"],
            "tags": recipe["tags"] or [],
            "ingredients": ingredients_by_recipe.get(rid, []),
        })

    return enriched


def format_recipe_for_prompt(index: int, recipe: dict) -> str:
    """Formate une recette pour le prompt Gemini."""
    lines = [f"{index}. {recipe['title']} ({recipe['servings']} portions)"]
    for ing in recipe["ingredients"]:
        qty = ing["quantity"]
        # Afficher sans decimale si c'est un entier
        qty_str = str(int(qty)) if qty == int(qty) else f"{qty:.1f}"
        lines.append(f"   - {ing['canonical_name']} : {qty_str} {ing['unit']}")
    if not recipe["ingredients"]:
        lines.append("   (pas d'ingredients details)")
    return "\n".join(lines)


def estimate_batch(
    client: genai.Client,
    batch: list[dict],
    batch_num: int,
    total_batches: int,
) -> list[dict]:
    """Envoie un batch de recettes a Gemini et parse la reponse JSON."""
    # Construire le prompt avec titres + ingredients
    recipe_blocks = []
    for i, recipe in enumerate(batch):
        recipe_blocks.append(format_recipe_for_prompt(i, recipe))

    prompt = (
        "Estime les valeurs nutritionnelles par portion pour ces recettes :\n\n"
        + "\n\n".join(recipe_blocks)
    )

    print(
        f"  Batch {batch_num}/{total_batches} ({len(batch)} recettes)...",
        end=" ",
        flush=True,
    )

    # Retry avec backoff en cas de rate limit
    max_retries = 3
    response = None
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
                wait = 60 * (attempt + 1)
                print(f"rate limit, retry in {wait}s...", end=" ", flush=True)
                time.sleep(wait)
            else:
                raise

    if response is None:
        print("ERREUR: pas de reponse")
        return _fallback_results(len(batch))

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
            return _fallback_results(len(batch))

    # Valider et normaliser
    validated = []
    for item in results:
        validated.append({
            "index": int(item.get("index", 0)),
            "calories": int(item.get("calories", 0)),
            "protein_g": round(float(item.get("protein_g", 0)), 1),
            "carbs_g": round(float(item.get("carbs_g", 0)), 1),
            "fat_g": round(float(item.get("fat_g", 0)), 1),
            "fiber_g": round(float(item.get("fiber_g", 0)), 1),
            "is_proteine": bool(item.get("is_proteine", False)),
            "is_leger": bool(item.get("is_leger", False)),
            "is_gourmand": bool(item.get("is_gourmand", False)),
        })

    print(f"OK ({len(validated)} resultats)")
    return validated


def _fallback_results(count: int) -> list[dict]:
    """Resultats par defaut en cas d'erreur API."""
    return [
        {
            "index": i,
            "calories": 0,
            "protein_g": 0.0,
            "carbs_g": 0.0,
            "fat_g": 0.0,
            "fiber_g": 0.0,
            "is_proteine": False,
            "is_leger": False,
            "is_gourmand": False,
        }
        for i in range(count)
    ]


def generate_sql(
    all_results: list[dict],
    output_file: str,
) -> None:
    """Genere le fichier SQL avec les UPDATEs nutrition + tags."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Estimation nutritionnelle LLM (Gemini 2.5 Flash)\n")
        f.write(f"-- {len(all_results)} recettes estimees\n")
        f.write("-- Genere par scripts/estimate_nutrition_llm.py\n")
        f.write("--\n")
        f.write("-- Nutrition JSONB : calories, protein_g, carbs_g, fat_g, fiber_g\n")
        f.write("-- Tags de style : proteine, leger, gourmand\n\n")
        f.write("BEGIN;\n\n")

        for result in all_results:
            recipe_id = result["id"]
            title = result["title"].replace("'", "''")
            nutrition = {
                "calories": result["calories"],
                "protein_g": result["protein_g"],
                "carbs_g": result["carbs_g"],
                "fat_g": result["fat_g"],
                "fiber_g": result["fiber_g"],
            }
            nutrition_json = json.dumps(nutrition, ensure_ascii=False)
            escaped_nutrition = nutrition_json.replace("'", "''")

            f.write(f"-- {title}\n")
            f.write(
                f"UPDATE recipes SET nutrition = '{escaped_nutrition}' "
                f"WHERE id = '{recipe_id}';\n"
            )

            # Tags de style
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
                    f"WHERE id = '{recipe_id}' "
                    f"AND NOT ('{tag}' = ANY(tags));\n"
                )

            f.write("\n")

        f.write("COMMIT;\n")


def main() -> None:
    """Point d'entree principal."""
    # Verifier la cle API
    api_key = os.getenv("GOOGLE_AI_API_KEY", "")
    if not api_key:
        print("ERREUR : GOOGLE_AI_API_KEY non definie.")
        print()
        print("Usage :")
        print("  set GOOGLE_AI_API_KEY=votre_cle_api")
        print("  python scripts/estimate_nutrition_llm.py")
        print()
        print("Pour obtenir une cle API Gemini gratuite :")
        print("  https://aistudio.google.com/app/apikey")
        return

    # Connexion DB
    print("Connexion a la DB Docker dev locale...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Charger les recettes avec ingredients
    print("Chargement des recettes plat_principal (quality >= 0.6)...")
    recipes = fetch_recipes_with_ingredients(cur)
    print(f"{len(recipes)} recettes trouvees.\n")

    if not recipes:
        print("Aucune recette a traiter.")
        cur.close()
        conn.close()
        return

    # Stats ingredients
    total_ingredients = sum(len(r["ingredients"]) for r in recipes)
    avg_ingredients = total_ingredients / len(recipes) if recipes else 0
    print(f"Total ingredients : {total_ingredients}")
    print(f"Moyenne par recette : {avg_ingredients:.1f}\n")

    cur.close()
    conn.close()

    # Client Gemini
    client = genai.Client(api_key=api_key)

    # Decouper en batches
    batches: list[list[dict]] = []
    for i in range(0, len(recipes), BATCH_SIZE):
        batches.append(recipes[i : i + BATCH_SIZE])

    total_batches = len(batches)
    print(f"Estimation en {total_batches} batches de {BATCH_SIZE} max")
    print(f"Appels API Gemini : {total_batches} (free tier : 20/jour)\n")

    # Estimer chaque batch
    all_results: list[dict] = []

    for batch_num, batch in enumerate(batches, 1):
        estimated = estimate_batch(client, batch, batch_num, total_batches)

        # Mapper les resultats aux recettes du batch
        for item in estimated:
            idx = item["index"]
            if 0 <= idx < len(batch):
                recipe = batch[idx]
                all_results.append({
                    "id": recipe["id"],
                    "title": recipe["title"],
                    "calories": item["calories"],
                    "protein_g": item["protein_g"],
                    "carbs_g": item["carbs_g"],
                    "fat_g": item["fat_g"],
                    "fiber_g": item["fiber_g"],
                    "is_proteine": item["is_proteine"],
                    "is_leger": item["is_leger"],
                    "is_gourmand": item["is_gourmand"],
                })

        # Respecter le rate limit (5 secondes entre chaque batch)
        if batch_num < total_batches:
            print("  Attente 5s (rate limit)...")
            time.sleep(5)

    # Generer le SQL
    generate_sql(all_results, OUTPUT_FILE)

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"\nFichier SQL genere : {OUTPUT_FILE}")
    print(f"Taille : {file_size / 1024:.1f} Ko")

    # Stats
    proteine_count = sum(1 for r in all_results if r["is_proteine"])
    leger_count = sum(1 for r in all_results if r["is_leger"])
    gourmand_count = sum(1 for r in all_results if r["is_gourmand"])
    total = len(all_results)

    print(f"\n--- STATS nutrition ({total} recettes) ---")

    if total > 0:
        avg_cal = sum(r["calories"] for r in all_results) / total
        avg_prot = sum(r["protein_g"] for r in all_results) / total
        avg_carbs = sum(r["carbs_g"] for r in all_results) / total
        avg_fat = sum(r["fat_g"] for r in all_results) / total
        avg_fiber = sum(r["fiber_g"] for r in all_results) / total

        print(f"  Calories moyennes : {avg_cal:.0f} kcal")
        print(f"  Proteines moyennes : {avg_prot:.1f} g")
        print(f"  Glucides moyens : {avg_carbs:.1f} g")
        print(f"  Lipides moyens : {avg_fat:.1f} g")
        print(f"  Fibres moyennes : {avg_fiber:.1f} g")

    print(f"\n--- STATS style ({total} recettes) ---")
    if total > 0:
        pct_p = proteine_count / total * 100
        pct_l = leger_count / total * 100
        pct_g = gourmand_count / total * 100
        print(f"  proteine  : {proteine_count:4d} ({pct_p:5.1f}%)")
        print(f"  leger     : {leger_count:4d} ({pct_l:5.1f}%)")
        print(f"  gourmand  : {gourmand_count:4d} ({pct_g:5.1f}%)")

    # Distribution calories
    if total > 0:
        cal_ranges = Counter()
        for r in all_results:
            cal = r["calories"]
            if cal < 300:
                cal_ranges["< 300 kcal"] += 1
            elif cal < 500:
                cal_ranges["300-499 kcal"] += 1
            elif cal < 700:
                cal_ranges["500-699 kcal"] += 1
            else:
                cal_ranges[">= 700 kcal"] += 1

        print(f"\n--- Distribution calories ---")
        for label in ["< 300 kcal", "300-499 kcal", "500-699 kcal", ">= 700 kcal"]:
            count = cal_ranges.get(label, 0)
            pct = count / total * 100
            bar = "#" * int(pct / 2)
            print(f"  {label:15s} : {count:4d} ({pct:5.1f}%) {bar}")

    print("\nTermine. Executez le SQL sur Supabase apres verification.")


if __name__ == "__main__":
    main()
