"""
Endpoints d'administration — usage développement et ops.

Ces endpoints permettent de déclencher manuellement des agents
qui tournent normalement via Celery Beat (runs nocturnes).

Politique d'accès (SEC-02 FIX 2026-04-14) :
- Authentification JWT obligatoire dans TOUS les environnements (dev, staging, prod).
- TODO Phase 3 — Admin RBAC : restreindre aux utilisateurs avec rôle 'admin'
  via un check supplémentaire sur le claim JWT role/app_metadata.

Rate limit strict :
- POST /admin/scout/run : 1 requête par heure
  (le scraping est coûteux en ressources et en politesse envers les sources)

Ces endpoints ne font PAS partie de l'API publique.
Ils ne sont pas documentés dans la Swagger publique (include_in_schema=False
peut être activé en prod).
"""

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel, Field

from src.core.config import get_settings
from src.core.security import TokenPayload, get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


# SEC-02 FIX (2026-04-14) — Authentification obligatoire sur tous les endpoints admin.
# POURQUOI : les endpoints admin (scout/run) déclenchent des opérations coûteuses
# (scraping, tâches Celery). Sans auth, n'importe quel appelant peut les déclencher,
# ce qui constitue un risque d'abus et de déni de service.
# L'ancienne politique "pas d'auth en dev" laissait la porte ouverte en production
# si ENV n'était pas correctement configuré. On exige désormais un JWT valide
# dans TOUS les environnements.
def get_current_user_dep(request: Request) -> TokenPayload:
    """Dépendance FastAPI pour l'authentification JWT sur les routes admin."""
    settings = get_settings()
    return get_current_user(request, settings.SUPABASE_ANON_KEY)

# ---- Schémas de réponse ----


class ScoutRunResponse(BaseModel):
    """Réponse du déclenchement d'un run RECIPE_SCOUT."""

    task_id: str = Field(description="ID de la tâche Celery (vide si mode sync).")
    status: str = Field(description="'queued', 'running', ou 'error'.")
    message: str = Field(description="Description de l'action effectuée.")
    mode: str = Field(description="'celery' si Celery disponible, 'sync' sinon.")
    max_recipes: int = Field(description="Nombre de recettes demandées.")
    sources: list[str] = Field(description="Sources activées pour ce run.")


# ---- Rate limit : 1 run par heure ----
# Implémenté via Redis (pas de slowapi ici — limite sur endpoint admin unique).

_SCOUT_RATE_LIMIT_KEY = "admin:scout:last_run"
_SCOUT_RATE_LIMIT_SECONDS = 3600  # 1 heure


async def _check_scout_rate_limit(request: Request) -> None:
    """
    Vérifie que le dernier run RECIPE_SCOUT a eu lieu il y a plus d'1 heure.

    Utilise Redis pour persister le timestamp inter-requêtes.
    Si Redis est indisponible, la vérification est skippée (mode dégradé).

    Args:
        request: Requête FastAPI (accès à app.state.redis).

    Raises:
        HTTPException 429 si le rate limit est dépassé.
    """
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        logger.warning("scout_rate_limit_redis_unavailable", action="skip_check")
        return

    import time

    try:
        last_run = await redis_client.get(_SCOUT_RATE_LIMIT_KEY)
        if last_run is not None:
            elapsed = time.time() - float(last_run)
            remaining = int(_SCOUT_RATE_LIMIT_SECONDS - elapsed)
            if remaining > 0:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit dépassé.",
                        "message": (
                            f"Un run RECIPE_SCOUT a déjà été déclenché récemment. "
                            f"Attendez encore {remaining} secondes."
                        ),
                        "retry_after_seconds": remaining,
                    },
                    headers={"Retry-After": str(remaining)},
                )
    except HTTPException:
        raise
    except Exception as exc:
        # Redis error non bloquante : on laisse passer
        logger.warning("scout_rate_limit_check_error", error=str(exc))


async def _set_scout_rate_limit(request: Request) -> None:
    """
    Enregistre le timestamp du dernier run dans Redis.

    Args:
        request: Requête FastAPI (accès à app.state.redis).
    """
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        return

    import time

    try:
        await redis_client.setex(
            _SCOUT_RATE_LIMIT_KEY,
            _SCOUT_RATE_LIMIT_SECONDS,
            str(time.time()),
        )
    except Exception as exc:
        logger.warning("scout_rate_limit_set_error", error=str(exc))


# ---- Endpoint POST /admin/scout/run ----


@router.post(
    "/scout/run",
    summary="Déclencher un run RECIPE_SCOUT",
    description=(
        "Lance un batch de scraping RECIPE_SCOUT (10 recettes Marmiton par défaut). "
        "Déclenche une tâche Celery si le broker est disponible, "
        "sinon exécute en mode synchrone (pour les tests locaux sans Celery). "
        "Requiert une authentification JWT valide (SEC-02). "
        "Rate limit : 1 requête par heure."
    ),
    response_model=ScoutRunResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentification JWT requise."
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "description": "Run déjà déclenché récemment — attendre 1 heure."
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Celery broker indisponible et mode sync désactivé."
        },
    },
)
async def trigger_scout_run(
    request: Request,
    max_recipes: int = 10,
    sources: str = "marmiton",
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Déclenche un run RECIPE_SCOUT via Celery ou en mode synchrone.

    Stratégie de déclenchement :
    1. Si le broker Celery (Redis) est disponible → envoie une tâche Celery
       et retourne immédiatement le task_id.
    2. Sinon → exécute le run en mode synchrone dans la requête HTTP
       (utile pour les tests locaux sans Celery worker).

    Args:
        request: Requête FastAPI.
        max_recipes: Nombre de recettes à scraper (défaut: 10, max: 50).
        sources: Sources séparées par virgule (défaut: "marmiton").

    Returns:
        ScoutRunResponse avec le task_id et le mode d'exécution.
    """
    # ---- Validation des paramètres ----
    max_recipes = min(max_recipes, 50)  # Cap à 50 pour éviter les abus
    sources_list = [s.strip() for s in sources.split(",") if s.strip()]
    if not sources_list:
        sources_list = ["marmiton"]

    # ---- Vérification rate limit ----
    await _check_scout_rate_limit(request)

    # SEC-02 (2026-04-14) : log de sécurité — qui déclenche l'opération admin
    logger.info(
        "admin_scout_run_triggered",
        max_recipes=max_recipes,
        sources=sources_list,
        env=os.getenv("ENV", "dev"),
        triggered_by=user.user_id,
    )

    # ---- Tentative de déclenchement via Celery ----
    try:
        from celery import current_app as celery_current_app

        task = celery_current_app.send_task(
            "src.agents.recipe_scout.tasks.run_recipe_scout_nightly",
            kwargs={},
            queue="default",
        )

        await _set_scout_rate_limit(request)

        logger.info(
            "admin_scout_celery_task_sent",
            task_id=task.id,
            max_recipes=max_recipes,
            sources=sources_list,
        )

        return ScoutRunResponse(
            task_id=task.id,
            status="queued",
            message=(
                f"Run RECIPE_SCOUT mis en queue Celery. "
                f"Suivre avec : celery inspect active"
            ),
            mode="celery",
            max_recipes=max_recipes,
            sources=sources_list,
        )

    except Exception as celery_exc:
        logger.warning(
            "admin_scout_celery_unavailable",
            error=str(celery_exc),
            fallback="mode_sync",
        )

    # ---- Fallback : mode synchrone (sans Celery) ----
    # Utile en dev local sans worker Celery démarré.
    try:
        import asyncio

        from src.agents.recipe_scout.agent import RecipeScoutAgent

        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="DATABASE_URL non configurée — impossible de lancer le scout.",
            )

        agent = RecipeScoutAgent(
            db_url=db_url,
            sources=sources_list,
            max_recipes_per_source=max_recipes,
        )

        # Exécution async dans la requête HTTP (run court — max 50 recettes)
        stats = await asyncio.wait_for(agent.run(), timeout=120.0)

        await _set_scout_rate_limit(request)

        logger.info(
            "admin_scout_sync_complete",
            total_scraped=stats.total_scraped,
            total_inserted=stats.total_inserted,
        )

        return ScoutRunResponse(
            task_id=f"sync-{stats.started_at.isoformat()}",
            status="running",
            message=(
                f"Run synchrone terminé : {stats.total_inserted} recettes insérées "
                f"sur {stats.total_scraped} scrapées."
            ),
            mode="sync",
            max_recipes=max_recipes,
            sources=sources_list,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("admin_scout_run_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erreur lors du déclenchement du run RECIPE_SCOUT : {exc}",
        )
