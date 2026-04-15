"""Export propre des recettes Docker dev → SQL pour Supabase.

Utilise psycopg2 pour lire les données natives (JSONB en dict Python,
arrays en list Python) et json.dumps() pour garantir du JSON valide.

Génère des fichiers SQL découpés, chacun < 800 Ko, prêts pour le SQL Editor Supabase.
"""

import json
import os
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


def sql_escape(value):
    """Échappe une valeur pour SQL single-quoted string."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    # Seul échappement nécessaire dans les strings SQL standard : ' → ''
    s = s.replace("'", "''")
    return f"'{s}'"


def _sanitize_jsonb_value(obj):
    """Nettoie récursivement les caractères problématiques dans un objet JSONB.

    Supprime les caractères de contrôle (0x00-0x1F sauf tab/newline),
    U+2028 (LINE SEPARATOR) et U+2029 (PARAGRAPH SEPARATOR) qui sont
    rejetés par le parser JSONB de PostgreSQL/Supabase.
    """
    if isinstance(obj, str):
        cleaned = []
        for ch in obj:
            code = ord(ch)
            if code == 0x0D:  # CR → skip
                continue
            if code == 0x2028 or code == 0x2029:  # LINE/PARAGRAPH SEP → space
                cleaned.append(" ")
            elif code < 0x20 and code not in (0x09, 0x0A):  # other control → skip
                continue
            else:
                cleaned.append(ch)
        return "".join(cleaned)
    if isinstance(obj, list):
        return [_sanitize_jsonb_value(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_jsonb_value(v) for k, v in obj.items()}
    return obj


def jsonb_escape(value):
    """Sérialise un dict/list Python en JSONB SQL valide."""
    if value is None:
        return "'{}'::jsonb"
    # Nettoyer les chars problématiques AVANT json.dumps
    value = _sanitize_jsonb_value(value)
    # json.dumps garantit du JSON valide (échappement correct de \, ", etc.)
    j = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    # Échapper les ' pour SQL
    j = j.replace("'", "''")
    return f"'{j}'::jsonb"


def array_escape(values):
    """Sérialise une liste Python en text[] SQL."""
    if not values:
        return "'{}'::text[]"
    escaped = []
    for v in values:
        v_str = str(v).replace("'", "''").replace('"', '\\"')
        escaped.append(f'"{v_str}"')
    arr = ",".join(escaped)
    return f"'{{{arr}}}'::text[]"


def vector_escape(vec_str):
    """Formate un vecteur pgvector pour SQL."""
    if vec_str is None:
        return "NULL"
    return f"'{vec_str}'::vector(384)"


def write_file(filepath, header, lines):
    """Écrit un fichier SQL avec header et contenu."""
    with open(filepath, "w", encoding="utf-8", newline="\n") as f:
        f.write(header)
        f.write("\n")
        for line in lines:
            f.write(line)
            f.write("\n")
    size = os.path.getsize(filepath)
    print(f"  {os.path.basename(filepath)}: {len(lines)} lignes, {size/1024:.0f} Ko")


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # =========================================================================
    # 01_prerequisites.sql — inchangé (déjà corrigé manuellement)
    # =========================================================================
    print("01_prerequisites.sql — conservé tel quel")

    # =========================================================================
    # 02_ingredients.sql
    # =========================================================================
    print("\nExport ingredients...")
    cur.execute("""
        SELECT id, canonical_name, category, unit_default,
               off_id, off_last_checked_at, off_match_confidence,
               off_product_name, off_brand, created_at
        FROM ingredients
        ORDER BY canonical_name
    """)
    rows = cur.fetchall()

    lines = []
    for r in rows:
        vals = (
            f"{sql_escape(str(r['id']))}"
            f", {sql_escape(r['canonical_name'])}"
            f", {sql_escape(r['category'])}"
            f", {sql_escape(r['unit_default'])}"
            f", {sql_escape(r['off_id'])}"
            f", {sql_escape(str(r['off_last_checked_at'])) if r['off_last_checked_at'] else 'NULL'}"
            f", {sql_escape(r['off_match_confidence'])}"
            f", {sql_escape(r['off_product_name'])}"
            f", {sql_escape(r['off_brand'])}"
            f", {sql_escape(str(r['created_at']))}"
        )
        lines.append(
            f"INSERT INTO public.ingredients (id, canonical_name, category, unit_default, "
            f"off_id, off_last_checked_at, off_match_confidence, off_product_name, off_brand, created_at) "
            f"VALUES ({vals}) ON CONFLICT (canonical_name) DO UPDATE SET id = EXCLUDED.id, "
            f"category = EXCLUDED.category, unit_default = EXCLUDED.unit_default;"
        )

    header = (
        "-- FICHIER 02/07 — ingredients ({} lignes)\n"
        "-- Exécuter APRÈS 01_prerequisites.sql\n"
        "SET session_replication_role = replica;\n"
    ).format(len(lines))
    write_file(f"{OUTPUT_DIR}/02_ingredients.sql", header, lines)

    # =========================================================================
    # 03_recipes.sql
    # =========================================================================
    print("\nExport recipes...")
    cur.execute("""
        SELECT id, source, source_url, title, slug, description,
               instructions, servings, prep_time_min, cook_time_min,
               difficulty, cuisine_type, photo_url, nutrition, tags,
               quality_score, created_at, updated_at, language
        FROM recipes
        ORDER BY source, title
    """)
    rows = cur.fetchall()

    lines = []
    for r in rows:
        vals = (
            f"{sql_escape(str(r['id']))}"
            f", {sql_escape(r['source'])}"
            f", {sql_escape(r['source_url'])}"
            f", {sql_escape(r['title'])}"
            f", {sql_escape(r['slug'])}"
            f", {sql_escape(r['description'])}"
            f", {jsonb_escape(r['instructions'])}"
            f", {r['servings']}"
            f", {r['prep_time_min'] if r['prep_time_min'] is not None else 'NULL'}"
            f", {r['cook_time_min'] if r['cook_time_min'] is not None else 'NULL'}"
            f", {r['difficulty'] if r['difficulty'] is not None else 'NULL'}"
            f", {sql_escape(r['cuisine_type'])}"
            f", {sql_escape(r['photo_url'])}"
            f", {jsonb_escape(r['nutrition'])}"
            f", {array_escape(r['tags'])}"
            f", {r['quality_score']}"
            f", {sql_escape(str(r['created_at']))}"
            f", {sql_escape(str(r['updated_at']))}"
            f", {sql_escape(r['language'])}"
        )
        lines.append(
            f"INSERT INTO public.recipes (id, source, source_url, title, slug, description, "
            f"instructions, servings, prep_time_min, cook_time_min, difficulty, cuisine_type, "
            f"photo_url, nutrition, tags, quality_score, created_at, updated_at, language) "
            f"VALUES ({vals}) ON CONFLICT (slug) DO NOTHING;"
        )

    header = (
        "-- FICHIER 03/07 — recipes ({} lignes)\n"
        "-- Exécuter APRÈS 02_ingredients.sql\n"
        "SET session_replication_role = replica;\n"
    ).format(len(lines))
    write_file(f"{OUTPUT_DIR}/03_recipes.sql", header, lines)

    # =========================================================================
    # 04_recipe_ingredients.sql
    # =========================================================================
    print("\nExport recipe_ingredients...")
    cur.execute("""
        SELECT recipe_id, ingredient_id, quantity, unit, notes, position
        FROM recipe_ingredients
        ORDER BY recipe_id, position
    """)
    rows = cur.fetchall()

    lines = []
    for r in rows:
        vals = (
            f"{sql_escape(str(r['recipe_id']))}"
            f", {sql_escape(str(r['ingredient_id']))}"
            f", {r['quantity'] if r['quantity'] is not None else 'NULL'}"
            f", {sql_escape(r['unit'])}"
            f", {sql_escape(r['notes'])}"
            f", {r['position'] if r['position'] is not None else 'NULL'}"
        )
        lines.append(
            f"INSERT INTO public.recipe_ingredients (recipe_id, ingredient_id, quantity, "
            f"unit, notes, position) VALUES ({vals}) "
            f"ON CONFLICT (recipe_id, ingredient_id) DO NOTHING;"
        )

    header = (
        "-- FICHIER 04/07 — recipe_ingredients ({} lignes)\n"
        "-- Exécuter APRÈS 03_recipes.sql\n"
        "SET session_replication_role = replica;\n"
    ).format(len(lines))
    write_file(f"{OUTPUT_DIR}/04_recipe_ingredients.sql", header, lines)

    # =========================================================================
    # 05a/05b_recipe_embeddings.sql
    # =========================================================================
    print("\nExport recipe_embeddings...")
    # Use a regular cursor for vector data (RealDictCursor may not handle it)
    cur2 = conn.cursor()
    cur2.execute("""
        SELECT recipe_id, embedding::text, tags, total_time_min,
               difficulty, cuisine_type
        FROM recipe_embeddings
        ORDER BY recipe_id
    """)
    rows = cur2.fetchall()

    lines = []
    for r in rows:
        recipe_id, embedding, tags, total_time, difficulty, cuisine = r
        tags_sql = array_escape(tags) if tags else "NULL"
        lines.append(
            f"INSERT INTO public.recipe_embeddings (recipe_id, embedding, tags, "
            f"total_time_min, difficulty, cuisine_type) VALUES ("
            f"{sql_escape(str(recipe_id))}"
            f", '{embedding}'::vector(384)"
            f", {tags_sql}"
            f", {total_time if total_time is not None else 'NULL'}"
            f", {difficulty if difficulty is not None else 'NULL'}"
            f", {sql_escape(cuisine)}"
            f") ON CONFLICT (recipe_id) DO NOTHING;"
        )

    # Split embeddings if > 800 KB
    mid = len(lines) // 2
    part_a = lines[:mid]
    part_b = lines[mid:]

    header_a = (
        "-- FICHIER 05a/07 — recipe_embeddings PARTIE A ({} lignes)\n"
        "-- Exécuter APRÈS 04_recipe_ingredients.sql\n"
        "SET session_replication_role = replica;\n"
    ).format(len(part_a))
    write_file(f"{OUTPUT_DIR}/05a_recipe_embeddings.sql", header_a, part_a)

    header_b = (
        "-- FICHIER 05b/07 — recipe_embeddings PARTIE B ({} lignes)\n"
        "-- Exécuter APRÈS 05a_recipe_embeddings.sql\n"
        "SET session_replication_role = replica;\n"
    ).format(len(part_b))
    write_file(f"{OUTPUT_DIR}/05b_recipe_embeddings.sql", header_b, part_b)

    # =========================================================================
    # 06_verify.sql — inchangé
    # =========================================================================
    print("\n06_verify.sql — conservé tel quel")

    cur.close()
    cur2.close()
    conn.close()

    # =========================================================================
    # Validation : vérifier le JSON de 03_recipes.sql
    # =========================================================================
    print("\n--- VALIDATION JSON ---")
    with open(f"{OUTPUT_DIR}/03_recipes.sql", "r", encoding="utf-8") as f:
        data = f.read()

    import re
    matches = re.findall(r"'(\{.*?\})'::jsonb", data)
    errors = 0
    for i, m in enumerate(matches):
        try:
            json.loads(m.replace("''", "'"))
        except json.JSONDecodeError as e:
            errors += 1
            if errors <= 5:
                print(f"  ERREUR bloc {i}: {e}")
    # Also validate instruction arrays
    matches2 = re.findall(r"'(\[.*?\])'::jsonb", data)
    for i, m in enumerate(matches2):
        try:
            json.loads(m.replace("''", "'"))
        except json.JSONDecodeError as e:
            errors += 1
            if errors <= 5:
                print(f"  ERREUR instructions {i}: {e}")

    if errors == 0:
        print("  TOUTES les valeurs JSONB sont valides !")
    else:
        print(f"  {errors} erreur(s) JSON détectée(s)")

    # File sizes
    print("\n--- TAILLES FINALES ---")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith(".sql"):
            size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
            flag = " ⚠ >900KB" if size > 900_000 else ""
            print(f"  {f}: {size/1024:.0f} Ko{flag}")


if __name__ == "__main__":
    main()
