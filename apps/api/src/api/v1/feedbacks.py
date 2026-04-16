"""
Endpoints pour la gestion des feedbacks utilisateurs sur les recettes.

Les feedbacks alimentent le moteur de recommandation TASTE_PROFILE.
Chaque interaction (note, skip, favori) améliore les suggestions futures.

Politique UPSERT (favoris) :
- Pour feedback_type='favorited' : INSERT OR UPDATE pour éviter les doublons.
  Si un favori existe déjà pour le même (member_id, recipe_id, feedback_type),
  on met à jour le timestamp plutôt que de créer un doublon.
- Pour les autres types ('cooked', 'skipped') : INSERT classique (journal immuable).

Conformité RGPD : la suppression passe par une procédure service_role
dédiée avec audit_log (Phase 2).

Après chaque feedback : tâche Celery TASTE_PROFILE déclenchée (stub en v0).

Rate limits :
- POST : 30 req/min (écriture)
- GET : 300 req/min (lecture)
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from sqlalchemy import text

from src.api.v1.recipes import RecipeOut
from src.api.v1.schemas.common import PaginatedResponse
from src.api.v1.schemas.feedback import FeedbackCreate, FeedbackRead
from src.core.config import get_settings
from src.core.rate_limit import (
    LIMIT_USER_READ,
    LIMIT_USER_WRITE,
    get_user_key,
    limiter,  # FIX Phase 1 mature (review 2026-04-12) — singleton pour @limiter.limit()
)
from src.core.security import TokenPayload, get_current_user

router = APIRouter(prefix="/feedbacks", tags=["feedbacks"])


def get_current_user_dep(request: Request) -> TokenPayload:
    """Dépendance FastAPI pour l'authentification JWT."""
    settings = get_settings()
    return get_current_user(request, settings.SUPABASE_ANON_KEY)


async def _get_db(request: Request):
    """Retourne la factory de sessions DB."""
    db_session = getattr(request.app.state, "db_session_factory", None)
    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de données non disponible.",
        )
    return db_session


async def _get_member_info(db_session: Any, user_id: str) -> tuple[UUID, UUID]:
    """Récupère le member_id et household_id de l'utilisateur connecté."""
    async with db_session() as session:
        result = await session.execute(
            text(
                """
                SELECT id, household_id
                FROM household_members
                WHERE supabase_user_id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
        row = result.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vous n'appartenez à aucun foyer. Créez-en un via POST /api/v1/households.",
        )
    return row[0], row[1]


# ---- POST /feedbacks ----

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit écriture 30/min par user
@router.post(
    "",
    summary="Soumettre un feedback",
    description=(
        "Enregistre une interaction utilisateur sur une recette (note, skip, favori). "
        "Déclenche une tâche async pour mettre à jour le profil de goût (TASTE_PROFILE). "
        f"Rate limit : {LIMIT_USER_WRITE}."
    ),
    response_model=FeedbackRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recette introuvable."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentification requise."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def submit_feedback(
    request: Request,
    body: FeedbackCreate,
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Enregistre un feedback utilisateur et déclenche la mise à jour du profil de goût.

    Args:
        body: Données du feedback (recipe_id, type, rating, notes).
        request: Requête FastAPI.
        user: Payload JWT.

    Returns:
        FeedbackRead du feedback créé.
    """
    db_session = await _get_db(request)
    member_id, household_id = await _get_member_info(db_session, user.user_id)

    # Vérification que la recette existe
    async with db_session() as session:
        recipe_check = await session.execute(
            text("SELECT id FROM recipes WHERE id = :recipe_id LIMIT 1"),
            {"recipe_id": str(body.recipe_id)},
        )
        if recipe_check.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recette {body.recipe_id} introuvable.",
            )

        # UPSERT pour favoris : évite les doublons (member, recipe, type).
        # Pour les autres types (cooked, skipped) : INSERT classique (journal immuable).
        if body.feedback_type == "favorited":
            result = await session.execute(
                text(
                    """
                    INSERT INTO recipe_feedbacks (
                        household_id, member_id, recipe_id,
                        feedback_type, rating, notes
                    ) VALUES (
                        :household_id, :member_id, :recipe_id,
                        :feedback_type, :rating, :notes
                    )
                    ON CONFLICT (member_id, recipe_id, feedback_type)
                    DO UPDATE SET
                        rating = EXCLUDED.rating,
                        notes = EXCLUDED.notes,
                        created_at = now()
                    RETURNING id, household_id, member_id, recipe_id,
                              feedback_type, rating, notes, created_at
                    """
                ),
                {
                    "household_id": str(household_id),
                    "member_id": str(member_id),
                    "recipe_id": str(body.recipe_id),
                    "feedback_type": body.feedback_type,
                    "rating": body.rating,
                    "notes": body.notes,
                },
            )
        else:
            result = await session.execute(
                text(
                    """
                    INSERT INTO recipe_feedbacks (
                        household_id, member_id, recipe_id,
                        feedback_type, rating, notes
                    ) VALUES (
                        :household_id, :member_id, :recipe_id,
                        :feedback_type, :rating, :notes
                    )
                    RETURNING id, household_id, member_id, recipe_id,
                              feedback_type, rating, notes, created_at
                    """
                ),
                {
                    "household_id": str(household_id),
                    "member_id": str(member_id),
                    "recipe_id": str(body.recipe_id),
                    "feedback_type": body.feedback_type,
                    "rating": body.rating,
                    "notes": body.notes,
                },
            )
        feedback_row = result.mappings().one()
        await session.commit()

    feedback_id = str(feedback_row["id"])

    logger.info(
        "feedback_submitted",
        feedback_id=feedback_id,
        member_id=str(member_id),
        recipe_id=str(body.recipe_id),
        feedback_type=body.feedback_type,
        rating=body.rating,
    )

    # Déclenchement async de la mise à jour du vecteur de goût (TASTE_PROFILE)
    # En v0 : stub — la tâche sera implémentée en Phase 2
    try:
        _trigger_taste_profile_update(str(member_id), str(body.recipe_id), body.feedback_type)
    except Exception as exc:
        # Non bloquant : le feedback est enregistré même si le trigger échoue
        logger.warning(
            "taste_profile_trigger_failed",
            feedback_id=feedback_id,
            error=str(exc),
        )

    return FeedbackRead.model_validate(dict(feedback_row))


# ---- GET /feedbacks/me ----

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit lecture 300/min par user
@router.get(
    "/me",
    summary="Historique des feedbacks",
    description=(
        "Retourne l'historique des feedbacks de l'utilisateur authentifié. "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=PaginatedResponse[FeedbackRead],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentification requise."},
    },
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def get_my_feedbacks(
    request: Request,
    user: TokenPayload = Depends(get_current_user_dep),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    feedback_type: str | None = Query(
        default=None,
        description="Filtrer par type : 'cooked', 'skipped', 'favorited'.",
        pattern="^(cooked|skipped|favorited)$",
    ),
) -> Any:
    """
    Retourne l'historique paginé des feedbacks de l'utilisateur.

    Args:
        request: Requête FastAPI.
        user: Payload JWT.
        page: Page courante.
        per_page: Éléments par page.
        feedback_type: Filtre optionnel sur le type de feedback.

    Returns:
        PaginatedResponse[FeedbackRead]
    """
    db_session = await _get_db(request)
    member_id, _household_id = await _get_member_info(db_session, user.user_id)

    offset = (page - 1) * per_page
    params: dict = {
        "member_id": str(member_id),
        "limit": per_page,
        "offset": offset,
    }

    type_filter = ""
    if feedback_type:
        type_filter = "AND feedback_type = :feedback_type"
        params["feedback_type"] = feedback_type

    async with db_session() as session:
        count_result = await session.execute(
            text(
                f"SELECT COUNT(*) FROM recipe_feedbacks WHERE member_id = :member_id {type_filter}"
            ),
            params,
        )
        total = count_result.scalar() or 0

        rows_result = await session.execute(
            text(
                f"""
                SELECT id, household_id, member_id, recipe_id,
                       feedback_type, rating, notes, created_at
                FROM recipe_feedbacks
                WHERE member_id = :member_id {type_filter}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        rows = rows_result.mappings().all()

    feedbacks = [FeedbackRead.model_validate(dict(row)) for row in rows]

    return PaginatedResponse.build(
        results=feedbacks,
        total=total,
        page=page,
        per_page=per_page,
    )


# ---- GET /feedbacks/me/favorites ----

@router.get(
    "/me/favorites",
    summary="Recettes en favoris",
    description=(
        "Retourne les recettes marquées en favori par l'utilisateur authentifié. "
        "Résultat paginé, ordonné du plus récent au plus ancien. "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=PaginatedResponse[RecipeOut],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentification requise."},
    },
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def get_my_favorites(
    request: Request,
    user: TokenPayload = Depends(get_current_user_dep),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> Any:
    """
    Retourne les recettes favorites paginées de l'utilisateur.

    Effectue un JOIN entre recipe_feedbacks et recipes pour retourner
    des objets RecipeOut complets (pas juste les feedbacks).

    Args:
        request: Requête FastAPI.
        user: Payload JWT.
        page: Page courante (1-indexed).
        per_page: Éléments par page (max 100).

    Returns:
        PaginatedResponse[RecipeOut]
    """
    db_session = await _get_db(request)
    member_id, _household_id = await _get_member_info(db_session, user.user_id)

    offset = (page - 1) * per_page
    params: dict = {
        "member_id": str(member_id),
        "limit": per_page,
        "offset": offset,
    }

    async with db_session() as session:
        count_result = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM recipe_feedbacks rf
                WHERE rf.member_id = :member_id
                  AND rf.feedback_type = 'favorited'
                """
            ),
            params,
        )
        total = count_result.scalar() or 0

        rows_result = await session.execute(
            text(
                """
                SELECT
                    r.id,
                    r.title,
                    r.slug,
                    r.source,
                    r.servings,
                    r.prep_time_min,
                    r.cook_time_min,
                    r.total_time_min,
                    r.difficulty,
                    r.cuisine_type,
                    r.photo_url,
                    r.tags,
                    r.quality_score,
                    r.course,
                    r.nutrition
                FROM recipe_feedbacks rf
                JOIN recipes r ON r.id = rf.recipe_id
                WHERE rf.member_id = :member_id
                  AND rf.feedback_type = 'favorited'
                ORDER BY rf.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        rows = rows_result.mappings().all()

    recipes = [RecipeOut.model_validate(dict(row)) for row in rows]

    logger.info(
        "favorites_fetched",
        member_id=str(member_id),
        total=total,
        page=page,
        per_page=per_page,
    )

    return PaginatedResponse.build(
        results=recipes,
        total=total,
        page=page,
        per_page=per_page,
    )


# ---- Helper : déclenchement TASTE_PROFILE ----

def _trigger_taste_profile_update(
    member_id: str,
    recipe_id: str,
    feedback_type: str,
) -> None:
    """
    Déclenche la mise à jour du vecteur de goût via Celery (TASTE_PROFILE v0).

    Envoie la tâche "taste_profile.update_member_taste" sur la queue "embedding".
    Le vecteur de goût est recalculé en tenant compte du nouveau feedback.

    Non bloquant : si Celery n'est pas disponible, un log WARNING est émis
    et le feedback est quand même enregistré (graceful degradation).

    Args:
        member_id: UUID du membre ayant soumis le feedback.
        recipe_id: UUID de la recette notée (conservé pour le log).
        feedback_type: Type d'interaction (pour le log).
    """
    try:
        from celery import current_app as celery_app

        celery_app.send_task(
            "taste_profile.update_member_taste",
            args=[member_id],
            queue="embedding",
        )

        logger.info(
            "taste_profile_update_queued",
            member_id=member_id,
            recipe_id=recipe_id,
            feedback_type=feedback_type,
        )

    except Exception as exc:
        # Dégradation gracieuse : le feedback est enregistré même si Celery est KO.
        # Le vecteur sera recalculé au prochain feedback ou au batch nocturne (Phase 2).
        logger.warning(
            "taste_profile_update_celery_unavailable",
            member_id=member_id,
            recipe_id=recipe_id,
            feedback_type=feedback_type,
            error=str(exc),
            hint="Vecteur de goût non mis à jour — Celery indisponible.",
        )
