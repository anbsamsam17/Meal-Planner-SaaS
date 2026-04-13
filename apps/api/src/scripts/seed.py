"""seed.py — Script d'alimentation de la base de données avec les données de test.

Usage :
    cd apps/api
    uv run python -m src.scripts.seed

Ce script lit le fichier phase-0/database/07-seed-data.sql et l'exécute
via une connexion SQLAlchemy async. Il est conçu pour être idempotent
(ON CONFLICT DO NOTHING dans le SQL seed).

Pré-requis :
- DATABASE_URL définie dans l'environnement (ou fichier .env)
- Les migrations Alembic ont été appliquées (alembic upgrade head)
- Environnement de dev/staging UNIQUEMENT (ne jamais exécuter en production)

Résumé affiché après le seed :
- Nombre d'ingrédients
- Nombre de households
- Nombre de recettes
"""

import asyncio
import os
import sys
from pathlib import Path

# Ajout du répertoire apps/api au PYTHONPATH pour les imports src.*
# Nécessaire quand le script est lancé depuis un répertoire différent.
_api_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_api_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Chargement optionnel du fichier .env si python-dotenv est disponible
try:
    from dotenv import load_dotenv

    _env_file = _api_root / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
        print(f"[seed] Variables d'environnement chargées depuis {_env_file}")
except ImportError:
    pass  # python-dotenv optionnel en dev


def _get_database_url() -> str:
    """Retourne l'URL de connexion depuis DATABASE_URL."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL est requise.\n"
            "Exemple : export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mealplanner"
        )
    for old_prefix in ("postgresql://", "postgres://"):
        if url.startswith(old_prefix):
            return url.replace(old_prefix, "postgresql+asyncpg://", 1)
    return url


def _find_seed_file() -> Path:
    """Localise le fichier 07-seed-data.sql depuis la racine du monorepo."""
    # Remontée depuis apps/api/src/scripts/ → monorepo root
    monorepo_root = _api_root.parent.parent
    seed_path = monorepo_root / "phase-0" / "database" / "07-seed-data.sql"
    if not seed_path.exists():
        raise FileNotFoundError(
            f"Fichier seed introuvable : {seed_path}\n"
            f"Vérifier que le monorepo est correctement assemblé depuis phase-0/."
        )
    return seed_path


async def run_seed() -> None:
    """Exécute le seed SQL et affiche un résumé."""
    url = _get_database_url()
    seed_path = _find_seed_file()

    print(f"[seed] Lecture du fichier seed : {seed_path}")
    sql_content = seed_path.read_text(encoding="utf-8")

    engine = create_async_engine(
        url,
        # NullPool pour les scripts one-shot (pas de pool overhead)
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )

    async with engine.begin() as conn:
        print("[seed] Execution du seed SQL...")
        # Le seed SQL contient SET session_replication_role = replica pour désactiver
        # les triggers de validation pendant le seed, puis les réactive.
        # On exécute le fichier entier comme un bloc SQL.
        await conn.execute(text(sql_content))
        print("[seed] Seed SQL terminé avec succès.")

        # Résumé
        result_ingredients = await conn.execute(text("SELECT COUNT(*) FROM public.ingredients"))
        count_ingredients = result_ingredients.scalar_one()

        result_households = await conn.execute(text("SELECT COUNT(*) FROM public.households"))
        count_households = result_households.scalar_one()

        result_recipes = await conn.execute(text("SELECT COUNT(*) FROM public.recipes"))
        count_recipes = result_recipes.scalar_one()

        result_embeddings = await conn.execute(
            text("SELECT COUNT(*) FROM public.recipe_embeddings")
        )
        count_embeddings = result_embeddings.scalar_one()

    await engine.dispose()

    print("\n" + "=" * 50)
    print("[seed] RESUME DU SEED")
    print("=" * 50)
    print(f"  Ingredients     : {count_ingredients:>5}")
    print(f"  Households      : {count_households:>5}")
    print(f"  Recettes        : {count_recipes:>5}")
    print(f"  Embeddings      : {count_embeddings:>5} (vecteurs factices 0.001)")
    print("=" * 50)
    print("[seed] ATTENTION : Les embeddings sont des vecteurs factices (0.001).")
    print("       Regenerer avec RECIPE_SCOUT avant tout test de recommandation.")
    print("[seed] Ne jamais executer ce script en PRODUCTION.")


def main() -> None:
    """Point d'entrée du script."""
    print("[seed] Presto — Seed de la base de données")
    print("[seed] Environnement : DEVELOPPEMENT / STAGING uniquement\n")

    try:
        asyncio.run(run_seed())
    except FileNotFoundError as e:
        print(f"[seed] ERREUR : {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"[seed] ERREUR DE CONFIGURATION : {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[seed] ERREUR INATTENDUE : {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
