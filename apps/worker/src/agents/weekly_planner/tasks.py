"""
Tâches Celery pour l'agent WEEKLY_PLANNER.

Ces tâches exposent le WeeklyPlannerAgent au broker Celery.
La génération d'un plan est déclenché depuis l'API FastAPI
via POST /api/v1/plans/generate → cette tâche Celery.

Queue : llm (partagée avec les tâches LLM RECIPE_SCOUT)
Rate limit applicatif : 10 plans/heure/utilisateur (LIMIT_LLM_PLAN_USER)
"""

import asyncio
import os
from typing import Any

from celery.utils.log import get_task_logger
from loguru import logger

from src.app import celery_app

task_logger = get_task_logger(__name__)


@celery_app.task(
    queue="llm",
    name="weekly_planner.generate_plan",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    soft_time_limit=300,   # 5 minutes max par plan
    time_limit=360,
)
def generate_plan_task(
    self,
    household_id: str,
    week_start_iso: str,
    num_dinners: int = 5,
) -> dict[str, Any]:
    """
    Tâche Celery pour générer un plan hebdomadaire.

    Déclenché depuis POST /api/v1/plans/generate.
    Retourne le résultat complet (plan_id + recettes + liste de courses).

    Args:
        household_id: UUID du foyer (str).
        week_start_iso: Date de début de semaine au format ISO 8601 (YYYY-MM-DD).
        num_dinners: Nombre de dîners à planifier.

    Returns:
        Dict avec plan_id, recipe_count, shopping_items_count, duration_seconds.
    """
    from datetime import date
    from uuid import UUID

    logger.info(
        "task_weekly_planner_start",
        household_id=household_id,
        week_start=week_start_iso,
        num_dinners=num_dinners,
        task_id=self.request.id,
    )

    # Validation de la date
    try:
        week_start = date.fromisoformat(week_start_iso)
    except ValueError as exc:
        raise ValueError(f"Format de date invalide : {week_start_iso} (attendu YYYY-MM-DD)") from exc

    async def _run() -> dict[str, Any]:
        from mealplanner_db.session import AsyncSessionLocal

        from src.agents.weekly_planner.agent import WeeklyPlannerAgent

        agent = WeeklyPlannerAgent(
            session_factory=AsyncSessionLocal,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

        result = await agent.run(
            household_id=UUID(household_id),
            week_start=week_start,
            num_dinners=num_dinners,
        )

        return {
            "status": "completed",
            "plan_id": result.plan_id,
            "household_id": result.household_id,
            "week_start": str(result.week_start),
            "recipe_count": result.recipe_count,
            "shopping_items_count": len(result.shopping_list),
            "duration_seconds": result.duration_seconds,
            "used_llm_fallback": result.used_llm_fallback,
            "errors": result.errors,
        }

    try:
        task_result = asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            task_result = loop.run_until_complete(_run())
        finally:
            loop.close()

    logger.info(
        "task_weekly_planner_complete",
        task_id=self.request.id,
        plan_id=task_result.get("plan_id"),
        recipe_count=task_result.get("recipe_count"),
        duration_seconds=task_result.get("duration_seconds"),
    )

    return task_result
