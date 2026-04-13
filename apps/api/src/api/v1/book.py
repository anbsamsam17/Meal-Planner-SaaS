"""
Endpoints pour le livre de recettes PDF (BOOK_GENERATOR).

Endpoints :
  GET  /api/v1/plans/{plan_id}/book          → URL du PDF (404 si pas encore généré)
  POST /api/v1/plans/{plan_id}/book/generate → déclenche la génération (rate limit 5/h)

Sécurité :
- Auth JWT requise sur les deux endpoints.
- Isolation tenant : vérifie que le plan appartient au foyer.
- Plan minimum requis : 'famille' (PDF hebdo = feature premium).

Rate limits :
- GET  book status : LIMIT_USER_READ (300/min)
- POST book generate : 5/h par user (LLM coûteux = génération PDF)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.rate_limit import LIMIT_USER_READ, get_user_key, limiter
from src.core.security import TokenPayload, get_current_user
from src.core.subscription import require_plan

router = APIRouter(prefix="/plans", tags=["book"])

settings = get_settings()

# ---- Helpers ----


def get_current_user_dep(request: Request) -> TokenPayload:
    """Dépendance JWT."""
    return get_current_user(request, settings.SUPABASE_ANON_KEY)


async def get_db(request: Request) -> AsyncSession:
    """Session DB depuis app.state."""
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        raise HTTPException(status_code=503, detail="Base de données non disponible.")
    async with factory() as session:
        yield session


async def _verify_plan_ownership(
    session: AsyncSession, plan_id: UUID, user: TokenPayload
) -> str:
    """
    Vérifie que le plan appartient au foyer de l'utilisateur.

    Returns:
        household_id str.

    Raises:
        HTTPException 404 si plan introuvable.
        HTTPException 403 si le plan n'appartient pas au foyer.
    """
    # Household de l'utilisateur
    hm_result = await session.execute(
        text(
            "SELECT household_id FROM household_members "
            "WHERE supabase_user_id = :uid LIMIT 1"
        ),
        {"uid": user.user_id},
    )
    hm_row = hm_result.fetchone()
    if hm_row is None:
        raise HTTPException(status_code=404, detail="Foyer introuvable.")

    household_id = str(hm_row[0])

    # Vérification appartenance plan
    plan_result = await session.execute(
        text("SELECT household_id FROM weekly_plans WHERE id = :pid LIMIT 1"),
        {"pid": str(plan_id)},
    )
    plan_row = plan_result.fetchone()

    if plan_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} introuvable.",
        )

    if str(plan_row[0]) != household_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce plan n'appartient pas à votre foyer.",
        )

    return household_id


# ---- Schémas ----


class BookStatus(BaseModel):
    """Statut et URL du livre de recettes PDF."""

    plan_id: UUID
    status: str  # "ready" | "generating" | "not_started"
    pdf_url: str | None = None
    generated_at: str | None = None
    content_hash: str | None = None


class BookGenerateResponse(BaseModel):
    """Réponse au déclenchement de la génération."""

    task_id: str | None = None
    message: str
    status: str  # "queued" | "skipped"


# ---- Endpoints ----


@router.get(
    "/{plan_id}/book",
    summary="Statut et URL du livre de recettes PDF",
    description=(
        "Retourne l'URL présignée du PDF si disponible, "
        "ou 404 si la génération n'a pas encore été lancée. "
        "Requiert le plan 'famille' ou supérieur. "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=BookStatus,
    responses={
        404: {"description": "PDF non encore généré pour ce plan."},
        403: {"description": "Plan famille requis pour accéder au PDF."},
    },
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def get_book_status(
    request: Request,
    plan_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
    _subscription: None = Depends(require_plan("famille")),
) -> Any:
    """
    Retourne le statut du PDF et l'URL présignée si disponible.

    Args:
        request: Requête FastAPI.
        plan_id: UUID du plan.
        session: Session DB.
        user: Payload JWT.
        _subscription: Vérification plan famille (injecté par require_plan).

    Returns:
        BookStatus avec l'URL présignée valable 7 jours.
    """
    await _verify_plan_ownership(session, plan_id, user)

    # Recherche dans weekly_books
    book_result = await session.execute(
        text(
            """
            SELECT pdf_r2_key, content_hash, generated_at::text
            FROM weekly_books
            WHERE plan_id = :pid
            LIMIT 1
            """
        ),
        {"pid": str(plan_id)},
    )
    book_row = book_result.mappings().one_or_none()

    if book_row is None or not book_row["pdf_r2_key"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Le PDF n'a pas encore été généré pour ce plan. "
                "Lancez la génération via POST /api/v1/plans/{plan_id}/book/generate."
            ),
        )

    # Génération de l'URL présignée
    try:
        from src.agents.book_generator.storage import BookStorage

        storage = BookStorage()
        pdf_url = storage.get_presigned_url(book_row["pdf_r2_key"])
    except Exception as exc:
        logger.error(
            "book_get_presigned_url_error",
            plan_id=str(plan_id),
            pdf_key=book_row["pdf_r2_key"],
            error=str(exc),
        )
        # URL indisponible temporairement — retourne quand même le statut
        pdf_url = None

    return BookStatus(
        plan_id=plan_id,
        status="ready",
        pdf_url=pdf_url,
        generated_at=book_row["generated_at"],
        content_hash=book_row["content_hash"],
    )


@router.post(
    "/{plan_id}/book/generate",
    summary="Déclencher la génération du PDF",
    description=(
        "Déclenche la génération asynchrone du livre de recettes PDF. "
        "La tâche est envoyée à la queue Celery pdf_high. "
        "Idempotent : si le hash du plan n'a pas changé, la génération est skippée. "
        "Requiert le plan 'famille' ou supérieur. "
        "Rate limit : 5/heure par utilisateur."
    ),
    response_model=BookGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"description": "Plan introuvable ou non validé."},
        403: {"description": "Plan famille requis."},
        429: {"description": "Rate limit dépassé (5 générations/heure)."},
    },
)
@limiter.limit("5/hour", key_func=get_user_key)
async def trigger_book_generation(
    request: Request,
    plan_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
    _subscription: None = Depends(require_plan("famille")),
) -> Any:
    """
    Déclenche la génération du PDF via Celery.

    Vérifie que le plan est en status 'validated' avant d'envoyer la tâche.
    Retourne 202 immédiatement — la génération est asynchrone.

    Args:
        request: Requête FastAPI.
        plan_id: UUID du plan à générer.
        session: Session DB.
        user: Payload JWT.
        _subscription: Vérification plan famille.
    """
    household_id = await _verify_plan_ownership(session, plan_id, user)

    # Vérifie que le plan est validé (status = 'validated')
    status_result = await session.execute(
        text("SELECT status FROM weekly_plans WHERE id = :pid LIMIT 1"),
        {"pid": str(plan_id)},
    )
    status_row = status_result.fetchone()

    if status_row is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} introuvable.")

    if status_row[0] != "validated":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Le plan doit être validé pour générer le PDF. "
                f"Statut actuel : '{status_row[0]}'. "
                f"Validez d'abord le plan via POST /api/v1/plans/{plan_id}/validate."
            ),
        )

    # Envoi de la tâche Celery (pdf_high, priorité 9)
    task_id = None
    try:
        from celery import current_app as celery_app

        task = celery_app.send_task(
            "book_generator.generate_book",
            args=[str(plan_id)],
            queue="pdf_high",
            priority=9,
        )
        task_id = task.id
    except Exception as exc:
        logger.error(
            "book_generate_celery_error",
            plan_id=str(plan_id),
            household_id=household_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service de génération PDF temporairement indisponible.",
        ) from exc

    logger.info(
        "book_generate_task_queued",
        plan_id=str(plan_id),
        household_id=household_id,
        task_id=task_id,
    )

    return BookGenerateResponse(
        task_id=task_id,
        message=f"Génération du livre de recettes en cours pour le plan {plan_id}.",
        status="queued",
    )
