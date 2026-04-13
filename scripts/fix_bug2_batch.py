"""
BUG 2 fix - Version batch SQL optimisee.

Au lieu de 6000+ UPDATEs individuels, on fait :
1. SELECT all recipe_ingredients
2. Parse en Python
3. Un seul gros UPDATE via VALUES + FROM
"""

import asyncio
import re
import ssl

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = (
    "postgresql+asyncpg://postgres.sssjiqahivctpccwfjtt:"
    "87NuWTnC7j6596HF@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
)

FRACTION_MAP = {
    "1/2": 0.5, "1/3": 0.333, "2/3": 0.667, "1/4": 0.25,
    "3/4": 0.75, "1/8": 0.125, "1/6": 0.167, "1/5": 0.2,
    "2/5": 0.4, "3/5": 0.6, "4/5": 0.8, "1/10": 0.1,
    "3/8": 0.375, "5/8": 0.625, "7/8": 0.875,
}


def parse_quantity_unit(raw_unit: str) -> tuple[float, str]:
    """Parse un champ unit brut pour extraire quantity et unit."""
    if not raw_unit or not raw_unit.strip():
        return 1.0, ""

    s = raw_unit.strip()

    # "[N]" -> quantity=N
    bracket_match = re.match(r'^\[([0-9./]+)\]$', s)
    if bracket_match:
        return _parse_number(bracket_match.group(1)), ""

    # "N N/D unit" (e.g. "1 1/2 cups")
    mixed_match = re.match(r'^(\d+)\s+(\d+/\d+)\s*(.*?)$', s)
    if mixed_match:
        whole = float(mixed_match.group(1))
        frac = FRACTION_MAP.get(mixed_match.group(2), _eval_fraction(mixed_match.group(2)))
        return whole + frac, mixed_match.group(3).strip()

    # "N/D unit" (e.g. "1/4 tsp")
    frac_match = re.match(r'^(\d+/\d+)\s*(.*?)$', s)
    if frac_match:
        frac = FRACTION_MAP.get(frac_match.group(1), _eval_fraction(frac_match.group(1)))
        return frac, frac_match.group(2).strip()

    # "Nunit" ou "N unit" (e.g. "650g", "2 cups")
    num_match = re.match(r'^([0-9]+(?:\.[0-9]+)?)\s*(.*?)$', s)
    if num_match:
        return float(num_match.group(1)), num_match.group(2).strip()

    # "texte of N" (e.g. "Grated Zest of 2")
    of_match = re.search(r'of\s+(\d+(?:\.\d+)?)\s*$', s)
    if of_match:
        return float(of_match.group(1)), s[:of_match.start()].strip()

    # Pas de nombre -> garder en l'etat
    return 1.0, s


def _parse_number(s: str) -> float:
    if '/' in s:
        return _eval_fraction(s)
    return float(s)


def _eval_fraction(s: str) -> float:
    parts = s.split('/')
    if len(parts) == 2:
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            return 1.0
    return 1.0


def _make_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def main() -> None:
    engine = create_async_engine(
        DB_URL,
        echo=False,
        connect_args={"ssl": _make_ssl_context()},
    )

    async with engine.begin() as conn:
        print("=" * 60)
        print("BUG 2 -- DIAGNOSTIC")
        print("=" * 60)

        row = await conn.execute(text("SELECT COUNT(*) FROM recipe_ingredients"))
        total = row.scalar()
        print(f"Total recipe_ingredients : {total}")

        row = await conn.execute(text(
            "SELECT COUNT(*) FROM recipe_ingredients WHERE quantity = 1.0"
        ))
        qty_one = row.scalar()
        print(f"Avec quantity=1.0 : {qty_one} ({qty_one*100//total}%)")

        # Echantillon avant fix
        row = await conn.execute(text("""
            SELECT i.canonical_name, ri.quantity, ri.unit, ri.notes
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            ORDER BY RANDOM()
            LIMIT 10
        """))
        print("\nEchantillon AVANT fix :")
        for s in row.fetchall():
            print(f"  {s[0]:25s} qty={s[1]:<8} unit='{s[2]}'")

        # Charger tout en memoire
        print("\n" + "=" * 60)
        print("PARSING")
        print("=" * 60)

        row = await conn.execute(text(
            "SELECT recipe_id, ingredient_id, unit FROM recipe_ingredients"
        ))
        all_rows = row.fetchall()

        updates = []
        sample_fixes = []

        for recipe_id, ingredient_id, raw_unit in all_rows:
            if raw_unit is None:
                continue
            qty, new_unit = parse_quantity_unit(raw_unit)
            if qty == 1.0 and new_unit == raw_unit:
                continue
            if qty <= 0:
                qty = 1.0
            updates.append((str(recipe_id), str(ingredient_id), qty, new_unit))
            if len(sample_fixes) < 10:
                sample_fixes.append((raw_unit, qty, new_unit))

        print(f"  Lignes a mettre a jour : {len(updates)}")

        if sample_fixes:
            print("  Exemples :")
            for raw, qty, unit in sample_fixes:
                print(f"    '{raw}' -> qty={qty}, unit='{unit}'")

        # Batch update par groupes de 500 (eviter les requetes trop longues)
        print("\n" + "=" * 60)
        print("MISE A JOUR BATCH")
        print("=" * 60)

        batch_size = 500
        total_updated = 0

        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]

            # Construire la clause VALUES pour le batch UPDATE
            values_parts = []
            params = {}
            for j, (rid, iid, qty, unit) in enumerate(batch):
                values_parts.append(
                    f"(:rid_{j}::uuid, :iid_{j}::uuid, :qty_{j}::numeric, :unit_{j}::text)"
                )
                params[f"rid_{j}"] = rid
                params[f"iid_{j}"] = iid
                params[f"qty_{j}"] = qty
                params[f"unit_{j}"] = unit

            values_sql = ",\n".join(values_parts)

            sql = f"""
                UPDATE recipe_ingredients ri
                SET quantity = v.new_qty,
                    unit = v.new_unit
                FROM (VALUES
                    {values_sql}
                ) AS v(recipe_id, ingredient_id, new_qty, new_unit)
                WHERE ri.recipe_id = v.recipe_id
                  AND ri.ingredient_id = v.ingredient_id
            """

            result = await conn.execute(text(sql), params)
            total_updated += result.rowcount
            print(f"  Batch {i//batch_size + 1} : {result.rowcount} lignes")

        print(f"  TOTAL mis a jour : {total_updated}")

        # Verification post-fix
        print("\n" + "=" * 60)
        print("VERIFICATION POST-FIX")
        print("=" * 60)

        row = await conn.execute(text(
            "SELECT COUNT(*) FROM recipe_ingredients WHERE quantity = 1.0"
        ))
        qty_one_after = row.scalar()
        print(f"  Avec quantity=1.0 : {qty_one_after} (avant: {qty_one})")

        row = await conn.execute(text(
            "SELECT COUNT(DISTINCT ROUND(quantity::numeric, 2)) FROM recipe_ingredients"
        ))
        distinct_qty = row.scalar()
        print(f"  Valeurs quantity distinctes : {distinct_qty}")

        # Echantillon post-fix
        row = await conn.execute(text("""
            SELECT i.canonical_name, ri.quantity, ri.unit, ri.notes
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            ORDER BY RANDOM()
            LIMIT 15
        """))
        print("\n  Echantillon APRES fix :")
        for s in row.fetchall():
            print(f"    {s[0]:25s} qty={s[1]:<8} unit='{s[2]}'")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
