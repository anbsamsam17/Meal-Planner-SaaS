"""
Endpoints pour la gestion des foyers (Households).

Les foyers sont l'unité de multi-tenancy du système.
Chaque utilisateur Supabase appartient à exactement un foyer.

Sécurité :
- Tous les endpoints requièrent une authentification JWT Supabase.
- La création de foyer appelle la fonction SQL SECURITY DEFINER
  (crée atomiquement le foyer + le premier membre + configure la RLS session).
- La liste/modification des membres est restreinte au owner.

Rate limits :
- Lecture (GET) : 300 req/min (niveau 2 user)
- Écriture (POST/PATCH) : 30 req/min (niveau 2 write)
"""

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy import text

from src.api.v1.schemas.household import (
    HouseholdCreate,
    HouseholdRead,
    HouseholdUpdate,
    MemberCreate,
    MemberPreferenceCreate,
    MemberPreferenceRead,
    MemberRead,
)
from src.core.config import get_settings
from src.core.rate_limit import (
    LIMIT_USER_READ,
    LIMIT_USER_WRITE,
    get_user_key,
    limiter,  # FIX Phase 1 mature (review 2026-04-12) — singleton requis pour @limiter.limit()
)
from src.core.security import TokenPayload, get_current_user

router = APIRouter(prefix="/households", tags=["households"])


def get_current_user_dep(request: Request) -> TokenPayload:
    """Dépendance FastAPI pour l'authentification JWT."""
    settings = get_settings()
    return get_current_user(request, settings.SUPABASE_ANON_KEY)


async def _get_db(request: Request):
    """Retourne la factory de sessions DB depuis app.state."""
    db_session = getattr(request.app.state, "db_session_factory", None)
    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de données non disponible.",
        )
    return db_session


# ---- POST /households ----

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit écriture 30/min par user
@router.post(
    "",
    summary="Créer un foyer",
    description=(
        "Crée un nouveau foyer avec son premier membre (owner). "
        "Appelle la fonction SQL SECURITY DEFINER `create_household_with_owner`. "
        f"Rate limit : {LIMIT_USER_WRITE} (écriture)."
    ),
    response_model=HouseholdRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {"description": "Foyer existant retourné (idempotent)."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentification requise."},
        429: {"description": "Rate limit dépassé."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def create_household(
    request: Request,
    body: HouseholdCreate,
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Crée un foyer et son premier membre (owner).

    L'utilisateur Supabase authentifié devient automatiquement le owner.
    Un utilisateur ne peut appartenir qu'à un seul foyer (contrainte UNIQUE).

    Args:
        body: Données du foyer et du premier membre.
        request: Requête FastAPI.
        user: Payload JWT de l'utilisateur authentifié.

    Returns:
        HouseholdRead avec les membres créés.
    """
    db_session = await _get_db(request)

    async with db_session() as session:
        # FIX Phase 1 mature (review 2026-04-12) — BUG #7 : idempotence onboarding.
        # Au lieu de retourner 409, on retourne le foyer existant (200 idempotent).
        # Évite le blocage des retries après erreur partielle d'onboarding.
        existing = await session.execute(
            text(
                """
                SELECT hm.household_id
                FROM household_members hm
                WHERE hm.supabase_user_id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user.user_id},
        )
        existing_row = existing.fetchone()
        if existing_row:
            logger.info(
                "household_create_idempotent",
                household_id=str(existing_row[0]),
                user_id=user.user_id,
            )
            # Retourne 200 avec le foyer existant (idempotent — safe pour les retries)
            return await _get_household_by_id(db_session, existing_row[0])

        # FIX Phase 1 mature (review 2026-04-12) — BUG #2 : appel SECURITY DEFINER.
        # Remplace les 2-3 INSERTs directs par la fonction SQL SECURITY DEFINER
        # `create_household_with_owner` qui crée atomiquement foyer + owner
        # en bypassant RLS (role SECURITY DEFINER = postgres, contourne RLS).
        # Prérequis : la fonction existe dans 04-triggers-functions.sql (Phase 0).
        first_member = body.first_member
        household_result = await session.execute(
            text(
                "SELECT * FROM create_household_with_owner(:name, :user_id::uuid, :display_name)"
            ),
            {
                "name": body.name,
                "user_id": user.user_id,
                "display_name": first_member.display_name,
            },
        )
        # La fonction SQL retourne : household_id (UUID), member_id (UUID du owner)
        household_row = household_result.mappings().one()
        household_id = household_row["household_id"]
        member_id = household_row["member_id"]

        # Création des préférences initiales si fournies (après l'atomique DEFINER)
        if first_member.preferences:
            prefs = first_member.preferences
            await session.execute(
                text(
                    """
                    INSERT INTO member_preferences (
                        member_id, diet_tags, allergies, dislikes,
                        cooking_time_max, budget_pref
                    ) VALUES (
                        :member_id, :diet_tags::jsonb, :allergies::jsonb,
                        :dislikes::jsonb, :cooking_time_max, :budget_pref
                    )
                    """
                ),
                {
                    "member_id": str(member_id),
                    "diet_tags": json.dumps(prefs.diet_tags),
                    "allergies": json.dumps(prefs.allergies),
                    "dislikes": json.dumps(prefs.dislikes),
                    "cooking_time_max": prefs.cooking_time_max,
                    "budget_pref": prefs.budget_pref,
                },
            )

        await session.commit()

        logger.info(
            "household_created",
            household_id=str(household_id),
            user_id=user.user_id,
            member_id=str(member_id),
        )

    # Récupération du foyer complet pour la réponse
    return await _get_household_by_id(db_session, household_id)


# ---- GET /households/me ----

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit lecture 300/min par user
@router.get(
    "/me",
    summary="Mon foyer",
    description=(
        "Retourne le foyer et les membres de l'utilisateur authentifié. "
        f"Rate limit : {LIMIT_USER_READ} (lecture)."
    ),
    response_model=HouseholdRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "L'utilisateur n'appartient à aucun foyer."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentification requise."},
    },
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def get_my_household(
    request: Request,
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Récupère le foyer de l'utilisateur authentifié avec ses membres.

    Args:
        request: Requête FastAPI.
        user: Payload JWT.

    Returns:
        HouseholdRead avec tous les membres.
    """
    db_session = await _get_db(request)

    async with db_session() as session:
        result = await session.execute(
            text(
                """
                SELECT hm.household_id
                FROM household_members hm
                WHERE hm.supabase_user_id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user.user_id},
        )
        row = result.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vous n'appartenez à aucun foyer. Créez-en un via POST /api/v1/households.",
        )

    household_id = row[0]
    return await _get_household_by_id(db_session, household_id)


# ---- PATCH /households/me ----

@router.patch(
    "/me",
    summary="Mettre à jour mon foyer",
    description=(
        "Met à jour les informations du foyer de l'utilisateur authentifié. "
        "Seuls les champs fournis dans le body sont modifiés (partial update). "
        "Champs modifiables : `name`, `drive_provider`. "
        f"Rate limit : {LIMIT_USER_WRITE} (écriture)."
    ),
    response_model=HouseholdRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "L'utilisateur n'appartient à aucun foyer."},
        status.HTTP_403_FORBIDDEN: {"description": "Seul le owner peut modifier le foyer."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentification requise."},
        429: {"description": "Rate limit dépassé."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def update_my_household(
    request: Request,
    body: HouseholdUpdate,
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Met à jour partiellement le foyer de l'utilisateur authentifié.

    Seul le owner du foyer peut modifier les informations du foyer.
    La mise à jour est idempotente : appeler deux fois avec le même body
    produit le même résultat.

    Args:
        body: Champs à mettre à jour (tous optionnels).
        request: Requête FastAPI.
        user: Payload JWT.

    Returns:
        HouseholdRead avec les données mises à jour.
    """
    db_session = await _get_db(request)

    # Vérifie qu'au moins un champ est fourni (body non vide)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Au moins un champ doit être fourni pour la mise à jour.",
        )

    async with db_session() as session:
        # Récupérer le foyer + vérifier que l'utilisateur est owner
        role_result = await session.execute(
            text(
                """
                SELECT hm.role, hm.household_id
                FROM household_members hm
                WHERE hm.supabase_user_id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user.user_id},
        )
        owner_row = role_result.fetchone()

        if owner_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vous n'appartenez à aucun foyer.",
            )

        if owner_row[0] != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seul le owner du foyer peut modifier les informations du foyer.",
            )

        household_id = owner_row[1]

        # Construction dynamique des clauses SET — uniquement les champs fournis
        # Utilise des paramètres nommés pour éviter toute injection SQL
        set_clauses = []
        params: dict[str, Any] = {"household_id": str(household_id)}

        if "name" in updates:
            set_clauses.append("name = :name")
            params["name"] = updates["name"]

        if "drive_provider" in updates:
            set_clauses.append("drive_provider = :drive_provider")
            params["drive_provider"] = updates["drive_provider"]

        set_clauses.append("updated_at = NOW()")

        await session.execute(
            text(
                f"UPDATE households SET {', '.join(set_clauses)} WHERE id = :household_id"
            ),
            params,
        )
        await session.commit()

        logger.info(
            "household_updated",
            household_id=str(household_id),
            updated_fields=list(updates.keys()),
            by_user=user.user_id,
        )

    return await _get_household_by_id(db_session, household_id)


# ---- DELETE /households/me ----

@router.delete(
    "/me",
    summary="Supprimer mon foyer",
    description=(
        "Supprime définitivement le foyer de l'utilisateur authentifié et toutes ses données "
        "(membres, préférences, fridge_items, etc.) via CASCADE. "
        "Action irréversible — réservée au owner. "
        f"Rate limit : {LIMIT_USER_WRITE} (écriture)."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Foyer supprimé avec succès."},
        status.HTTP_404_NOT_FOUND: {"description": "L'utilisateur n'appartient à aucun foyer."},
        status.HTTP_403_FORBIDDEN: {"description": "Seul le owner peut supprimer le foyer."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentification requise."},
        429: {"description": "Rate limit dépassé."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def delete_my_household(
    request: Request,
    user: TokenPayload = Depends(get_current_user_dep),
) -> None:
    """
    Supprime définitivement le foyer et toutes ses données associées.

    La suppression est propagée via CASCADE au niveau base de données :
    household_members, member_preferences, fridge_items, meal_plans, etc.
    Cette opération est irréversible.

    Seul le owner du foyer peut déclencher cette action.

    Args:
        request: Requête FastAPI.
        user: Payload JWT.

    Returns:
        204 No Content si la suppression a réussi.
    """
    db_session = await _get_db(request)

    async with db_session() as session:
        # Vérifier que l'utilisateur est owner de son foyer
        role_result = await session.execute(
            text(
                """
                SELECT hm.role, hm.household_id
                FROM household_members hm
                WHERE hm.supabase_user_id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user.user_id},
        )
        owner_row = role_result.fetchone()

        if owner_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vous n'appartenez à aucun foyer.",
            )

        if owner_row[0] != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seul le owner du foyer peut le supprimer.",
            )

        household_id = owner_row[1]

        # Suppression hard delete — la CASCADE DB propage la suppression
        # sur : household_members, member_preferences, member_taste_vectors,
        # fridge_items, meal_plans, subscriptions, etc.
        await session.execute(
            text("DELETE FROM households WHERE id = :household_id"),
            {"household_id": str(household_id)},
        )
        await session.commit()

        logger.info(
            "household_deleted",
            household_id=str(household_id),
            by_user=user.user_id,
        )


# ---- POST /households/me/members ----

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit écriture 30/min par user
@router.post(
    "/me/members",
    summary="Ajouter un membre",
    description=(
        "Ajoute un nouveau membre au foyer de l'utilisateur authentifié. "
        "Réservé au owner du foyer. "
        f"Rate limit : {LIMIT_USER_WRITE} (écriture)."
    ),
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Seul le owner peut ajouter des membres."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentification requise."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def add_member(
    request: Request,
    body: MemberCreate,
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Ajoute un membre au foyer du owner authentifié.

    Args:
        body: Données du nouveau membre.
        request: Requête FastAPI.
        user: Payload JWT.

    Returns:
        MemberRead du membre créé.
    """
    db_session = await _get_db(request)

    async with db_session() as session:
        # Vérifier que l'utilisateur est owner de son foyer
        role_result = await session.execute(
            text(
                """
                SELECT hm.role, hm.household_id
                FROM household_members hm
                WHERE hm.supabase_user_id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user.user_id},
        )
        owner_row = role_result.fetchone()

        if owner_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vous n'appartenez à aucun foyer.",
            )

        if owner_row[0] != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seul le owner du foyer peut ajouter des membres.",
            )

        household_id = owner_row[1]

        # Insertion du nouveau membre
        birth_date_str = body.birth_date.isoformat() if body.birth_date else None
        member_result = await session.execute(
            text(
                """
                INSERT INTO household_members (
                    household_id, role, display_name, is_child, birth_date
                )
                VALUES (:household_id, 'member', :display_name, :is_child, :birth_date)
                RETURNING id, household_id, role, display_name, is_child, birth_date, created_at, updated_at
                """
            ),
            {
                "household_id": str(household_id),
                "display_name": body.display_name,
                "is_child": body.is_child,
                "birth_date": birth_date_str,
            },
        )
        member_row = member_result.mappings().one()
        member_id = member_row["id"]

        # Préférences si fournies
        if body.preferences:
            prefs = body.preferences
            await session.execute(
                text(
                    """
                    INSERT INTO member_preferences (
                        member_id, diet_tags, allergies, dislikes,
                        cooking_time_max, budget_pref
                    ) VALUES (
                        :member_id, :diet_tags::jsonb, :allergies::jsonb,
                        :dislikes::jsonb, :cooking_time_max, :budget_pref
                    )
                    """
                ),
                {
                    "member_id": str(member_id),
                    "diet_tags": json.dumps(prefs.diet_tags),
                    "allergies": json.dumps(prefs.allergies),
                    "dislikes": json.dumps(prefs.dislikes),
                    "cooking_time_max": prefs.cooking_time_max,
                    "budget_pref": prefs.budget_pref,
                },
            )

        await session.commit()

        logger.info(
            "household_member_added",
            household_id=str(household_id),
            member_id=str(member_id),
            by_user=user.user_id,
        )

    # Récupération du membre complet
    async with db_session() as session:
        return await _get_member_by_id(session, member_id)


# ---- PATCH /households/me/members/{member_id}/preferences ----

# FIX Phase 1 mature (review 2026-04-12) — BUG #1 : rate limit écriture 30/min par user
@router.patch(
    "/me/members/{member_id}/preferences",
    summary="Mettre à jour les préférences d'un membre",
    description=(
        "Met à jour les préférences alimentaires d'un membre du foyer. "
        "Accessible par le owner ou le membre lui-même (si supabase_user_id correspond). "
        f"Rate limit : {LIMIT_USER_WRITE} (écriture)."
    ),
    response_model=MemberPreferenceRead,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Non autorisé."},
        status.HTTP_404_NOT_FOUND: {"description": "Membre introuvable."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def update_member_preferences(
    request: Request,
    member_id: UUID,
    body: MemberPreferenceCreate,
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Met à jour les préférences alimentaires d'un membre.

    Args:
        member_id: UUID du membre à modifier.
        body: Nouvelles préférences.
        request: Requête FastAPI.
        user: Payload JWT.

    Returns:
        MemberPreferenceRead avec les préférences mises à jour.
    """
    db_session = await _get_db(request)

    async with db_session() as session:
        # Vérifier les droits d'accès
        access_result = await session.execute(
            text(
                """
                SELECT hm_target.id, hm_caller.role
                FROM household_members hm_target
                JOIN household_members hm_caller ON hm_caller.household_id = hm_target.household_id
                WHERE hm_target.id = :member_id
                  AND hm_caller.supabase_user_id = :user_id
                LIMIT 1
                """
            ),
            {"member_id": str(member_id), "user_id": user.user_id},
        )
        access_row = access_result.fetchone()

        if access_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Membre {member_id} introuvable dans votre foyer.",
            )

        # UPSERT des préférences
        pref_result = await session.execute(
            text(
                """
                INSERT INTO member_preferences (
                    member_id, diet_tags, allergies, dislikes,
                    cooking_time_max, budget_pref
                ) VALUES (
                    :member_id, :diet_tags::jsonb, :allergies::jsonb,
                    :dislikes::jsonb, :cooking_time_max, :budget_pref
                )
                ON CONFLICT (member_id) DO UPDATE SET
                    diet_tags = EXCLUDED.diet_tags,
                    allergies = EXCLUDED.allergies,
                    dislikes = EXCLUDED.dislikes,
                    cooking_time_max = EXCLUDED.cooking_time_max,
                    budget_pref = EXCLUDED.budget_pref,
                    updated_at = NOW()
                RETURNING id, member_id, diet_tags, allergies, dislikes,
                          cooking_time_max, budget_pref, created_at, updated_at
                """
            ),
            {
                "member_id": str(member_id),
                "diet_tags": json.dumps(body.diet_tags),
                "allergies": json.dumps(body.allergies),
                "dislikes": json.dumps(body.dislikes),
                "cooking_time_max": body.cooking_time_max,
                "budget_pref": body.budget_pref,
            },
        )
        pref_row = pref_result.mappings().one()
        await session.commit()

        logger.info(
            "member_preferences_updated",
            member_id=str(member_id),
            by_user=user.user_id,
        )

        return MemberPreferenceRead.model_validate(dict(pref_row))


# ---- Helpers privés ----

async def _get_household_by_id(db_session: Any, household_id: Any) -> HouseholdRead:
    """Récupère un foyer complet avec ses membres, préférences, drive_provider et owner_id."""
    async with db_session() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    h.id, h.name, h.plan, h.drive_provider, h.created_at, h.updated_at,
                    hm.id AS member_id, hm.role, hm.display_name,
                    hm.is_child, hm.birth_date, hm.supabase_user_id,
                    hm.created_at AS member_created_at,
                    hm.updated_at AS member_updated_at,
                    mp.id AS pref_id, mp.diet_tags, mp.allergies,
                    mp.dislikes, mp.cooking_time_max, mp.budget_pref,
                    mp.created_at AS pref_created_at, mp.updated_at AS pref_updated_at
                FROM households h
                LEFT JOIN household_members hm ON hm.household_id = h.id
                LEFT JOIN member_preferences mp ON mp.member_id = hm.id
                WHERE h.id = :household_id
                ORDER BY hm.created_at ASC
                """
            ),
            {"household_id": str(household_id)},
        )
        rows = result.mappings().all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Foyer {household_id} introuvable.",
        )

    # Construction de la réponse (dénormalisation des jointures)
    household_data = dict(rows[0])
    members = []
    owner_id = None

    for row in rows:
        if row.get("member_id") is None:
            continue
        # Le owner_id correspond au supabase_user_id du membre ayant le rôle 'owner'
        if row.get("role") == "owner" and row.get("supabase_user_id"):
            owner_id = row["supabase_user_id"]
        prefs = None
        if row.get("pref_id"):
            prefs = MemberPreferenceRead(
                id=row["pref_id"],
                member_id=row["member_id"],
                diet_tags=row["diet_tags"] or [],
                allergies=row["allergies"] or [],
                dislikes=row["dislikes"] or [],
                cooking_time_max=row.get("cooking_time_max"),
                budget_pref=row.get("budget_pref"),
                created_at=row["pref_created_at"],
                updated_at=row["pref_updated_at"],
            )
        members.append(
            MemberRead(
                id=row["member_id"],
                household_id=household_data["id"],
                display_name=row["display_name"],
                is_child=row["is_child"] or False,
                role=row["role"],
                birth_date=row.get("birth_date"),
                created_at=row["member_created_at"],
                preferences=prefs,
            )
        )

    return HouseholdRead(
        id=household_data["id"],
        name=household_data["name"],
        plan=household_data["plan"],
        drive_provider=household_data.get("drive_provider"),
        owner_id=owner_id,
        created_at=household_data["created_at"],
        updated_at=household_data["updated_at"],
        members=members,
    )


async def _get_member_by_id(session: Any, member_id: Any) -> MemberRead:
    """Récupère un membre avec ses préférences."""
    result = await session.execute(
        text(
            """
            SELECT
                hm.id, hm.household_id, hm.role, hm.display_name,
                hm.is_child, hm.birth_date, hm.created_at, hm.updated_at,
                mp.id AS pref_id, mp.diet_tags, mp.allergies, mp.dislikes,
                mp.cooking_time_max, mp.budget_pref,
                mp.created_at AS pref_created_at, mp.updated_at AS pref_updated_at
            FROM household_members hm
            LEFT JOIN member_preferences mp ON mp.member_id = hm.id
            WHERE hm.id = :member_id
            """
        ),
        {"member_id": str(member_id)},
    )
    row = result.mappings().one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Membre {member_id} introuvable.",
        )

    prefs = None
    if row.get("pref_id"):
        prefs = MemberPreferenceRead(
            id=row["pref_id"],
            member_id=row["id"],
            diet_tags=row["diet_tags"] or [],
            allergies=row["allergies"] or [],
            dislikes=row["dislikes"] or [],
            cooking_time_max=row.get("cooking_time_max"),
            budget_pref=row.get("budget_pref"),
            created_at=row["pref_created_at"],
            updated_at=row["pref_updated_at"],
        )

    return MemberRead(
        id=row["id"],
        household_id=row["household_id"],
        display_name=row["display_name"],
        is_child=row["is_child"] or False,
        role=row["role"],
        birth_date=row.get("birth_date"),
        created_at=row["created_at"],
        preferences=prefs,
    )
