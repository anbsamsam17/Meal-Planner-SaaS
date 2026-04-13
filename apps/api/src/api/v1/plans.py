"""
Endpoints pour la gestion des plans hebdomadaires.

Sécurité :
- Tous les endpoints requièrent une authentification JWT Supabase.
- L'isolation par foyer est garantie par les vérifications household_id.

Rate limits :
- Génération plan (LLM coûteux) : 10/h par user (LIMIT_LLM_PLAN_USER)
- Lecture : 300 req/min (niveau 2 user)
- Écriture légère (validate, swap) : 30 req/min

FIX Phase 1 mature (review 2026-04-12) :
- BUG #1  : ajout @limiter.limit() sur tous les endpoints
- BUG #4  : GET /me/current et GET /me/{plan_id}/shopping-list déclarés
             AVANT GET /{plan_id} pour éviter le conflit de routing FastAPI
             ("me" matché comme UUID → 422)
- BUG #5  : session unique par requête via Depends(get_db) — suppression
             du session splitting (3 sessions → 1 session par requête GET)
"""

import json
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.schemas.common import TaskResponse
from src.api.v1.schemas.plan import (
    AddMealRequest,
    GeneratePlanRequest,
    PlannedMealRead,
    RecipeSummary,
    ShoppingListItemRead,
    SwapMealRequest,
    ValidatePlanRequest,
    WeeklyPlanDetail,
    WeeklyPlanRead,
)
from src.core.config import get_settings
from src.core.rate_limit import (
    LIMIT_LLM_PLAN_USER,
    LIMIT_USER_READ,
    LIMIT_USER_WRITE,
    get_user_key,
    limiter,  # FIX Phase 1 mature (review 2026-04-12) — singleton pour @limiter.limit()
)
from src.core.security import TokenPayload, get_current_user

router = APIRouter(prefix="/plans", tags=["plans"])


def get_current_user_dep(request: Request) -> TokenPayload:
    """Dépendance FastAPI pour l'authentification JWT."""
    settings = get_settings()
    return get_current_user(request, settings.SUPABASE_ANON_KEY)


async def get_db(request: Request) -> AsyncSession:
    """
    Dépendance FastAPI retournant une session DB depuis app.state.

    FIX Phase 1 mature (review 2026-04-12) — BUG #5 :
    Session unique par requête via Depends(get_db). Remplace l'ancien pattern
    qui ouvrait 3 sessions distinctes (session splitting) pour chaque GET /plans/{id}.
    """
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de données non disponible.",
        )
    async with db_session_factory() as session:
        yield session


async def _get_user_household_id(session: AsyncSession, user_id: str) -> UUID:
    """
    Récupère l'ID du foyer de l'utilisateur ou lève 404.

    FIX Phase 1 mature (review 2026-04-12) — BUG #5 :
    Accepte la session en paramètre (injectée via Depends) au lieu
    d'ouvrir une nouvelle session en interne.

    Args:
        session: Session SQLAlchemy async injectée par Depends(get_db).
        user_id: UUID Supabase de l'utilisateur.

    Returns:
        UUID du foyer de l'utilisateur.
    """
    result = await session.execute(
        text(
            "SELECT household_id FROM household_members WHERE supabase_user_id = :user_id LIMIT 1"
        ),
        {"user_id": user_id},
    )
    row = result.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vous n'appartenez à aucun foyer. Créez-en un via POST /api/v1/households.",
        )
    return row[0]


# =========================================================================
# FIX Phase 1 mature (review 2026-04-12) — BUG #4 :
# Les routes statiques (/me/current, /me/{plan_id}/shopping-list)
# DOIVENT être déclarées AVANT les routes dynamiques (/{plan_id}).
# FastAPI résout les routes dans l'ordre de déclaration.
# Si /{plan_id} est déclaré en premier, "me" est capturé comme plan_id
# → UUID("me") → ValueError → 422 Unprocessable Entity.
# =========================================================================


# ---- POST /plans/generate ---- (statique, avant les routes dynamiques)

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit LLM 10/h par user
@router.post(
    "/generate",
    summary="Générer un plan hebdomadaire",
    description=(
        "Déclenche la génération asynchrone d'un plan via l'agent WEEKLY_PLANNER (Celery). "
        "Retourne un task_id pour suivre l'état. "
        f"Rate limit : {LIMIT_LLM_PLAN_USER} par utilisateur (LLM coûteux)."
    ),
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "L'utilisateur n'appartient à aucun foyer."},
        429: {"description": "Rate limit LLM dépassé (10 plans/heure)."},
    },
)
@limiter.limit(LIMIT_LLM_PLAN_USER, key_func=get_user_key)
async def generate_plan(
    request: Request,
    body: GeneratePlanRequest,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Déclenche la génération asynchrone d'un plan hebdomadaire.

    La tâche Celery weekly_planner.generate_plan est envoyée au broker Redis.
    L'API retourne immédiatement avec le task_id pour le polling.

    Args:
        request: Requête FastAPI (requis par slowapi pour key_func).
        body: Paramètres de génération (week_start, num_dinners).
        session: Session DB injectée (BUG #5 : session unique).
        user: Payload JWT.

    Returns:
        TaskResponse avec le task_id Celery.
    """
    household_id = await _get_user_household_id(session, user.user_id)

    logger.info(
        "plan_generate_sync_start",
        household_id=str(household_id),
        week_start=str(body.week_start),
        max_time=body.max_time,
        budget=body.effective_budget,
        style=body.style,
    )

    # Generation SYNCHRONE -- selectionne des recettes et cree le plan directement
    # Plus fiable que Celery pour la v1 (pas de dependance Redis inter-containers)
    try:
        # 0. Supprimer l'ancien plan si il existe (regeneration)
        await session.execute(
            text("""
                DELETE FROM planned_meals WHERE plan_id IN (
                    SELECT id FROM weekly_plans WHERE household_id = :hid AND week_start = :ws
                )
            """),
            {"hid": str(household_id), "ws": body.week_start},
        )
        await session.execute(
            text("""
                DELETE FROM weekly_plans WHERE household_id = :hid AND week_start = :ws
            """),
            {"hid": str(household_id), "ws": body.week_start},
        )

        # 1. Construire la query filtree selon les preferences utilisateur
        conditions = ["quality_score >= 0.6", "NOT ('dessert' = ANY(tags))"]
        params: dict[str, object] = {"limit": body.num_dinners * 6}

        if body.max_time:
            conditions.append("total_time_min <= :max_time")
            params["max_time"] = body.max_time

        effective_budget = body.effective_budget
        if effective_budget:
            conditions.append(":budget = ANY(tags)")
            params["budget"] = effective_budget

        if body.style == "végétarien":
            conditions.append("'végétarien' = ANY(tags)")
        elif body.style == "protéiné":
            conditions.append("NOT ('végétarien' = ANY(tags))")
            conditions.append("NOT ('vegan' = ANY(tags))")
        elif body.style == "léger":
            conditions.append("difficulty <= 2")

        where = " AND ".join(conditions)

        candidates_result = await session.execute(
            text(f"""
                SELECT id, title, cuisine_type, total_time_min, difficulty, tags
                FROM recipes WHERE {where}
                ORDER BY RANDOM() LIMIT :limit
            """),
            params,
        )
        candidates = candidates_result.mappings().all()

        if len(candidates) < body.num_dinners:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "Pas assez de recettes en base correspondant aux filtres pour générer un plan.",
            )

        # 2. Selectionner N recettes diversifiees (cuisines variees)
        selected = []
        cuisines_seen: set[str] = set()
        for c in candidates:
            if len(selected) >= body.num_dinners:
                break
            cuisine = c.get("cuisine_type", "")
            # Favoriser la diversite de cuisines
            if cuisine not in cuisines_seen or len(selected) >= body.num_dinners - 2:
                selected.append(c)
                cuisines_seen.add(cuisine)

        # Completer si pas assez
        if len(selected) < body.num_dinners:
            remaining = [c for c in candidates if c not in selected]
            selected.extend(remaining[: body.num_dinners - len(selected)])

        # 3. Creer le plan en base
        plan_result = await session.execute(
            text("""
                INSERT INTO weekly_plans (id, household_id, week_start, status)
                VALUES (gen_random_uuid(), :hid, :ws, 'draft')
                RETURNING id
            """),
            {"hid": str(household_id), "ws": body.week_start},
        )
        plan_id = str(plan_result.fetchone()[0])

        # 4. Inserer les meals (1 par jour, du lundi au dimanche)
        for i, recipe in enumerate(selected):
            day_of_week = i + 1  # 1=lundi, 2=mardi, etc.
            await session.execute(
                text("""
                    INSERT INTO planned_meals (id, plan_id, day_of_week, slot, recipe_id, servings_adjusted)
                    VALUES (gen_random_uuid(), :pid, :dow, 'dinner', :rid, 4)
                """),
                {"pid": plan_id, "dow": day_of_week, "rid": str(recipe["id"])},
            )

        await session.commit()

        logger.info("plan_generate_sync_done", plan_id=plan_id, recipes=len(selected))

        return TaskResponse(
            task_id=plan_id,
            status="completed",
            message=f"Plan de {len(selected)} dîners créé pour la semaine du {body.week_start}.",
            poll_url="/api/v1/plans/me/current",
        )

    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        logger.error("plan_generate_sync_error", error=str(exc), error_type=type(exc).__name__)
        raise HTTPException(500, f"Erreur lors de la génération : {type(exc).__name__}")


# ---- GET /plans/me/current ----
# FIX Phase 1 mature (review 2026-04-12) — BUG #4 : déclaré AVANT /{plan_id}

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit lecture 300/min par user
@router.get(
    "/me/current",
    summary="Plan de la semaine en cours",
    description=(
        "Retourne le plan de la semaine courante du foyer de l'utilisateur. "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=WeeklyPlanDetail | None,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Aucun plan pour la semaine en cours."},
    },
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def get_current_plan(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Récupère le plan de la semaine courante (week_start = lundi de cette semaine).

    FIX Phase 1 mature (review 2026-04-12) — BUG #5 : session unique via Depends(get_db).

    Args:
        request: Requête FastAPI (requis par slowapi).
        session: Session DB injectée (session unique par requête).
        user: Payload JWT.

    Returns:
        WeeklyPlanDetail ou None si aucun plan cette semaine.
    """
    from datetime import timedelta

    try:
        household_id = await _get_user_household_id(session, user.user_id)

        today = date.today()
        monday = today - timedelta(days=today.weekday())

        logger.info("get_current_plan_query", household_id=str(household_id), monday=str(monday))

        result = await session.execute(
            text(
                "SELECT id FROM weekly_plans WHERE household_id = :hid AND week_start = :ws LIMIT 1"
            ),
            {"hid": str(household_id), "ws": monday},
        )
        row = result.fetchone()

        if row is None:
            return None

        plan_id = row[0]
        logger.info("get_current_plan_found", plan_id=str(plan_id))
        return await _get_plan_detail(session, plan_id)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_current_plan_error", error=str(exc), error_type=type(exc).__name__)
        raise HTTPException(500, f"Erreur: {type(exc).__name__}: {str(exc)[:200]}")


# ---- GET /plans/me/{plan_id}/shopping-list ----
# FIX Phase 1 mature (review 2026-04-12) — BUG #4 : déclaré AVANT /{plan_id}

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit lecture 300/min par user
@router.get(
    "/me/{plan_id}/shopping-list",
    summary="Liste de courses d'un plan",
    description=(
        "Retourne la liste de courses consolidée d'un plan. "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=list[ShoppingListItemRead],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Plan ou liste de courses introuvable."},
    },
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def get_shopping_list(
    request: Request,
    plan_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Récupère la liste de courses d'un plan.

    FIX Phase 1 mature (review 2026-04-12) — BUG #5 : session unique via Depends(get_db).

    Args:
        request: Requête FastAPI (requis par slowapi).
        plan_id: UUID du plan.
        session: Session DB injectée (session unique par requête).
        user: Payload JWT.

    Returns:
        Liste d'items de courses avec rayons et quantités.
    """
    household_id = await _get_user_household_id(session, user.user_id)

    plan_result = await session.execute(
        text("SELECT household_id FROM weekly_plans WHERE id = :plan_id"),
        {"plan_id": str(plan_id)},
    )
    plan_row = plan_result.fetchone()

    if plan_row is None or str(plan_row[0]) != str(household_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} introuvable dans votre foyer.",
        )

    sl_result = await session.execute(
        text("SELECT items FROM shopping_lists WHERE plan_id = :plan_id"),
        {"plan_id": str(plan_id)},
    )
    sl_row = sl_result.fetchone()

    if sl_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Liste de courses non encore générée pour ce plan.",
        )

    items_raw = sl_row[0]
    if isinstance(items_raw, str):
        items_raw = json.loads(items_raw)

    return [ShoppingListItemRead.model_validate(item) for item in (items_raw or [])]


# ---- GET /plans/me/history ----
# Stub Phase 2 : retourne l'historique des plans du foyer.
# Déclaré AVANT /{plan_id} pour éviter que "me" soit capturé comme UUID.

@router.get(
    "/me/history",
    summary="Historique des plans hebdomadaires",
    description=(
        "Retourne la liste des plans passés du foyer, triés du plus récent au plus ancien. "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=list[WeeklyPlanRead],
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def get_plans_history(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Retourne l'historique des plans hebdomadaires du foyer de l'utilisateur.

    Stub Phase 2 (2026-04-12) : endpoint créé pour corriger les 404 Railway.
    La pagination et les filtres avancés seront ajoutés en Phase 2 complète.

    Args:
        request: Requête FastAPI (requis par slowapi).
        session: Session DB injectée.
        user: Payload JWT.

    Returns:
        Liste de WeeklyPlanRead triée par week_start décroissant.
    """
    household_id = await _get_user_household_id(session, user.user_id)

    result = await session.execute(
        text(
            """
            SELECT id, household_id, week_start, status, validated_at, created_at, updated_at
            FROM weekly_plans
            WHERE household_id = :household_id
            ORDER BY week_start DESC
            LIMIT 50
            """
        ),
        {"household_id": str(household_id)},
    )
    rows = result.mappings().all()

    logger.info(
        "plans_history_fetched",
        household_id=str(household_id),
        count=len(rows),
    )

    return [WeeklyPlanRead.model_validate(dict(row)) for row in rows]


# ---- GET /plans/{plan_id} ----
# FIX Phase 1 mature (review 2026-04-12) — BUG #4 : déclaré APRÈS /me/* (ordre critique)

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit lecture 300/min par user
@router.get(
    "/{plan_id}",
    summary="Détail d'un plan",
    description=(
        "Retourne un plan hebdomadaire avec ses repas et sa liste de courses. "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=WeeklyPlanDetail,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Plan introuvable."},
        status.HTTP_403_FORBIDDEN: {"description": "Ce plan n'appartient pas à votre foyer."},
    },
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def get_plan(
    request: Request,
    plan_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Récupère un plan hebdomadaire avec ses repas (jointure recettes) et la liste de courses.

    FIX Phase 1 mature (review 2026-04-12) — BUG #5 : session unique via Depends(get_db).
    Toutes les queries (household_id, vérification plan, détail plan) utilisent
    la même session → 1 connexion pool au lieu de 3.

    Args:
        request: Requête FastAPI (requis par slowapi).
        plan_id: UUID du plan.
        session: Session DB injectée (session unique par requête).
        user: Payload JWT.

    Returns:
        WeeklyPlanDetail complet.
    """
    household_id = await _get_user_household_id(session, user.user_id)

    # Vérification appartenance au foyer (isolation tenant)
    plan_result = await session.execute(
        text(
            """
            SELECT id, household_id, week_start, status, validated_at, created_at, updated_at
            FROM weekly_plans
            WHERE id = :plan_id
            LIMIT 1
            """
        ),
        {"plan_id": str(plan_id)},
    )
    plan_row = plan_result.mappings().one_or_none()

    if plan_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} introuvable.",
        )

    if str(plan_row["household_id"]) != str(household_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce plan n'appartient pas à votre foyer.",
        )

    return await _get_plan_detail(session, plan_id)


# ---- POST /plans/{plan_id}/validate ----

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit écriture 30/min par user
@router.post(
    "/{plan_id}/validate",
    summary="Valider un plan",
    description=(
        "Marque un plan comme validé (status 'draft' → 'validated'). "
        "Déclenchera ultérieurement BOOK_GENERATOR pour le PDF hebdomadaire. "
        f"Rate limit : {LIMIT_USER_WRITE}."
    ),
    response_model=WeeklyPlanRead,
    responses={
        status.HTTP_409_CONFLICT: {"description": "Le plan est déjà validé."},
        status.HTTP_403_FORBIDDEN: {"description": "Ce plan n'appartient pas à votre foyer."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def validate_plan(
    request: Request,
    plan_id: UUID,
    body: ValidatePlanRequest,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Valide le plan hebdomadaire (passage en status 'validated').

    FIX Phase 1 mature (review 2026-04-12) — BUG #5 : session unique via Depends(get_db).
    Le SELECT et l'UPDATE se font dans la même session (atomique, pas de TOCTOU).

    Args:
        request: Requête FastAPI (requis par slowapi).
        plan_id: UUID du plan à valider.
        body: Confirmation de validation.
        session: Session DB injectée.
        user: Payload JWT.

    Returns:
        WeeklyPlanRead avec le nouveau statut.
    """
    household_id = await _get_user_household_id(session, user.user_id)

    plan_result = await session.execute(
        text("SELECT id, household_id, status FROM weekly_plans WHERE id = :plan_id"),
        {"plan_id": str(plan_id)},
    )
    plan_row = plan_result.mappings().one_or_none()

    if plan_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} introuvable.",
        )

    if str(plan_row["household_id"]) != str(household_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce plan n'appartient pas à votre foyer.",
        )

    if plan_row["status"] == "validated":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce plan est déjà validé.",
        )

    # UPDATE dans la même session (atomique — même transaction que le SELECT)
    result = await session.execute(
        text(
            """
            UPDATE weekly_plans
            SET status = 'validated', validated_at = NOW(), updated_at = NOW()
            WHERE id = :plan_id AND status = 'draft'
            RETURNING id, household_id, week_start, status, validated_at, created_at, updated_at
            """
        ),
        {"plan_id": str(plan_id)},
    )
    updated = result.mappings().one_or_none()

    if updated is None:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce plan est déjà validé (modifié en parallèle).",
        )

    # -- Generation de la liste de courses a la validation --
    await _generate_shopping_list(session, plan_id)

    await session.commit()

    logger.info(
        "plan_validated",
        plan_id=str(plan_id),
        household_id=str(household_id),
        by_user=user.user_id,
    )

    return WeeklyPlanRead.model_validate(dict(updated))


# ---- PATCH /plans/{plan_id}/meals/{meal_id} ----

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit écriture 30/min par user
@router.patch(
    "/{plan_id}/meals/{meal_id}",
    summary="Remplacer une recette dans le plan",
    description=(
        "Remplace une recette dans un plan en statut 'draft'. "
        f"Rate limit : {LIMIT_USER_WRITE}."
    ),
    response_model=PlannedMealRead,
    responses={
        status.HTTP_409_CONFLICT: {"description": "Le plan est déjà validé — impossible de modifier."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def swap_meal(
    request: Request,
    plan_id: UUID,
    meal_id: UUID,
    body: SwapMealRequest,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Remplace une recette dans un plan draft (swap utilisateur).

    FIX Phase 1 mature (review 2026-04-12) — BUG #5 : session unique via Depends(get_db).

    Args:
        request: Requête FastAPI (requis par slowapi).
        plan_id: UUID du plan.
        meal_id: UUID du PlannedMeal à remplacer.
        body: UUID de la nouvelle recette.
        session: Session DB injectée.
        user: Payload JWT.

    Returns:
        PlannedMealRead mis à jour.
    """
    household_id = await _get_user_household_id(session, user.user_id)

    # Vérification plan + status (même session)
    plan_result = await session.execute(
        text("SELECT household_id, status FROM weekly_plans WHERE id = :plan_id"),
        {"plan_id": str(plan_id)},
    )
    plan_row = plan_result.mappings().one_or_none()

    if plan_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} introuvable.",
        )

    if str(plan_row["household_id"]) != str(household_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce plan n'appartient pas à votre foyer.",
        )

    if plan_row["status"] != "draft":
        await session.execute(
            text("UPDATE weekly_plans SET status = 'draft', validated_at = NULL WHERE id = :pid"),
            {"pid": str(plan_id)},
        )
        logger.info("plan_reverted_to_draft", plan_id=str(plan_id))

    meal_result = await session.execute(
        text(
            """
            UPDATE planned_meals
            SET recipe_id = :new_recipe_id
            WHERE id = :meal_id AND plan_id = :plan_id
            RETURNING id, plan_id, day_of_week, slot, recipe_id, servings_adjusted
            """
        ),
        {
            "meal_id": str(meal_id),
            "plan_id": str(plan_id),
            "new_recipe_id": str(body.new_recipe_id),
        },
    )
    meal_row = meal_result.mappings().one_or_none()
    await session.commit()

    if meal_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repas {meal_id} introuvable dans ce plan.",
        )

    logger.info(
        "plan_meal_swapped",
        plan_id=str(plan_id),
        meal_id=str(meal_id),
        new_recipe_id=str(body.new_recipe_id),
        by_user=user.user_id,
    )

    return PlannedMealRead.model_validate(dict(meal_row))


# ---- POST /plans/{plan_id}/meals/add ----

@router.post(
    "/{plan_id}/meals/add",
    summary="Ajouter un repas au plan",
    description=(
        "Ajoute un repas à un plan en statut 'draft' (ex: samedi ou dimanche). "
        "Si un repas existe déjà pour ce jour et ce slot, il est remplacé. "
        f"Rate limit : {LIMIT_USER_WRITE}."
    ),
    response_model=PlannedMealRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Plan ou recette introuvable."},
        status.HTTP_409_CONFLICT: {"description": "Le plan est déjà validé."},
        status.HTTP_403_FORBIDDEN: {"description": "Ce plan n'appartient pas à votre foyer."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def add_meal_to_plan(
    request: Request,
    plan_id: UUID,
    body: AddMealRequest,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Ajoute un repas manuellement à un plan draft (ex: samedi/dimanche).

    Utilise ON CONFLICT pour remplacer le repas existant si le jour et le slot
    sont déjà occupés (upsert).

    Args:
        request: Requête FastAPI (requis par slowapi).
        plan_id: UUID du plan.
        body: Jour de la semaine et recipe_id.
        session: Session DB injectée.
        user: Payload JWT.

    Returns:
        PlannedMealRead du repas créé/remplacé.
    """
    household_id = await _get_user_household_id(session, user.user_id)

    # Verification plan + status
    plan_result = await session.execute(
        text("SELECT household_id, status FROM weekly_plans WHERE id = :plan_id"),
        {"plan_id": str(plan_id)},
    )
    plan_row = plan_result.mappings().one_or_none()

    if plan_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} introuvable.",
        )

    if str(plan_row["household_id"]) != str(household_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce plan n'appartient pas à votre foyer.",
        )

    if plan_row["status"] != "draft":
        await session.execute(
            text("UPDATE weekly_plans SET status = 'draft', validated_at = NULL WHERE id = :pid"),
            {"pid": str(plan_id)},
        )

    # Verifier que la recette existe
    recipe_check = await session.execute(
        text("SELECT id FROM recipes WHERE id = :rid"),
        {"rid": str(body.recipe_id)},
    )
    if recipe_check.fetchone() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recette {body.recipe_id} introuvable.",
        )

    # Upsert : ON CONFLICT sur (plan_id, day_of_week, slot) remplace la recette
    meal_result = await session.execute(
        text("""
            INSERT INTO planned_meals (id, plan_id, day_of_week, slot, recipe_id, servings_adjusted)
            VALUES (gen_random_uuid(), :pid, :dow, 'dinner', :rid, 4)
            ON CONFLICT (plan_id, day_of_week, slot)
            DO UPDATE SET recipe_id = :rid
            RETURNING id, plan_id, day_of_week, slot, recipe_id, servings_adjusted
        """),
        {
            "pid": str(plan_id),
            "dow": body.day_of_week,
            "rid": str(body.recipe_id),
        },
    )
    meal_row = meal_result.mappings().one()
    await session.commit()

    logger.info(
        "plan_meal_added",
        plan_id=str(plan_id),
        day_of_week=body.day_of_week,
        recipe_id=str(body.recipe_id),
        by_user=user.user_id,
    )

    return PlannedMealRead.model_validate(dict(meal_row))


# ---- GET /plans/{plan_id}/suggestions ----

@router.get(
    "/{plan_id}/suggestions",
    summary="Suggestions de recettes pour swap",
    description=(
        "Retourne 6 recettes alternatives pour remplacer un repas dans le plan. "
        "Exclut les recettes déjà présentes dans le plan et les desserts. "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=list[RecipeSummary],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Plan introuvable."},
        status.HTTP_403_FORBIDDEN: {"description": "Ce plan n'appartient pas à votre foyer."},
    },
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def get_recipe_suggestions(
    request: Request,
    plan_id: UUID,
    style: str | None = None,
    max_time: int | None = None,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Retourne des recettes alternatives pour le swap individuel.

    Exclut les recettes deja dans le plan pour garantir la diversite.
    Filtre optionnel par style culinaire et temps max.

    Args:
        request: Requête FastAPI (requis par slowapi).
        plan_id: UUID du plan.
        style: Filtre style (rapide, protéiné, végétarien, léger).
        max_time: Temps max en minutes.
        session: Session DB injectée.
        user: Payload JWT.

    Returns:
        Liste de 6 RecipeSummary matchant les critères.
    """
    household_id = await _get_user_household_id(session, user.user_id)

    # Verification plan + appartenance
    plan_result = await session.execute(
        text("SELECT household_id FROM weekly_plans WHERE id = :plan_id"),
        {"plan_id": str(plan_id)},
    )
    plan_row = plan_result.mappings().one_or_none()

    if plan_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} introuvable.",
        )

    if str(plan_row["household_id"]) != str(household_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce plan n'appartient pas à votre foyer.",
        )

    # Recuperer les recipe_ids deja dans le plan (a exclure)
    existing_result = await session.execute(
        text("SELECT recipe_id FROM planned_meals WHERE plan_id = :pid"),
        {"pid": str(plan_id)},
    )
    existing_ids = [str(row[0]) for row in existing_result.fetchall()]

    # Construire la query filtree
    conditions = ["quality_score >= 0.6", "NOT ('dessert' = ANY(tags))"]
    params: dict[str, object] = {"limit": 6}

    if existing_ids:
        conditions.append("id != ALL(:existing_ids)")
        params["existing_ids"] = existing_ids

    if max_time:
        conditions.append("total_time_min <= :max_time")
        params["max_time"] = max_time

    if style == "végétarien":
        conditions.append("'végétarien' = ANY(tags)")
    elif style == "protéiné":
        conditions.append("NOT ('végétarien' = ANY(tags))")
        conditions.append("NOT ('vegan' = ANY(tags))")
    elif style == "léger":
        conditions.append("difficulty <= 2")
    elif style == "rapide":
        conditions.append("total_time_min <= 30")

    where = " AND ".join(conditions)

    suggestions_result = await session.execute(
        text(f"""
            SELECT id, title, slug, photo_url, total_time_min,
                   difficulty, cuisine_type, tags, quality_score
            FROM recipes WHERE {where}
            ORDER BY RANDOM() LIMIT :limit
        """),
        params,
    )
    rows = suggestions_result.mappings().all()

    suggestions = []
    for r_row in rows:
        r_dict = dict(r_row)
        tags_raw = r_dict.get("tags")
        if isinstance(tags_raw, str):
            r_dict["tags"] = json.loads(tags_raw)
        elif tags_raw is None:
            r_dict["tags"] = []
        suggestions.append(RecipeSummary.model_validate(r_dict))

    return suggestions


# ---- Helpers ----

# Mapping categorie ingredient -> rayon supermarche
RAYON_MAP = {
    "other": "Epicerie",
    "meat": "Boucherie",
    "poultry": "Volaille",
    "fish": "Poissonnerie",
    "dairy": "Cremerie",
    "vegetable": "Fruits & legumes",
    "fruit": "Fruits & legumes",
    "spice": "Epices",
    "grain": "Epicerie",
    "oil": "Huiles & condiments",
    "sauce": "Sauces",
    "herb": "Herbes fraiches",
}


def _map_category_to_rayon(cat: str) -> str:
    """Mappe une categorie d'ingredient a un rayon de supermarche."""
    return RAYON_MAP.get(cat, "Epicerie")


async def _generate_shopping_list(session: AsyncSession, plan_id: Any) -> None:
    """
    Genere la liste de courses a partir des ingredients des recettes du plan.

    Agregue les quantites par ingredient canonique et insere/met a jour
    la shopping_list en base avec ON CONFLICT pour eviter les doublons.

    Args:
        session: Session SQLAlchemy async (meme transaction que la validation).
        plan_id: UUID du plan valide.
    """
    from collections import defaultdict

    ingredients_result = await session.execute(
        text("""
            SELECT i.canonical_name, i.category, ri.unit, ri.notes, ri.quantity, ri.position
            FROM planned_meals pm
            JOIN recipe_ingredients ri ON ri.recipe_id = pm.recipe_id
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE pm.plan_id = :pid
            ORDER BY i.category, i.canonical_name
        """),
        {"pid": str(plan_id)},
    )

    # Agreger par ingredient
    items_by_name: dict[str, dict] = defaultdict(
        lambda: {"quantities": [], "category": "other"}
    )
    for row in ingredients_result.mappings().all():
        name = row["canonical_name"]
        items_by_name[name]["category"] = row["category"] or "other"
        items_by_name[name]["canonical_name"] = name
        items_by_name[name]["quantities"].append(
            {
                "quantity": float(row["quantity"] or 1),
                "unit": row["unit"] or "",
                "from_recipe": row["notes"] or name,
            }
        )

    # Construire le JSON et INSERT/UPDATE dans shopping_lists
    items_json = json.dumps(
        [
            {
                "ingredient_id": "",
                "canonical_name": name,
                "category": data["category"],
                "rayon": _map_category_to_rayon(data["category"]),
                "quantities": data["quantities"],
                "checked": False,
            }
            for name, data in items_by_name.items()
        ]
    )

    await session.execute(
        text("""
            INSERT INTO shopping_lists (id, plan_id, items, generated_at)
            VALUES (gen_random_uuid(), :pid, CAST(:items AS jsonb), now())
            ON CONFLICT (plan_id) DO UPDATE SET items = CAST(:items AS jsonb), generated_at = now()
        """),
        {"pid": str(plan_id), "items": items_json},
    )

    logger.info(
        "shopping_list_generated",
        plan_id=str(plan_id),
        items_count=len(items_by_name),
    )


async def _get_plan_detail(session: AsyncSession, plan_id: Any) -> WeeklyPlanDetail:
    """
    Récupère un plan complet avec les repas et la liste de courses.

    FIX Phase 1 mature (review 2026-04-12) — BUG #5 :
    Accepte la session en paramètre au lieu d'ouvrir une nouvelle session.
    Toutes les queries sont exécutées dans la même session → 1 connexion pool.

    Args:
        session: Session SQLAlchemy async injectée par Depends(get_db).
        plan_id: UUID du plan.

    Returns:
        WeeklyPlanDetail complet.
    """
    # Plan de base
    plan_result = await session.execute(
        text(
            """
            SELECT id, household_id, week_start, status, validated_at, created_at, updated_at
            FROM weekly_plans WHERE id = :plan_id
            """
        ),
        {"plan_id": str(plan_id)},
    )
    plan_row = plan_result.mappings().one_or_none()

    if plan_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} introuvable.",
        )

    # Repas avec jointure recettes (evite N+1) -- meme session
    meals_result = await session.execute(
        text(
            """
            SELECT
                pm.id, pm.plan_id, pm.day_of_week, pm.slot,
                pm.recipe_id, pm.servings_adjusted,
                r.title AS recipe_title,
                r.cuisine_type AS recipe_cuisine_type,
                r.total_time_min AS recipe_total_time_min,
                r.difficulty AS recipe_difficulty,
                r.photo_url AS recipe_photo_url
            FROM planned_meals pm
            JOIN recipes r ON r.id = pm.recipe_id
            WHERE pm.plan_id = :plan_id
            ORDER BY pm.day_of_week ASC
            """
        ),
        {"plan_id": str(plan_id)},
    )
    meals_rows = meals_result.mappings().all()

    # FIX BLOQUANT 5 (audit 2026-04-13) : recuperer les recettes completes
    # pour le champ recipes[] attendu par le frontend (recipesById lookup).
    recipe_ids = list({str(row["recipe_id"]) for row in meals_rows})

    recipes: list[RecipeSummary] = []
    if recipe_ids:
        recipes_result = await session.execute(
            text(
                """
                SELECT id, title, slug, photo_url, total_time_min,
                       difficulty, cuisine_type, tags, quality_score
                FROM recipes
                WHERE id = ANY(:ids)
                """
            ),
            {"ids": recipe_ids},
        )
        recipes_rows = recipes_result.mappings().all()

        for r_row in recipes_rows:
            r_dict = dict(r_row)
            # tags peut etre une string JSON ou deja une liste
            tags_raw = r_dict.get("tags")
            if isinstance(tags_raw, str):
                r_dict["tags"] = json.loads(tags_raw)
            elif tags_raw is None:
                r_dict["tags"] = []
            recipes.append(RecipeSummary.model_validate(r_dict))

    # Liste de courses -- meme session
    sl_result = await session.execute(
        text("SELECT items FROM shopping_lists WHERE plan_id = :plan_id"),
        {"plan_id": str(plan_id)},
    )
    sl_row = sl_result.fetchone()

    meals = [PlannedMealRead.model_validate(dict(row)) for row in meals_rows]

    shopping_list: list[ShoppingListItemRead] = []
    if sl_row and sl_row[0]:
        items_raw = sl_row[0]
        if isinstance(items_raw, str):
            items_raw = json.loads(items_raw)
        shopping_list = [ShoppingListItemRead.model_validate(item) for item in items_raw]

    plan_dict = dict(plan_row)

    return WeeklyPlanDetail(
        id=plan_dict["id"],
        household_id=plan_dict["household_id"],
        week_start=plan_dict["week_start"],
        status=plan_dict["status"],
        validated_at=plan_dict.get("validated_at"),
        created_at=plan_dict["created_at"],
        updated_at=plan_dict["updated_at"],
        meals=meals,
        recipes=recipes,
        shopping_list=shopping_list,
    )
