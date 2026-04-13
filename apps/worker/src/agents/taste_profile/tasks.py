"""
Tâches Celery pour l'agent TASTE_PROFILE.

Déclenchement :
- À la demande : après chaque feedback utilisateur (via feedbacks.py)
- Futur Phase 2 : batch périodique (tous les membres actifs chaque nuit)

Queue : "embedding" — mêmes ressources que les embeddings (numpy, CPU)
Durée estimée par tâche : < 2 secondes (quelques dizaines de feedbacks max)
"""

import asyncio
from typing import Any

from celery.utils.log import get_task_logger
from loguru import logger

from src.app import celery_app

task_logger = get_task_logger(__name__)


@celery_app.task(
    queue="embedding",
    name="taste_profile.update_member_taste",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=60,
    time_limit=90,
)
def update_member_taste_task(self, member_id: str) -> dict[str, Any]:
    """
    Met à jour le vecteur de goût d'un membre après un feedback.

    Récupère l'historique complet des feedbacks du membre,
    calcule la moyenne pondérée des embeddings, et insère dans
    member_taste_vectors.

    Idempotente : peut être relancée plusieurs fois sans effet secondaire
    (ON CONFLICT DO UPDATE dans l'agent).

    Args:
        member_id: UUID du membre (sous forme de chaîne).

    Returns:
        Dict avec status, vector_updated, num_feedbacks.
    """
    from uuid import UUID

    logger.info(
        "task_taste_profile_start",
        member_id=member_id,
        task_id=self.request.id,
    )

    async def _run() -> dict[str, Any]:
        from src.agents.taste_profile.agent import TasteProfileAgent

        agent = TasteProfileAgent()
        return await agent.run(member_id=UUID(member_id))

    try:
        result = asyncio.run(_run())
    except RuntimeError:
        # Celery peut déjà avoir une event loop — créer une nouvelle
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_run())
        finally:
            loop.close()
    except Exception as exc:
        logger.error(
            "task_taste_profile_error",
            member_id=member_id,
            task_id=self.request.id,
            error=str(exc),
        )
        raise self.retry(exc=exc)

    logger.info(
        "task_taste_profile_complete",
        member_id=member_id,
        task_id=self.request.id,
        **result,
    )

    return result
