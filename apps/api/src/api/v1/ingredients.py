"""
Endpoint de recherche d'ingrédients dans le catalogue.

Endpoints :
  GET /api/v1/ingredients/search?q=tomat&limit=10 → liste d'ingrédients correspondants

Sécurité :
- Requiert une authentification JWT (cohérence avec fridge.py).
- Catalogue partagé : pas d'isolation tenant (les ingrédients sont globaux).
- Rate limit niveau 2 lecture : 300 req/min par utilisateur.

Recherche :
- pg_trgm activé : index GIN sur canonical_name.
- Stratégie hybride : ILIKE (sous-chaîne) OR similarity > 0.2 (fautes de frappe).
- Tri par pertinence similarité décroissante.
- Supporte noms français (seed) et anglais (TheMealDB).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.rate_limit import LIMIT_USER_READ, get_user_key, limiter
from src.core.security import TokenPayload, get_current_user

router = APIRouter(prefix="/ingredients", tags=["ingredients"])
settings = get_settings()

# ---- Helpers ----

_MIN_QUERY_LENGTH = 2
_MAX_LIMIT = 50


def get_current_user_dep(request: Request) -> TokenPayload:
    """Dépendance JWT — identique au pattern de fridge.py."""
    return get_current_user(request, settings.SUPABASE_ANON_KEY)


async def get_db(request: Request) -> AsyncSession:
    """Session DB depuis app.state — identique au pattern de fridge.py."""
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        raise HTTPException(status_code=503, detail="Base de données non disponible.")
    async with factory() as session:
        yield session


# ---- Schémas ----


class IngredientSearchResult(BaseModel):
    """Représentation publique d'un ingrédient retourné par la recherche."""

    id: UUID
    name: str
    category: str | None
    unit_default: str | None

    model_config = {"from_attributes": True}


# ---- Endpoint ----


@router.get(
    "/search",
    summary="Rechercher des ingrédients dans le catalogue",
    description=(
        "Recherche floue sur le catalogue d'ingrédients en utilisant pg_trgm. "
        "Supporte les noms en français et en anglais. "
        "Stratégie : sous-chaîne (ILIKE) OU similarité > 0.2 pour tolérer les fautes. "
        "Résultats triés par score de similarité décroissant. "
        f"Longueur minimale de requête : {_MIN_QUERY_LENGTH} caractères. "
        f"Rate limit : {LIMIT_USER_READ}."
    ),
    response_model=list[IngredientSearchResult],
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Requête trop courte (< 2 caractères)."},
        503: {"description": "Base de données non disponible."},
    },
)
@limiter.limit(LIMIT_USER_READ, key_func=get_user_key)
async def search_ingredients(
    request: Request,
    q: str = Query(
        ...,
        min_length=_MIN_QUERY_LENGTH,
        max_length=200,
        description="Terme de recherche (ex: 'tomat', 'poulet', 'tomato').",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=_MAX_LIMIT,
        description="Nombre maximum de résultats retournés.",
    ),
    session: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Recherche des ingrédients dans le catalogue par correspondance floue.

    Utilise pg_trgm pour la similarité — requiert l'extension activée en base.
    La requête est validée côté Pydantic (min_length=2) ; la validation Query
    de FastAPI retourne automatiquement HTTP 422 si la contrainte n'est pas
    respectée, mais on garde une garde explicite pour les cas de contournement.

    Args:
        request: Requête FastAPI (requis par slowapi).
        q: Terme de recherche saisi par l'utilisateur.
        limit: Nombre de résultats souhaités.
        session: Session DB asynchrone.
        _user: Payload JWT (auth obligatoire, non utilisé dans la requête).

    Returns:
        Liste d'IngredientSearchResult triée par pertinence.
    """
    # Garde défensive au cas où min_length serait contourné
    if len(q.strip()) < _MIN_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La recherche doit contenir au moins {_MIN_QUERY_LENGTH} caractères.",
        )

    clean_q = q.strip()

    result = await session.execute(
        text(
            """
            SELECT id, canonical_name, category, unit_default
            FROM ingredients
            WHERE canonical_name ILIKE '%' || :q || '%'
               OR similarity(canonical_name, :q) > 0.2
            ORDER BY similarity(canonical_name, :q) DESC
            LIMIT :limit
            """
        ),
        {"q": clean_q, "limit": limit},
    )
    rows = result.mappings().all()

    items = [
        IngredientSearchResult(
            id=row["id"],
            name=row["canonical_name"],
            category=row["category"],
            unit_default=row["unit_default"],
        )
        for row in rows
    ]

    logger.debug(
        "ingredient_search",
        query=clean_q,
        result_count=len(items),
        limit=limit,
    )

    return items
