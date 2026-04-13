"""
BUG 2 fix v3 - Utilise une table temporaire pour le batch UPDATE.
Evite les problemes de cast ::uuid dans les VALUES via SQLAlchemy text().
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
    if not raw_unit or not raw_unit.strip():
        return 1.0, ""
    s = raw_unit.strip()

    bracket_match = re.match(r'^\[([0-9./]+)\]$', s)
    if bracket_match:
        return _parse_number(bracket_match.group(1)), ""

    mixed_match = re.match(r'^(\d+)\s+(\d+/\d+)\s*(.*?)$', s)
    if mixed_match:
        whole = float(mixed_match.group(1))
        frac = FRACTION_MAP.get(mixed_match.group(2), _eval_fraction(mixed_match.group(2)))
        return whole + frac, mixed_match.group(3).strip()

    frac_match = re.match(r'^(\d+/\d+)\s*(.*?)$', s)
    if frac_match:
        frac = FRACTION_MAP.get(frac_match.group(1), _eval_fraction(frac_match.group(1)))
        return frac, frac_match.group(2).strip()

    num_match = re.match(r'^([0-9]+(?:\.[0-9]+)?)\s*(.*?)$', s)
    if num_match:
        return float(num_match.group(1)), num_match.group(2).strip()

    of_match = re.search(r'of\s+(\d+(?:\.\d+)?)\s*$', s)
    if of_match:
        return float(of_match.group(1)), s[:of_match.start()].strip()

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

        # Charger toutes les lignes
        row = await conn.execute(text(
            "SELECT recipe_id, ingredient_id, unit FROM recipe_ingredients"
        ))
        all_rows = row.fetchall()

        # Parser en Python
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

        print(f"\nLignes a mettre a jour : {len(updates)}")
        if sample_fixes:
            print("Exemples :")
            for raw, qty, unit in sample_fixes:
                print(f"  '{raw}' -> qty={qty}, unit='{unit}'")

        # Creer une table temporaire
        print("\n" + "=" * 60)
        print("MISE A JOUR VIA TABLE TEMPORAIRE")
        print("=" * 60)

        await conn.execute(text("""
            CREATE TEMP TABLE _fix_qty (
                recipe_id UUID,
                ingredient_id UUID,
                new_qty NUMERIC(10,3),
                new_unit TEXT
            ) ON COMMIT DROP
        """))

        # Inserer par batch de 200 avec executemany
        batch_size = 200
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            await conn.execute(
                text("""
                    INSERT INTO _fix_qty (recipe_id, ingredient_id, new_qty, new_unit)
                    VALUES (:rid, :iid, :qty, :unit)
                """),
                [
                    {"rid": rid, "iid": iid, "qty": qty, "unit": unit}
                    for rid, iid, qty, unit in batch
                ],
            )
            if (i // batch_size) % 5 == 0:
                print(f"  Insere {min(i + batch_size, len(updates))}/{len(updates)}...")

        # Un seul UPDATE depuis la table temporaire
        result = await conn.execute(text("""
            UPDATE recipe_ingredients ri
            SET quantity = f.new_qty,
                unit = f.new_unit
            FROM _fix_qty f
            WHERE ri.recipe_id = f.recipe_id
              AND ri.ingredient_id = f.ingredient_id
        """))
        print(f"\n  UPDATE applique : {result.rowcount} lignes")

        # Verification
        print("\n" + "=" * 60)
        print("VERIFICATION POST-FIX")
        print("=" * 60)

        row = await conn.execute(text(
            "SELECT COUNT(*) FROM recipe_ingredients WHERE quantity = 1.0"
        ))
        qty_one_after = row.scalar()
        print(f"  quantity=1.0 : {qty_one_after} (avant: {qty_one})")

        row = await conn.execute(text(
            "SELECT COUNT(DISTINCT ROUND(quantity::numeric, 2)) FROM recipe_ingredients"
        ))
        distinct_qty = row.scalar()
        print(f"  Valeurs quantity distinctes : {distinct_qty}")

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
