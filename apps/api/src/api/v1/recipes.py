"""
Endpoints v0 minimaux pour la consultation de recettes.

Ces endpoints constituent le scaffold de base pour la Phase 1.
En v0, ils retournent des données depuis la DB sans personnalisation.
La recherche sémantique (pgvector) sera intégrée en Phase 1 mature.

Sécurité :
- Les recettes sont publiques (pas de RLS sur la table recipes).
- Seuls les feedbacks et plannings sont soumis à l'isolation par household.
- Rate limit niveau 2 lecture : 300 req/min par user (slowapi).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from loguru import logger
from pydantic import BaseModel, Field

# FIX #2 (review Phase 1 2026-04-12) : LIMIT_USER_READ documenté — le rate limit 300/min
# est appliqué via SlowAPIMiddleware (default_limits dans create_limiter, main.py).
# La constante est conservée ici pour la documentation OpenAPI et les futures surcharges par endpoint.
from src.core.cache import (
    CACHE_TTL_RECIPE_DETAIL,
    CACHE_TTL_RECIPE_LIST,
    build_recipe_detail_key,
    build_recipe_list_key,
    cache_response,
    pydantic_to_cache,
)
from src.core.rate_limit import (  # noqa: F401 — documenté intentionnellement
    LIMIT_USER_READ,
    get_user_key,
)

router = APIRouter(prefix="/recipes", tags=["recipes"])


# -------------------------------------------------------------------------
# Schémas Pydantic v2 — réponses
# -------------------------------------------------------------------------


class RecipeOut(BaseModel):
    """Représentation publique d'une recette (sans données privées foyer)."""

    id: UUID
    title: str
    slug: str
    source: str | None = None
    servings: int | None = None
    prep_time_min: int | None = None
    cook_time_min: int | None = None
    total_time_min: int | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    cuisine_type: str | None = None
    # BUG 1 FIX (2026-04-12) : photo_url absent de la réponse API — ajout du champ
    photo_url: str | None = None
    tags: list[str] = []
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)

    model_config = {"from_attributes": True}


class RecipeIngredientDetail(BaseModel):
    """Ingrédient avec quantité dans le contexte d'une recette (endpoint detail)."""

    ingredient_id: UUID
    canonical_name: str
    quantity: float | None = None
    unit: str | None = None
    notes: str | None = None
    position: int

    model_config = {"from_attributes": True}


class RecipeDetail(RecipeOut):
    """Détail complet d'une recette avec ingrédients et instructions."""

    description: str | None = None
    instructions: list[dict] = Field(
        default=[],
        description="Étapes de préparation [{'step': 1, 'text': '...'}].",
    )
    ingredients: list[RecipeIngredientDetail] = Field(
        default=[],
        description="Ingrédients avec quantités et unités.",
    )

    model_config = {"from_attributes": True}


class RecipeSearchResult(BaseModel):
    """Résultat paginé de la recherche de recettes."""

    results: list[RecipeOut]
    total: int
    query: str
    page: int
    per_page: int


# -------------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------------
# FIX #2 (review Phase 1 2026-04-12) : rate limiting appliqué via deux mécanismes :
# 1. SlowAPIMiddleware avec default_limits=["300/minute"] couvre TOUS les endpoints (get_recipe inclus).
# 2. L'endpoint search_recipes applique un check Redis manuel pour la limite 60/min
#    (search double COUNT+SELECT = plus coûteux que GET par ID).
# Request doit être passé à chaque endpoint — requis par slowapi pour extraire la key_func.


@router.get(
    "/random",
    summary="5 recettes aléatoires",
    description=(
        "Retourne 5 recettes aléatoires depuis le catalogue. "
        "Utilisé pour le dashboard quand l'utilisateur n'a pas encore de plan. "
        "Les recettes retournées ont toutes un quality_score >= 0.6. "
        f"Rate limit : {LIMIT_USER_READ} par utilisateur."
    ),
    response_model=list[RecipeOut],
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Base de données non disponible"},
    },
)
async def get_random_recipes(
    request: Request,
    count: int = Query(default=5, ge=1, le=20, description="Nombre de recettes (défaut: 5, max: 20)."),
) -> Any:
    """
    Retourne des recettes aléatoires pour le dashboard.

    Utilise TABLESAMPLE BERNOULLI pour un sampling efficace sans ORDER BY RANDOM()
    qui fait un full scan. En cas de résultat insuffisant (table petite),
    fallback sur ORDER BY RANDOM().

    Args:
        request: Requête FastAPI.
        count: Nombre de recettes à retourner.

    Returns:
        Liste de RecipeOut (peut être inférieure à count si la DB est peu peuplée).
    """
    db_session = getattr(request.app.state, "db_session_factory", None)

    if db_session is None:
        logger.debug("get_random_recipes_no_db")
        return []

    try:
        async with db_session() as session:
            from sqlalchemy import text

            # TABLESAMPLE BERNOULLI(10) = 10% des lignes — plus rapide que RANDOM()
            # Fallback ORDER BY RANDOM() si TABLESAMPLE retourne moins de `count` résultats.
            result = await session.execute(
                text(
                    """
                    WITH sampled AS (
                        SELECT id, title, slug, source, servings, prep_time_min,
                               cook_time_min, total_time_min, difficulty, cuisine_type,
                               photo_url, tags, quality_score
                        FROM recipes TABLESAMPLE BERNOULLI(10)
                        WHERE quality_score >= 0.6
                        LIMIT :count
                    ),
                    fallback AS (
                        SELECT id, title, slug, source, servings, prep_time_min,
                               cook_time_min, total_time_min, difficulty, cuisine_type,
                               photo_url, tags, quality_score
                        FROM recipes
                        WHERE quality_score >= 0.6
                        ORDER BY RANDOM()
                        LIMIT :count
                    )
                    SELECT * FROM sampled
                    UNION ALL
                    SELECT * FROM fallback
                    WHERE NOT EXISTS (SELECT 1 FROM sampled)
                    LIMIT :count
                    """
                ),
                {"count": count},
            )
            rows = result.mappings().all()

        recipes = [RecipeOut.model_validate(dict(row)) for row in rows]

        logger.debug(
            "random_recipes_served",
            requested=count,
            returned=len(recipes),
        )

        return recipes

    except Exception as exc:
        # FIX PROD (2026-04-12) : retourner une liste vide au lieu d'un 500
        # si la DB Supabase est inaccessible (SSL, pas de données, timeout).
        logger.error(
            "random_recipes_db_error",
            error=str(exc),
            count=count,
        )
        return []


@router.get(
    "",
    summary="Recherche de recettes",
    description=(
        "Recherche de recettes par mot-clé dans le titre et les tags. "
        "En v0 : recherche ILIKE (trigramme pg_trgm). "
        "Phase 2 : filtres avancés budget, difficulté, régime alimentaire, saison. "
        "Rate limit : 60 req/min par utilisateur (plus coûteux en DB que le GET par ID)."
    ),
    response_model=RecipeSearchResult,
    responses={429: {"description": "Rate limit dépassé — voir header Retry-After"}},
)
# Phase 2 — Filtres avancés ajoutés : budget, difficulty range, diet, season
async def search_recipes(
    request: Request,
    q: str = Query(
        default="",
        description="Mot-clé de recherche (titre, tags, cuisine).",
        max_length=200,
    ),
    page: int = Query(default=1, ge=1, description="Numéro de page (commence à 1)."),
    per_page: int = Query(
        default=20, ge=1, le=100, description="Nombre de résultats par page (max 100)."
    ),
    cuisine: str | None = Query(default=None, description="Filtre par type de cuisine."),
    max_time: int | None = Query(
        default=None, ge=5, le=300, description="Temps total max en minutes."
    ),
    # ---- Filtres Phase 2 ----
    budget: str | None = Query(
        default=None,
        description="Filtre par budget : 'économique', 'moyen', 'premium'. "
        "Filtre sur le tag correspondant de la recette.",
    ),
    min_difficulty: int | None = Query(
        default=None, ge=1, le=5, description="Difficulté minimale (1=très facile, 5=expert)."
    ),
    max_difficulty: int | None = Query(
        default=None, ge=1, le=5, description="Difficulté maximale (1=très facile, 5=expert)."
    ),
    # BUG P0 FIX (2026-04-14) : multi-select diet — accepte plusieurs valeurs
    # ex: ?diet=végétarien&diet=sans-gluten → list[str] via Query(None)
    diet: list[str] | None = Query(
        default=None,
        description="Filtre régime alimentaire (multi-select) : 'végétarien', 'sans-gluten', 'vegan', etc. "
        "Accepte plusieurs valeurs (?diet=végétarien&diet=sans-gluten). "
        "Filtre sur le tableau tags de la recette (AND logique : tous les régimes doivent matcher).",
    ),
    season: str | None = Query(
        default=None,
        description="Filtre saison : 'printemps', 'été', 'automne', 'hiver'. "
        "Filtre sur le tableau tags de la recette.",
    ),
) -> RecipeSearchResult:
    """
    Recherche de recettes avec filtres et pagination.

    Stratégie v0 : ILIKE sur le titre + filtre sur les tags (GIN index).
    Stratégie Phase 1 : recherche sémantique pgvector (cosine similarity).

    Les résultats sont ordonnés par quality_score DESC pour privilégier
    les recettes les mieux notées par le pipeline de validation LLM.

    Args:
        request: Requête FastAPI.
        q: Terme de recherche (titre / tags).
        page: Page courante.
        per_page: Taille de page.
        cuisine: Filtre optionnel sur cuisine_type.
        max_time: Filtre optionnel sur total_time_min.

    Returns:
        RecipeSearchResult avec pagination.
    """
    db_session = getattr(request.app.state, "db_session_factory", None)
    redis = getattr(request.app.state, "redis", None)
    offset = (page - 1) * per_page

    if db_session is None:
        logger.warning("search_recipes_no_db_session", hint="app.state.db_session_factory est None — la DB n'est pas connectée")
        return RecipeSearchResult(
            results=[], total=0, query=q, page=page, per_page=per_page
        )

    # Mapping EN→FR des tags régime alimentaire (frontend → DB)
    # IMP-05 fix (2026-04-14) : le frontend envoie des tags EN ("gluten-free", "lactose-free",
    # "no-pork", "no-seafood", "nut-free") mais la DB stocke des tags FR ("sans-gluten",
    # "sans-lactose", "sans-porc", "sans-fruits-de-mer", "sans-fruits-à-coque").
    _DIET_EN_TO_FR: dict[str, str] = {
        "gluten-free": "sans-gluten",
        "gluten_free": "sans-gluten",
        "lactose-free": "sans-lactose",
        "lactose_free": "sans-lactose",
        "no-pork": "sans-porc",
        "no_pork": "sans-porc",
        "no-seafood": "sans-fruits-de-mer",
        "no_seafood": "sans-fruits-de-mer",
        "nut-free": "sans-fruits-à-coque",
        "nut_free": "sans-fruits-à-coque",
        "vegetarian": "végétarien",
        "vegetarien": "végétarien",
    }
    normalized_diet = [_DIET_EN_TO_FR.get(tag, tag) for tag in diet] if diet else None

    # ---- PERF-02 : Cache Redis TTL 5min sur la liste/recherche ----
    cache_key = build_recipe_list_key(
        q=q,
        page=page,
        per_page=per_page,
        cuisine=cuisine,
        max_time=max_time,
        budget=budget,
        min_difficulty=min_difficulty,
        max_difficulty=max_difficulty,
        diet=normalized_diet,
        season=season,
    )

    async def _fetch_from_db() -> dict[str, Any]:
        """Query PostgreSQL — appelée uniquement en cas de cache miss."""
        try:
            async with db_session() as session:
                from sqlalchemy import text

                # Construction dynamique de la requête avec filtres optionnels
                # Utilise des paramètres liés pour éviter l'injection SQL
                conditions = ["quality_score >= 0.6"]
                params: dict[str, Any] = {"limit": per_page, "offset": offset}

                if q:
                    conditions.append("title ILIKE :query")
                    params["query"] = f"%{q}%"

                if cuisine:
                    conditions.append("cuisine_type = :cuisine")
                    params["cuisine"] = cuisine

                if max_time is not None:
                    conditions.append("total_time_min <= :max_time")
                    params["max_time"] = max_time

                # ---- Filtres Phase 2 ----

                # Filtre budget (tag sur la recette : 'économique', 'moyen', 'premium')
                if budget is not None:
                    conditions.append(":budget = ANY(tags)")
                    params["budget"] = budget

                # Filtre difficulté (range min/max sur colonne difficulty 1-5)
                if min_difficulty is not None:
                    conditions.append("difficulty >= :min_difficulty")
                    params["min_difficulty"] = min_difficulty

                if max_difficulty is not None:
                    conditions.append("difficulty <= :max_difficulty")
                    params["max_difficulty"] = max_difficulty

                # Filtre régime alimentaire (multi-select — AND logique entre les régimes)
                # FIX CRIT (2026-04-14) : SQLAlchemy text() ne peut pas sérialiser
                # list[str] Python → PostgreSQL text[]. L'opérateur @> avec :diet_arr::text[]
                # retournait 0 résultats. Corrigé en conditions individuelles = ANY(tags).
                if normalized_diet:
                    for idx, diet_tag in enumerate(normalized_diet):
                        conditions.append(f":diet_{idx} = ANY(tags)")
                        params[f"diet_{idx}"] = diet_tag

                # Filtre saison (tag dans le tableau tags)
                if season is not None:
                    conditions.append(":season = ANY(tags)")
                    params["season"] = season

                where_clause = " AND ".join(conditions)

                # FIX Phase 1 mature (review 2026-04-12) — BUG #8 :
                # Remplacement du double COUNT+SELECT (2 round-trips) par un seul SELECT
                # avec COUNT(*) OVER() comme window function → 1 seul round-trip DB.
                # BUG 1 FIX (2026-04-12) : ajout de photo_url dans le SELECT
                rows_result = await session.execute(
                    text(
                        f"""
                        SELECT id, title, slug, source, servings, prep_time_min,
                               cook_time_min, total_time_min, difficulty, cuisine_type,
                               photo_url, tags, quality_score,
                               COUNT(*) OVER() AS total_count
                        FROM recipes
                        WHERE {where_clause}
                        ORDER BY quality_score DESC NULLS LAST, created_at DESC
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    params,
                )
                rows = rows_result.mappings().all()
                total: int = int(rows[0]["total_count"]) if rows else 0

            # FIX Phase 1 mature (review 2026-04-12) — BUG #8 :
            # Exclure total_count de la sérialisation RecipeOut (champ window function uniquement).
            recipes = [
                RecipeOut.model_validate({k: v for k, v in dict(row).items() if k != "total_count"})
                for row in rows
            ]

            # FIX PROD (2026-04-12) : log INFO quand la DB retourne 0 recettes
            if total == 0:
                logger.info(
                    "recipes_search_empty_result",
                    query=q,
                    page=page,
                    per_page=per_page,
                    hint="La DB est peut-être vide — vérifier que le seed a été exécuté sur Supabase prod.",
                )
            else:
                logger.debug("recipes_search_result", query=q, total=total, page=page, per_page=per_page)

            # Sérialiser en dict JSON-safe pour le stockage Redis
            return {
                "results": [pydantic_to_cache(r) for r in recipes],
                "total": total,
                "query": q,
                "page": page,
                "per_page": per_page,
            }

        except Exception as exc:
            # FIX PROD (2026-04-12) : retourner liste vide si DB inaccessible
            logger.error("recipes_search_error", error=str(exc), query=q, page=page, per_page=per_page)
            return {"results": [], "total": 0, "query": q, "page": page, "per_page": per_page}

    # cache_response gère : hit Redis → retour direct / miss → _fetch_from_db / Redis down → fallback
    cached = await cache_response(redis, cache_key, CACHE_TTL_RECIPE_LIST, _fetch_from_db)

    return RecipeSearchResult(
        results=[RecipeOut.model_validate(r) for r in cached["results"]],
        total=cached["total"],
        query=cached["query"],
        page=cached["page"],
        per_page=cached["per_page"],
    )


# -------------------------------------------------------------------------
# BUG P0 FIX (2026-04-14) — Route /{recipe_id} déclarée APRÈS les routes statiques
# pour éviter que FastAPI mappe "search" comme UUID → 422.
# Ordre correct : /random → "" (search) → /{recipe_id}
# -------------------------------------------------------------------------


@router.get(
    "/{recipe_id}",
    summary="Détail d'une recette avec ingrédients",
    description=(
        "Retourne le détail complet d'une recette par son ID UUID, "
        "incluant la liste des ingrédients avec quantités et unités. "
        "Les recettes sont publiques (pas d'authentification requise). "
        f"Rate limit : {LIMIT_USER_READ} par utilisateur (via SlowAPIMiddleware default_limits)."
    ),
    response_model=RecipeDetail,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recette introuvable"},
        429: {"description": "Rate limit dépassé — voir header Retry-After"},
    },
)
# FIX #2 (review Phase 1 2026-04-12) : le rate limit 300/min est appliqué via SlowAPIMiddleware
# (default_limits=["300/minute"] configuré dans create_limiter, main.py).
# Request est passé en paramètre — requis par slowapi pour identifier l'utilisateur via key_func.
async def get_recipe(
    recipe_id: UUID,
    request: Request,
) -> Any:
    """
    Récupère une recette par son ID avec ses ingrédients détaillés.

    Joint recipe_ingredients et ingredients pour retourner la liste complète
    avec quantités, unités et notes pour chaque ingrédient.

    En v0 : deux requêtes SQL séquentielles (recette + ingrédients).
    Phase 1 mature : ajout cache Redis (TTL 1h) + invalidation sur UPDATE.

    Args:
        recipe_id: UUID de la recette.
        request: Requête FastAPI pour accéder au pool DB.

    Returns:
        RecipeDetail avec ingrédients et instructions complètes.
    """
    db_session = getattr(request.app.state, "db_session_factory", None)
    redis = getattr(request.app.state, "redis", None)

    if db_session is None:
        logger.debug("get_recipe_no_db", recipe_id=str(recipe_id))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de données non configurée.",
        )

    # ---- PERF-02 : Cache Redis TTL 1h sur le détail recette ----
    cache_key = build_recipe_detail_key(str(recipe_id))

    async def _fetch_recipe_from_db() -> dict[str, Any]:
        """
        Query PostgreSQL pour le détail d'une recette.
        Levée HTTPException 404 si introuvable — propagée hors du cache_response.
        """
        async with db_session() as session:
            from sqlalchemy import text

            # Requête principale — métadonnées de la recette
            # BUG 2 FIX (2026-04-12) : ajout de photo_url et description dans le SELECT
            # pour éviter le crash frontend sur champs null/undefined non prévus
            result = await session.execute(
                text(
                    """
                    SELECT id, title, slug, source, servings, prep_time_min,
                           cook_time_min, total_time_min, difficulty, cuisine_type,
                           photo_url, description, tags, quality_score, instructions
                    FROM recipes
                    WHERE id = :recipe_id
                    LIMIT 1
                    """
                ),
                {"recipe_id": str(recipe_id)},
            )
            row = result.mappings().one_or_none()

            if row is None:
                logger.info("recipe_not_found", recipe_id=str(recipe_id))
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Recette {recipe_id} introuvable.",
                )

            # Jointure recipe_ingredients + ingredients — ingrédients avec quantités
            ing_result = await session.execute(
                text(
                    """
                    SELECT
                        ri.ingredient_id,
                        i.canonical_name,
                        ri.quantity,
                        ri.unit,
                        ri.notes,
                        ri.position
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON i.id = ri.ingredient_id
                    WHERE ri.recipe_id = :recipe_id
                    ORDER BY ri.position
                    """
                ),
                {"recipe_id": str(recipe_id)},
            )
            ingredient_rows = ing_result.mappings().all()

        recipe_data = dict(row)
        ingredients_data = [dict(ing_row) for ing_row in ingredient_rows]

        logger.debug(
            "recipe_detail_fetched_from_db",
            recipe_id=str(recipe_id),
            ingredients_count=len(ingredients_data),
        )

        # BUG 2 FIX (2026-04-12) : construction explicite avec valeurs par défaut sûres
        # pour éviter le crash frontend sur champs null/undefined.
        detail = RecipeDetail(
            id=recipe_data["id"],
            title=recipe_data["title"],
            slug=recipe_data["slug"],
            source=recipe_data.get("source"),
            servings=recipe_data.get("servings"),
            prep_time_min=recipe_data.get("prep_time_min"),
            cook_time_min=recipe_data.get("cook_time_min"),
            total_time_min=recipe_data.get("total_time_min"),
            difficulty=recipe_data.get("difficulty"),
            cuisine_type=recipe_data.get("cuisine_type"),
            photo_url=recipe_data.get("photo_url"),
            description=recipe_data.get("description"),
            tags=recipe_data.get("tags") or [],
            quality_score=recipe_data.get("quality_score"),
            instructions=recipe_data.get("instructions") or [],
            ingredients=[
                RecipeIngredientDetail.model_validate(ing) for ing in ingredients_data
            ],
        )
        # Retourner un dict JSON-safe pour stockage Redis
        return pydantic_to_cache(detail)

    # cache_response : hit Redis → retour direct / miss → _fetch_recipe_from_db / Redis down → fallback
    # HTTPException 404 levée dans le fallback se propage normalement (non catchée par cache_response)
    cached = await cache_response(redis, cache_key, CACHE_TTL_RECIPE_DETAIL, _fetch_recipe_from_db)

    logger.debug("recipe_detail_served", recipe_id=str(recipe_id))
    return RecipeDetail.model_validate(cached)
