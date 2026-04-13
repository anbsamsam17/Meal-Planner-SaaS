"""
Tâches Celery pour l'agent BOOK_GENERATOR.

Deux tâches :
- generate_book_task   : génère le PDF d'un plan validé (queue pdf_high, priorité 9)
- batch_missing_books_task : batch dimanche soir — génère les PDFs manquants (queue pdf_low)

Pipeline déclenché par validate_plan() dans l'API FastAPI :
  Celery.send_task('book_generator.generate_book', args=[plan_id], queue='pdf_high')
"""

from __future__ import annotations

import asyncio
import os
from uuid import UUID

from celery import Task
from celery.utils.log import get_task_logger
from loguru import logger

from src.app import celery_app

_task_logger = get_task_logger(__name__)

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/mealplanner",
)


def _get_db_session_factory():
    """
    Factory de session DB SQLAlchemy async.

    Créé à la demande dans les tâches Celery (pas de connexion au démarrage du worker).
    Pool de 2 connexions par worker (les tâches PDF sont séquentielles).
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    # Conversion postgresql:// → postgresql+asyncpg:// si nécessaire
    db_url = DATABASE_URL
    if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, pool_size=2, max_overflow=0)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(
    bind=True,
    name="book_generator.generate_book",
    queue="pdf_high",
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=180,   # 3 minutes (WeasyPrint peut être lent)
    time_limit=240,        # 4 minutes limite dure
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_book_task(self: Task, plan_id: str) -> dict:
    """
    Génère le PDF hebdomadaire pour un plan validé.

    Idempotente : skip si content_hash identique au précédent.
    Retries automatiques sur erreur avec délai exponentiel (30s, 60s, 120s).

    Args:
        plan_id: UUID str du plan hebdomadaire validé.

    Returns:
        dict : {skipped, pdf_key, content_hash, duration_ms}
    """
    from src.agents.book_generator.agent import BookGeneratorAgent

    logger.info("book_generator_task_start", plan_id=plan_id, task_id=self.request.id)

    agent = BookGeneratorAgent()
    session_factory = _get_db_session_factory()

    async def _run() -> dict:
        async with session_factory() as session:
            return await agent.run(UUID(plan_id), session)

    try:
        result = asyncio.run(_run())
    except ValueError as exc:
        # Plan non trouvé ou non validé — pas de retry
        logger.error("book_generator_plan_invalid", plan_id=plan_id, error=str(exc))
        raise

    except Exception as exc:
        logger.error(
            "book_generator_task_error",
            plan_id=plan_id,
            task_id=self.request.id,
            retry_count=self.request.retries,
            error=str(exc),
        )
        # Retry avec backoff exponentiel
        countdown = 30 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    logger.info(
        "book_generator_task_done",
        plan_id=plan_id,
        task_id=self.request.id,
        skipped=result.get("skipped", False),
        pdf_key=result.get("pdf_key"),
        duration_ms=result.get("duration_ms"),
    )

    return result


@celery_app.task(
    bind=True,
    name="book_generator.batch_missing_books",
    queue="pdf_low",
    max_retries=1,
    soft_time_limit=3600,  # 1 heure pour le batch
    time_limit=3900,
    acks_late=True,
)
def batch_missing_books_task(self: Task) -> dict:
    """
    Batch dimanche soir : génère les PDFs manquants pour la semaine suivante.

    Cible : plans validés sans weekly_book (ou book périmé).
    Lancé via Celery beat le dimanche à 22h00 (queue pdf_low).

    Returns:
        dict : {total_processed, skipped, generated, errors}
    """
    logger.info("book_generator_batch_start", task_id=self.request.id)

    session_factory = _get_db_session_factory()
    agent = BookGeneratorAgent()

    async def _run_batch() -> dict:
        from sqlalchemy import text

        async with session_factory() as session:
            # Récupère les plans validés sans PDF ou avec PDF périmé (hash différent)
            result = await session.execute(
                text(
                    """
                    SELECT wp.id::text
                    FROM weekly_plans wp
                    LEFT JOIN weekly_books wb ON wb.plan_id = wp.id
                    WHERE wp.status = 'validated'
                      AND wp.validated_at >= NOW() - INTERVAL '7 days'
                      AND (wb.id IS NULL OR wb.content_hash IS NULL)
                    ORDER BY wp.validated_at DESC
                    LIMIT 500
                    """
                )
            )
            plan_ids = [row[0] for row in result.fetchall()]

        logger.info(
            "book_generator_batch_plans_found",
            count=len(plan_ids),
        )

        stats = {
            "total_processed": len(plan_ids),
            "skipped": 0,
            "generated": 0,
            "errors": 0,
        }

        for plan_id_str in plan_ids:
            try:
                async with session_factory() as session:
                    result = await agent.run(UUID(plan_id_str), session)
                    if result.get("skipped"):
                        stats["skipped"] += 1
                    else:
                        stats["generated"] += 1
            except Exception as exc:
                stats["errors"] += 1
                logger.error(
                    "book_generator_batch_plan_error",
                    plan_id=plan_id_str,
                    error=str(exc),
                )

        return stats

    result = asyncio.run(_run_batch())

    logger.info(
        "book_generator_batch_done",
        task_id=self.request.id,
        **result,
    )

    return result
