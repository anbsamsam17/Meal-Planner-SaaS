"""
Tâches Celery pour l'agent RETENTION_LOOP.

Schedule : toutes les 4 heures (Celery beat crontab).
Queue : default (légère en ressources — pas de LLM ni de PDF).

La tâche est idempotente : elle ré-analyse à chaque exécution
(pas d'état persistant entre les runs).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from celery.utils.log import get_task_logger
from loguru import logger

from src.app import celery_app

_task_logger = get_task_logger(__name__)

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/mealplanner",
)


def _get_db_session_factory():
    """Factory de session DB pour les tâches Celery."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    db_url = DATABASE_URL
    if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, pool_size=2, max_overflow=0)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(
    name="retention_loop.check_engagement",
    queue="default",
    max_retries=1,
    soft_time_limit=300,   # 5 minutes max
    time_limit=360,
    acks_late=True,
)
def check_engagement_task() -> dict[str, Any]:
    """
    Vérifie l'engagement de tous les foyers actifs.

    Exécutée toutes les 4 heures via Celery beat.
    En v0 (Phase 2) : logging uniquement.
    En Phase 3 : envoi d'emails/push notifications.

    Returns:
        dict : {total_checked, at_risk, inactive, disengaged}
    """
    from src.agents.retention_loop.agent import RetentionLoopAgent

    logger.info("retention_loop_task_start")

    agent = RetentionLoopAgent()
    session_factory = _get_db_session_factory()

    async def _run() -> dict:
        async with session_factory() as session:
            return await agent.run(session)

    try:
        result = asyncio.run(_run())
    except Exception as exc:
        logger.error("retention_loop_task_error", error=str(exc))
        raise

    logger.info("retention_loop_task_done", **result)
    return result
