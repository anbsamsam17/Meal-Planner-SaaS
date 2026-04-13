"""
Endpoints du mode frigo — gestion du stock d'ingrédients du foyer.

Endpoints :
  GET    /api/v1/fridge                → liste les items du frigo du foyer
  POST   /api/v1/fridge                → ajouter un item
  DELETE /api/v1/fridge/{item_id}      → retirer un item (consommé)
  POST   /api/v1/fridge/suggest-recipes → 5 recettes utilisant les ingrédients en stock

Sécurité :
- Tous les endpoints requièrent une authentification JWT.
- Isolation tenant : les items sont filtrés par household_id.
- RLS Postgres garantit l'isolation côté DB (colonne household_id).

Logique "utiliser les restes" :
La suggestion priorise :
  1. Les recettes qui matchent ≥2 ingrédients du frigo
  2. Les items proches de la date d'expiration (score de fraîcheur)
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.rate_limit import LIMIT_USER_READ, LIMIT_USER_WRITE, get_user_key, limiter
from src.core.security import TokenPayload, get_current_user

router = APIRouter(prefix="/fridge", tags=["fridge"])
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


async def _get_household_id(session: AsyncSession, user_id: str) -> str:
    """Récupère le household_id de l'utilisateur."""
    result = await session.execute(
        text(
            "SELECT household_id FROM household_members "
            "WHERE supabase_user_id = :uid LIMIT 1"
        ),
        {"uid": user_id},
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vous n'appartenez à aucun foyer.",
        )
    return str(row[0])


# ---- Schémas ----


class FridgeItemCreate(BaseModel):
    """Corps pour ajouter un item au frigo."""

    ingredient_id: UUID = Field(description="UUID de l'ingrédient en base.")
    quantity: float | None = Field(default=None, ge=0, description="Quantité.")
    unit: str | None = Field(default=None, max_length=50, description="Unité (ex: g, ml, pièce).")
    expiry_date: date | None = Field(
        default=None, description="Date d'expiration (YYYY-MM-DD). Optionnel."
    )


class FridgeItemRead(BaseModel):
    """Représentation publique d'un item du frigo."""

    id: UUID
    household_id: UUID
    ingredient_id: UUID
    canonical_name: str
    quantity: float | None
    unit: str | None
    expiry_date: date | None
    added_at: str | None
    days_until_expiry: int | None = None

    model_config = {"from_attributes": True}


class RecipeSuggestion(BaseModel):
    """Suggestion de recette basée sur le contenu du frigo."""

    recipe_id: UUID
    title: str
    total_time_min: int | None
    difficulty: int | None
    matching_ingredients: list[str]
    match_count: int
    has_expiring_items: bool


# ---- Endpoints ----


@router.get(
    "",
    summary="Contenu du frigo",
    description=(
        "Liste les ingrédients actuellement dans le frigo du foyer. "
        "Triés par date d'expiration (les plus proches en premier). "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=list[FridgeItemRead],
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def list_fridge_items(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Liste les items du frigo triés par urgence (expiry_date ASC NULLS LAST).

    Calcule les jours restants avant expiration pour chaque item.
    """
    household_id = await _get_household_id(session, user.user_id)

    result = await session.execute(
        text(
            """
            SELECT
                fi.id,
                fi.household_id,
                fi.ingredient_id,
                i.canonical_name,
                fi.quantity,
                fi.unit,
                fi.expiry_date,
                fi.added_at::text,
                CASE
                    WHEN fi.expiry_date IS NOT NULL
                    THEN (fi.expiry_date - CURRENT_DATE)
                    ELSE NULL
                END AS days_until_expiry
            FROM fridge_items fi
            JOIN ingredients i ON i.id = fi.ingredient_id
            WHERE fi.household_id = :hid
            ORDER BY fi.expiry_date ASC NULLS LAST, fi.added_at DESC
            """
        ),
        {"hid": household_id},
    )
    rows = result.mappings().all()

    items = [FridgeItemRead.model_validate(dict(row)) for row in rows]

    logger.debug(
        "fridge_list",
        household_id=household_id,
        item_count=len(items),
    )

    return items


@router.post(
    "",
    summary="Ajouter un item au frigo",
    description=(
        "Ajoute un ingrédient au stock du frigo du foyer. "
        "L'ingredient_id doit exister dans le catalogue. "
        f"Rate limit : {LIMIT_USER_WRITE}."
    ),
    response_model=FridgeItemRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Ingrédient introuvable dans le catalogue."},
        409: {"description": "Ingrédient déjà présent dans le frigo."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def add_fridge_item(
    request: Request,
    body: FridgeItemCreate,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Ajoute un ingrédient dans le frigo du foyer.

    Vérifie que l'ingredient_id existe dans le catalogue.
    Retourne 409 si l'ingrédient est déjà présent (même ingredient_id + household_id).

    Args:
        request: Requête FastAPI.
        body: Données de l'item à ajouter.
        session: Session DB.
        user: Payload JWT.
    """
    household_id = await _get_household_id(session, user.user_id)

    # Vérifie que l'ingrédient existe
    ing_result = await session.execute(
        text("SELECT id, canonical_name FROM ingredients WHERE id = :ing_id"),
        {"ing_id": str(body.ingredient_id)},
    )
    ing_row = ing_result.mappings().one_or_none()
    if ing_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingrédient {body.ingredient_id} introuvable dans le catalogue.",
        )

    # Insert (pas d'upsert — on permet plusieurs quantités du même ingrédient)
    insert_result = await session.execute(
        text(
            """
            INSERT INTO fridge_items
                (household_id, ingredient_id, quantity, unit, expiry_date)
            VALUES
                (:hid, :ing_id, :qty, :unit, :expiry)
            RETURNING id, household_id, ingredient_id, quantity, unit, expiry_date, added_at::text
            """
        ),
        {
            "hid": household_id,
            "ing_id": str(body.ingredient_id),
            "qty": body.quantity,
            "unit": body.unit,
            "expiry": body.expiry_date.isoformat() if body.expiry_date else None,
        },
    )
    row = insert_result.mappings().one()
    await session.commit()

    logger.info(
        "fridge_item_added",
        household_id=household_id,
        ingredient_id=str(body.ingredient_id),
        ingredient_name=ing_row["canonical_name"],
        expiry_date=str(body.expiry_date) if body.expiry_date else None,
    )

    item_dict = dict(row)
    item_dict["canonical_name"] = ing_row["canonical_name"]
    item_dict["days_until_expiry"] = None

    if body.expiry_date:
        item_dict["days_until_expiry"] = (body.expiry_date - date.today()).days

    return FridgeItemRead.model_validate(item_dict)


@router.delete(
    "/{item_id}",
    summary="Retirer un item du frigo",
    description=(
        "Supprime un item du frigo (ingrédient consommé ou périmé). "
        f"Rate limit : {LIMIT_USER_WRITE}."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Item introuvable ou n'appartient pas à votre foyer."},
    },
)
@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)
async def remove_fridge_item(
    request: Request,
    item_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> None:
    """
    Supprime un item du frigo (action "consommé" ou "jeté").

    Vérifie l'appartenance au household_id avant suppression (isolation tenant).

    Args:
        request: Requête FastAPI.
        item_id: UUID de l'item à supprimer.
        session: Session DB.
        user: Payload JWT.
    """
    household_id = await _get_household_id(session, user.user_id)

    result = await session.execute(
        text(
            """
            DELETE FROM fridge_items
            WHERE id = :item_id AND household_id = :hid
            RETURNING id
            """
        ),
        {"item_id": str(item_id), "hid": household_id},
    )
    deleted = result.fetchone()
    await session.commit()

    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} introuvable dans votre frigo.",
        )

    logger.info(
        "fridge_item_removed",
        household_id=household_id,
        item_id=str(item_id),
    )


@router.post(
    "/suggest-recipes",
    summary="Suggérer des recettes basées sur le frigo",
    description=(
        "Retourne jusqu'à 5 recettes qui utilisent les ingrédients actuellement dans le frigo. "
        "Priorise les recettes avec le plus de correspondances et les items proches de l'expiration. "
        "Requête SQL : jointure fridge_items × recipe_ingredients, "
        "COUNT des correspondances + boost score expiration. "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=list[RecipeSuggestion],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Liste vide si le frigo est vide."},
    },
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def suggest_recipes_from_fridge(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Suggère des recettes basées sur les ingrédients disponibles dans le frigo.

    Logique SQL :
    1. Récupère les ingredient_id du frigo du foyer
    2. Joint avec recipe_ingredients pour compter les correspondances
    3. Boost les recettes ayant des items proches de l'expiration
    4. Filtre : ≥ 1 correspondance, qualité >= 0.5
    5. Ordonne par (has_expiring + match_count) DESC

    Note : le seuil de ≥2 correspondances idéal est assoupli à ≥1 pour les
    foyers avec peu d'items dans le frigo.

    Args:
        request: Requête FastAPI.
        session: Session DB.
        user: Payload JWT.

    Returns:
        Liste de RecipeSuggestion, max 5 résultats.
    """
    household_id = await _get_household_id(session, user.user_id)

    # Récupère les IDs et noms des ingrédients du frigo
    fridge_result = await session.execute(
        text(
            """
            SELECT
                fi.ingredient_id::text,
                i.canonical_name,
                fi.expiry_date,
                CASE
                    WHEN fi.expiry_date IS NOT NULL AND fi.expiry_date <= CURRENT_DATE + INTERVAL '3 days'
                    THEN true ELSE false
                END AS expires_soon
            FROM fridge_items fi
            JOIN ingredients i ON i.id = fi.ingredient_id
            WHERE fi.household_id = :hid
            """
        ),
        {"hid": household_id},
    )
    fridge_rows = fridge_result.mappings().all()

    if not fridge_rows:
        logger.debug("fridge_suggest_empty_fridge", household_id=household_id)
        return []

    fridge_ingredient_ids = [row["ingredient_id"] for row in fridge_rows]
    expiring_ids = {row["ingredient_id"] for row in fridge_rows if row["expires_soon"]}
    name_by_id = {row["ingredient_id"]: row["canonical_name"] for row in fridge_rows}

    # Requête principale :
    # - joint recipe_ingredients avec les ingrédients du frigo
    # - compte les correspondances par recette
    # - booste si des items expirent bientôt
    suggestions_result = await session.execute(
        text(
            """
            SELECT
                r.id::text AS recipe_id,
                r.title,
                r.total_time_min,
                r.difficulty,
                COUNT(ri.ingredient_id) AS match_count,
                ARRAY_AGG(ri.ingredient_id::text) AS matched_ingredient_ids,
                BOOL_OR(
                    ri.ingredient_id::text = ANY(:expiring_ids)
                ) AS has_expiring_items
            FROM recipes r
            JOIN recipe_ingredients ri ON ri.recipe_id = r.id
            WHERE ri.ingredient_id::text = ANY(:fridge_ids)
              AND r.quality_score >= 0.5
            GROUP BY r.id, r.title, r.total_time_min, r.difficulty
            HAVING COUNT(ri.ingredient_id) >= 1
            ORDER BY
                BOOL_OR(ri.ingredient_id::text = ANY(:expiring_ids)) DESC,
                COUNT(ri.ingredient_id) DESC,
                r.quality_score DESC
            LIMIT 5
            """
        ),
        {
            "fridge_ids": fridge_ingredient_ids,
            "expiring_ids": list(expiring_ids) if expiring_ids else [""],
        },
    )
    suggestion_rows = suggestions_result.mappings().all()

    suggestions = []
    for row in suggestion_rows:
        matched_ids = row["matched_ingredient_ids"] or []
        matching_names = [name_by_id.get(ing_id, ing_id) for ing_id in matched_ids if ing_id in name_by_id]

        suggestions.append(
            RecipeSuggestion(
                recipe_id=UUID(row["recipe_id"]),
                title=row["title"],
                total_time_min=row["total_time_min"],
                difficulty=row["difficulty"],
                matching_ingredients=matching_names,
                match_count=int(row["match_count"]),
                has_expiring_items=bool(row["has_expiring_items"]),
            )
        )

    logger.info(
        "fridge_suggest_done",
        household_id=household_id,
        fridge_item_count=len(fridge_rows),
        suggestions_count=len(suggestions),
        expiring_count=len(expiring_ids),
    )

    return suggestions
