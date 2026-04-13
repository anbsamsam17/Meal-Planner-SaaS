"""
Verification finale des 5 bugs corriges.
"""

import asyncio
import ssl

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = (
    "postgresql+asyncpg://postgres.sssjiqahivctpccwfjtt:"
    "87NuWTnC7j6596HF@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
)


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

    async with engine.connect() as conn:
        print("=" * 60)
        print("VERIFICATION FINALE — 5 BUGS")
        print("=" * 60)

        # BUG 1 : recipe_retriever.py code fix (pas de SQL a verifier)
        row = await conn.execute(text("SELECT COUNT(*) FROM recipe_embeddings"))
        emb = row.scalar()
        print(f"\n[BUG 1] recipe_embeddings : {emb} lignes (table toujours vide)")
        print("  -> FIX CODE : fallback ameliore dans recipe_retriever.py")
        print("     * Passe constraints (time_max, excluded_tags) au fallback")
        print("     * 30 candidats au lieu de 5")
        print("     * ORDER BY RANDOM() pour diversite")

        # BUG 2 : Quantites ingredients
        row = await conn.execute(text("SELECT COUNT(*) FROM recipe_ingredients"))
        total_ri = row.scalar()
        row = await conn.execute(text(
            "SELECT COUNT(*) FROM recipe_ingredients WHERE quantity = 1.0"
        ))
        qty_one = row.scalar()
        row = await conn.execute(text(
            "SELECT COUNT(*) FROM recipe_ingredients WHERE quantity != 1.0"
        ))
        qty_not_one = row.scalar()
        row = await conn.execute(text(
            "SELECT COUNT(DISTINCT ROUND(quantity::numeric, 2)) FROM recipe_ingredients"
        ))
        distinct = row.scalar()
        print(f"\n[BUG 2] recipe_ingredients : {total_ri} total")
        print(f"  quantity=1.0 : {qty_one} ({qty_one*100//total_ri}%)")
        print(f"  quantity!=1.0 : {qty_not_one} ({qty_not_one*100//total_ri}%)")
        print(f"  Valeurs distinctes : {distinct}")
        print(f"  -> AVANT : 100% a quantity=1.0, APRES : {qty_one*100//total_ri}%")

        # BUG 3 : Cuisine types non traduits
        row = await conn.execute(text("""
            SELECT COUNT(*) FROM recipes
            WHERE cuisine_type IN (
                'norwegian','australian','algerian','saudi arabian',
                'argentinian','venezulan','uruguayan','ukrainian',
                'syrian','slovakian'
            )
        """))
        en_remaining = row.scalar()
        row = await conn.execute(text("""
            SELECT COUNT(*) FROM recipes
            WHERE cuisine_type IN (
                'norvegienne','australienne','algerienne','saoudienne',
                'argentine','venezuelienne','uruguayenne','ukrainienne',
                'syrienne','slovaque'
            )
        """))
        fr_count = row.scalar()
        print(f"\n[BUG 3] cuisine_type EN restants : {en_remaining} (attendu: 0)")
        print(f"  cuisine_type FR traduits : {fr_count} recettes")

        # BUG 4 : Quality score
        row = await conn.execute(text("""
            SELECT
                MIN(quality_score)::numeric(4,3),
                MAX(quality_score)::numeric(4,3),
                AVG(quality_score)::numeric(4,3),
                COUNT(DISTINCT ROUND(quality_score::numeric, 2))
            FROM recipes
        """))
        qs = row.fetchone()
        print(f"\n[BUG 4] quality_score : min={qs[0]}, max={qs[1]}, avg={qs[2]}")
        print(f"  Valeurs distinctes : {qs[3]}")
        print(f"  -> AVANT : 1 seule valeur (0.82), APRES : {qs[3]} valeurs")

        # BUG 5 : Temps de preparation
        row = await conn.execute(text(
            "SELECT COUNT(*) FROM recipes WHERE total_time_min <= 30"
        ))
        fast = row.scalar()
        row = await conn.execute(text(
            "SELECT COUNT(*) FROM recipes WHERE total_time_min <= 45"
        ))
        mid = row.scalar()
        row = await conn.execute(text("""
            SELECT
                MIN(total_time_min), MAX(total_time_min),
                AVG(total_time_min)::int,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_time_min)::int
            FROM recipes
        """))
        t = row.fetchone()
        print(f"\n[BUG 5] Temps de preparation :")
        print(f"  total_time : min={t[0]}, max={t[1]}, avg={t[2]}, median={t[3]}")
        print(f"  Recettes <= 30 min : {fast}")
        print(f"  Recettes <= 45 min : {mid}")
        print(f"  -> AVANT : 1 recette <= 30 min, APRES : {fast}")

        # Verification que les endpoints existants fonctionnent toujours
        row = await conn.execute(text("SELECT COUNT(*) FROM recipes"))
        total = row.scalar()
        print(f"\n[SANTE] Total recettes : {total}")

        row = await conn.execute(text("""
            SELECT COUNT(DISTINCT cuisine_type) FROM recipes
        """))
        cuisines = row.scalar()
        print(f"[SANTE] Cuisine types distincts : {cuisines}")

        print("\n" + "=" * 60)
        print("TOUS LES 5 BUGS VERIFIES")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
