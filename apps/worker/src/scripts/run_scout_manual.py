"""Script de test manuel RECIPE_SCOUT.

Lance RECIPE_SCOUT sur un petit batch (10 recettes Marmiton) sans passer
par Celery. Utile pour valider le pipeline complet en environnement local
avant de confier les runs nocturnes à Celery Beat.

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5433/mealplanner \\
    GOOGLE_AI_API_KEY=your_key \\
    uv run python -m src.scripts.run_scout_manual

Variables d'environnement :
    DATABASE_URL        Obligatoire — connexion PostgreSQL async (asyncpg).
                        Pointer sur localhost:5433 pour le Docker local.
    GOOGLE_AI_API_KEY   Optionnel — si absent ou "dummy", la validation
                        Gemini est skippée (mode dégradé, score=0.7).
    REDIS_URL           Optionnel — non requis pour ce script (pas de Celery).
    DRY_RUN             Optionnel — "true" pour scraper sans insérer en DB.
    MAX_RECIPES         Optionnel — nombre de recettes à scraper (défaut: 10).
"""

import asyncio
import os
import sys

from loguru import logger


def _configure_logging() -> None:
    """Configure loguru pour la sortie console du script manuel."""
    logger.remove()
    logger.add(
        sys.stdout,
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> — {message}"
        ),
    )


def _validate_env() -> None:
    """
    Vérifie que DATABASE_URL est définie avant de démarrer.

    Lève une erreur explicite plutôt que de laisser crasher l'agent
    avec un message cryptique sur la connexion DB.
    """
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error(
            "DATABASE_URL manquante. "
            "Exemple : DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5433/mealplanner"
        )
        sys.exit(1)

    if "asyncpg" not in db_url and "postgresql" in db_url:
        logger.warning(
            "DATABASE_URL ne contient pas 'asyncpg'. "
            "Assurez-vous d'utiliser le driver async : postgresql+asyncpg://..."
        )

    google_key = os.getenv("GOOGLE_AI_API_KEY", "")
    if not google_key or google_key.lower() in ("dummy", "placeholder", ""):
        logger.warning(
            "GOOGLE_AI_API_KEY absente ou invalide — "
            "mode dégradé actif : validation Gemini skippée, "
            "quality_score=0.7 attribué par défaut."
        )
    else:
        logger.info("GOOGLE_AI_API_KEY configurée — validation Gemini activée.")


async def main() -> None:
    """Point d'entrée principal du script de test manuel."""
    _configure_logging()
    _validate_env()

    max_recipes = int(os.getenv("MAX_RECIPES", "10"))
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    if dry_run:
        logger.info("Mode DRY_RUN activé — les recettes NE seront PAS insérées en DB.")

    logger.info(
        "scout_manual_start",
        sources=["marmiton"],
        max_recipes=max_recipes,
        dry_run=dry_run,
    )

    from src.agents.recipe_scout.agent import RecipeScoutAgent

    agent = RecipeScoutAgent(
        db_url=os.getenv("DATABASE_URL"),
        sources=["marmiton"],
        max_recipes_per_source=max_recipes,
    )

    # Injection du flag dry_run directement dans l'agent avant le run
    # L'agent vérifie cet attribut dans _insert_recipe pour skip l'écriture DB.
    agent._dry_run = dry_run

    stats = await agent.run()

    # ---- Rapport de fin ----
    duration = stats.duration_seconds or 0.0
    logger.info("=" * 60)
    logger.info("RAPPORT RECIPE_SCOUT MANUEL")
    logger.info(f"  Durée              : {duration:.1f}s")
    logger.info(f"  Scrapées           : {stats.total_scraped}")
    logger.info(f"  Normalisées        : {stats.total_normalized}")
    logger.info(f"  Dédupliquées       : {stats.total_deduplicated}")
    logger.info(f"  Validées           : {stats.total_validated}")
    logger.info(f"  Rejetées qualité   : {stats.total_rejected_quality}")
    logger.info(f"  Insérées en DB     : {stats.total_inserted}")
    logger.info(f"  Taux de succès     : {stats.success_rate:.1%}")
    if stats.errors:
        logger.warning(f"  Erreurs ({len(stats.errors)}) :")
        for err in stats.errors[:10]:
            logger.warning(f"    - {err}")
    logger.info("=" * 60)

    return stats


if __name__ == "__main__":
    asyncio.run(main())
