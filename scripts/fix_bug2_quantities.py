"""
BUG 2 : Quantites ingredients corrompues (quantity=1 partout).

Le champ `unit` contient "2 cups", "650g", "1/4 tsp" mais quantity vaut 1.0.

Ce script :
1. Diagnostique l'etat actuel
2. Parse le champ `unit` pour extraire la quantite numerique
3. Met a jour quantity et unit correctement

La cle primaire de recipe_ingredients est composite (recipe_id, ingredient_id).

Patterns a parser :
- "2 cups"        -> quantity=2.0, unit="cups"
- "650g"          -> quantity=650.0, unit="g"
- "1/4 tsp"       -> quantity=0.25, unit="tsp"
- "1 1/2 cups"    -> quantity=1.5, unit="cups"
- "Leaves"        -> quantity=1.0, unit="Leaves" (pas de nombre)
- "[2]"           -> quantity=2.0, unit="" (nombre entre crochets)
- "[0.5]"         -> quantity=0.5, unit=""
- "Grated Zest of 2" -> quantity=2.0, unit="Grated Zest of"
- "1/4 cup"       -> quantity=0.25, unit="cup"
- "Pinch"         -> quantity=1.0, unit="pinch"
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

# Fractions courantes
FRACTION_MAP = {
    "1/2": 0.5,
    "1/3": 0.333,
    "2/3": 0.667,
    "1/4": 0.25,
    "3/4": 0.75,
    "1/8": 0.125,
    "1/6": 0.167,
    "1/5": 0.2,
    "2/5": 0.4,
    "3/5": 0.6,
    "4/5": 0.8,
    "1/10": 0.1,
    "3/8": 0.375,
    "5/8": 0.625,
    "7/8": 0.875,
}


def parse_quantity_unit(raw_unit: str) -> tuple[float, str]:
    """
    Parse un champ unit brut de TheMealDB pour extraire quantity et unit.

    Returns:
        (quantity, unit) tuple
    """
    if not raw_unit or not raw_unit.strip():
        return 1.0, ""

    s = raw_unit.strip()

    # Pattern : "[N]" -> quantity=N, unit=""
    bracket_match = re.match(r'^\[([0-9./]+)\]$', s)
    if bracket_match:
        return _parse_number(bracket_match.group(1)), ""

    # Pattern : "N unit" ou "Nunit" (e.g. "2 cups", "650g")
    # Aussi : "N N/N unit" (e.g. "1 1/2 cups")

    # Essai : nombre + fraction + texte (e.g. "1 1/2 cups")
    mixed_match = re.match(
        r'^(\d+)\s+(\d+/\d+)\s*(.*?)$', s
    )
    if mixed_match:
        whole = float(mixed_match.group(1))
        frac = FRACTION_MAP.get(
            mixed_match.group(2),
            _eval_fraction(mixed_match.group(2))
        )
        unit = mixed_match.group(3).strip()
        return whole + frac, unit

    # Essai : fraction seule + texte (e.g. "1/4 tsp")
    frac_match = re.match(r'^(\d+/\d+)\s*(.*?)$', s)
    if frac_match:
        frac = FRACTION_MAP.get(
            frac_match.group(1),
            _eval_fraction(frac_match.group(1))
        )
        unit = frac_match.group(2).strip()
        return frac, unit

    # Essai : nombre decimal + unite collee ou separee (e.g. "650g", "2 cups", "1.5 tbsp")
    num_match = re.match(r'^([0-9]+(?:\.[0-9]+)?)\s*(.*?)$', s)
    if num_match:
        qty = float(num_match.group(1))
        unit = num_match.group(2).strip()
        return qty, unit

    # Pattern fin : "texte of N" (e.g. "Grated Zest of 2")
    of_match = re.search(r'of\s+(\d+(?:\.\d+)?)\s*$', s)
    if of_match:
        qty = float(of_match.group(1))
        unit = s[:of_match.start()].strip()
        return qty, unit

    # Pas de nombre detecte : c'est probablement un mot-cle ("Leaves", "Pinch")
    return 1.0, s


def _parse_number(s: str) -> float:
    """Parse un nombre simple ou une fraction."""
    if '/' in s:
        return _eval_fraction(s)
    return float(s)


def _eval_fraction(s: str) -> float:
    """Evalue une fraction simple N/D."""
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
        # Diagnostic
        print("=" * 60)
        print("BUG 2 -- DIAGNOSTIC recipe_ingredients")
        print("=" * 60)

        row = await conn.execute(text("""
            SELECT COUNT(*) FROM recipe_ingredients
        """))
        total = row.scalar()
        print(f"Total recipe_ingredients : {total}")

        row = await conn.execute(text("""
            SELECT COUNT(*) FROM recipe_ingredients WHERE quantity = 1.0
        """))
        qty_one = row.scalar()
        print(f"Avec quantity=1.0 : {qty_one} ({qty_one*100//total}%)")

        # Echantillon des units actuels (cle composite, pas de ri.id)
        row = await conn.execute(text("""
            SELECT i.canonical_name, ri.quantity, ri.unit, ri.notes
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            ORDER BY RANDOM()
            LIMIT 20
        """))
        samples = row.fetchall()
        print("\nEchantillon (20 lignes) :")
        for s in samples:
            print(f"  {s[0]:25s} qty={s[1]:<8} unit='{s[2]}' notes='{s[3]}'")

        # Charger toutes les lignes pour le parsing (cle composite)
        print("\n" + "=" * 60)
        print("PARSING ET MISE A JOUR")
        print("=" * 60)

        row = await conn.execute(text("""
            SELECT recipe_id, ingredient_id, unit FROM recipe_ingredients
        """))
        all_rows = row.fetchall()

        updated = 0
        skipped = 0
        errors = 0
        sample_fixes = []

        for recipe_id, ingredient_id, raw_unit in all_rows:
            if raw_unit is None:
                skipped += 1
                continue

            qty, new_unit = parse_quantity_unit(raw_unit)

            # Ne pas mettre a jour si quantity resterait 1.0 et unit inchange
            if qty == 1.0 and new_unit == raw_unit:
                skipped += 1
                continue

            # quantity doit etre > 0 (CHECK constraint en DB)
            if qty <= 0:
                qty = 1.0

            try:
                await conn.execute(
                    text("""
                        UPDATE recipe_ingredients
                        SET quantity = :qty, unit = :unit
                        WHERE recipe_id = :recipe_id
                          AND ingredient_id = :ingredient_id
                    """),
                    {
                        "qty": qty,
                        "unit": new_unit,
                        "recipe_id": recipe_id,
                        "ingredient_id": ingredient_id,
                    },
                )
                updated += 1
                if len(sample_fixes) < 15:
                    sample_fixes.append((raw_unit, qty, new_unit))
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  ERREUR: {e}")

        print(f"  Lignes mises a jour : {updated}")
        print(f"  Lignes inchangees   : {skipped}")
        print(f"  Erreurs             : {errors}")

        if sample_fixes:
            print("\n  Exemples de corrections :")
            for raw, qty, unit in sample_fixes:
                print(f"    '{raw}' -> qty={qty}, unit='{unit}'")

        # Verification post-fix
        row = await conn.execute(text("""
            SELECT COUNT(*) FROM recipe_ingredients WHERE quantity = 1.0
        """))
        qty_one_after = row.scalar()
        print(f"\n  Avec quantity=1.0 apres fix : {qty_one_after} (avant: {qty_one})")

        row = await conn.execute(text("""
            SELECT COUNT(DISTINCT ROUND(quantity::numeric, 2)) FROM recipe_ingredients
        """))
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
        samples2 = row.fetchall()
        print("\n  Echantillon post-fix (15 lignes) :")
        for s in samples2:
            print(f"    {s[0]:25s} qty={s[1]:<8} unit='{s[2]}' notes='{s[3]}'")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
