"""
RecipeRetriever — recherche de recettes candidates via pgvector.

Ce module implémente la recherche hybride (sémantique + filtres) pour
trouver les recettes candidates du plan hebdomadaire.

Pipeline de recherche :
1. Agréger les vecteurs de goût de tous les membres du foyer
2. Requête pgvector HNSW avec pré-filtrage (temps, tags exclus)
3. Filtrage anti-répétition (exclure les recettes des 3 dernières semaines)
4. Retour des k meilleures candidates

Performance cible : < 100ms p95 (index HNSW activé par ORDER BY pgvector).

Note architecture SQL :
La requête utilise ORDER BY ... <=> distance pour activer l'index HNSW.
Le filtrage par seuil est fait côté Python (évite le scan séquentiel).
Décision documentée dans project-context.md (2026-04-12).
"""

from datetime import date, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.weekly_planner.constraint_builder import HouseholdConstraints

# Nombre de candidats à récupérer (avant sélection finale)
DEFAULT_K_CANDIDATES = 50

# Période d'anti-répétition (en semaines)
ANTI_REPEAT_WEEKS = 3


async def get_household_taste_vector(
    session: AsyncSession,
    household_id: UUID,
) -> list[float] | None:
    """
    Récupère et agrège les vecteurs de goût de tous les membres du foyer.

    Stratégie d'agrégation : moyenne pondérée (poids 1 adulte = 1, enfant = 0.5).
    En v0 : moyenne simple (même poids pour tous les membres).

    Args:
        session: Session SQLAlchemy async.
        household_id: UUID du foyer.

    Returns:
        Vecteur de goût agrégé (384 dims) ou None si aucun vecteur.
    """
    result = await session.execute(
        text(
            """
            SELECT mtv.vector, hm.is_child
            FROM member_taste_vectors mtv
            JOIN household_members hm ON hm.id = mtv.member_id
            WHERE hm.household_id = :household_id
            """
        ),
        {"household_id": str(household_id)},
    )
    rows = result.fetchall()

    if not rows:
        logger.info("recipe_retriever_no_taste_vectors", household_id=str(household_id))
        return None

    # Agrégation : moyenne simple en v0
    # En v1 : pondération adultes/enfants + recency weighting
    vectors = [row[0] for row in rows]
    dim = len(vectors[0])

    aggregated = [0.0] * dim
    for vec in vectors:
        for i, val in enumerate(vec):
            aggregated[i] += val

    # Normalisation par le nombre de membres
    n = len(vectors)
    aggregated = [v / n for v in aggregated]

    logger.debug(
        "recipe_retriever_taste_vector_aggregated",
        household_id=str(household_id),
        member_count=n,
        vector_dim=dim,
    )

    return aggregated


async def get_recently_planned_recipe_ids(
    session: AsyncSession,
    household_id: UUID,
    weeks: int = ANTI_REPEAT_WEEKS,
) -> list[str]:
    """
    Retourne les IDs des recettes cuisinées dans les N dernières semaines.

    Utilisé pour l'anti-répétition : ces recettes seront exclues des candidates.

    Args:
        session: Session SQLAlchemy async.
        household_id: UUID du foyer.
        weeks: Nombre de semaines à remonter.

    Returns:
        Liste d'UUIDs (str) des recettes récentes.
    """
    cutoff_date = date.today() - timedelta(weeks=weeks)

    result = await session.execute(
        text(
            """
            SELECT DISTINCT pm.recipe_id::text
            FROM planned_meals pm
            JOIN weekly_plans wp ON wp.id = pm.plan_id
            WHERE wp.household_id = :household_id
              AND wp.week_start >= :cutoff_date
              AND wp.status IN ('validated', 'draft')
            """
        ),
        {
            "household_id": str(household_id),
            "cutoff_date": cutoff_date.isoformat(),
        },
    )
    ids = [row[0] for row in result.fetchall()]

    logger.debug(
        "recipe_retriever_recent_recipes",
        household_id=str(household_id),
        recent_count=len(ids),
        cutoff_date=str(cutoff_date),
    )

    return ids


async def retrieve_candidate_recipes(
    session: AsyncSession,
    household_id: UUID,
    constraints: HouseholdConstraints,
    taste_vector: list[float] | None = None,
    k: int = DEFAULT_K_CANDIDATES,
) -> list[dict]:
    """
    Récupère les recettes candidates via pgvector HNSW + filtres.

    Si taste_vector est None (nouveau foyer sans feedbacks), retourne
    les recettes les mieux notées (quality_score DESC) correspondant
    aux contraintes.

    Args:
        session: Session SQLAlchemy async.
        household_id: UUID du foyer.
        constraints: Contraintes agrégées du foyer.
        taste_vector: Vecteur de goût agrégé (None → classement qualité).
        k: Nombre de candidates à retourner.

    Returns:
        Liste de dicts avec les métadonnées des recettes candidates.
    """
    # IDs des recettes récentes à exclure (anti-répétition)
    recent_ids = await get_recently_planned_recipe_ids(session, household_id)

    if taste_vector is not None:
        # Recherche sémantique pgvector (path prioritaire)
        candidates = await _retrieve_by_similarity(
            session=session,
            taste_vector=taste_vector,
            constraints=constraints,
            recent_ids=recent_ids,
            k=k,
        )
    else:
        # Fallback : classement par quality_score (nouveau foyer sans historique)
        candidates = await _retrieve_by_quality(
            session=session,
            constraints=constraints,
            recent_ids=recent_ids,
            k=k,
        )

    logger.info(
        "recipe_retriever_candidates",
        household_id=str(household_id),
        candidate_count=len(candidates),
        excluded_recent=len(recent_ids),
        using_similarity=taste_vector is not None,
    )

    return candidates


async def _retrieve_by_similarity(
    session: AsyncSession,
    taste_vector: list[float],
    constraints: HouseholdConstraints,
    recent_ids: list[str],
    k: int,
) -> list[dict]:
    """
    Requête pgvector avec index HNSW pour la recherche par similarité.

    La requête utilise ORDER BY <=> pour activer l'index HNSW.
    Le filtrage par seuil est fait côté Python.

    Note : le paramètre :taste_vec doit être au format pgvector '[0.1,0.2,...]'.

    Args:
        session: Session SQLAlchemy async.
        taste_vector: Vecteur de goût (384 dims).
        constraints: Contraintes du foyer.
        recent_ids: IDs à exclure.
        k: Nombre de candidates.

    Returns:
        Liste de dicts recettes candidates.
    """
    # Format pgvector
    vector_str = "[" + ",".join(str(round(v, 6)) for v in taste_vector) + "]"

    # Construction des exclusions
    excluded_ids_clause = ""
    params: dict = {
        "taste_vec": vector_str,
        "time_max": constraints.time_max_min,
        "quality_min": 0.6,
        "k": k,
    }

    if recent_ids:
        excluded_ids_clause = "AND r.id::text != ALL(:recent_ids)"
        params["recent_ids"] = recent_ids

    # Exclusion des tags (allergies + régimes)
    excluded_tags_clause = ""
    if constraints.excluded_tags:
        excluded_tags_clause = "AND NOT (re.tags && :excluded_tags)"
        params["excluded_tags"] = constraints.excluded_tags

    # FIX Phase 1 mature (review 2026-04-12) — BUG #3 :
    # Vérification des alias confirmée via le schéma 01-schema-core.sql :
    # - `re.total_time_min` : colonne dénormalisée sur recipe_embeddings (OPT #1)
    #   → utilisée dans WHERE pour pré-filtrer AVANT le scan HNSW (cible <100ms)
    # - `r.total_time_min`  : colonne générée sur recipes (prep_time_min + cook_time_min)
    #   → utilisée dans SELECT pour retourner la valeur au caller
    # Les deux alias sont corrects — pas de substitution nécessaire.
    sql = f"""
        SELECT
            r.id::text,
            r.title,
            r.cuisine_type,
            r.prep_time_min,
            r.cook_time_min,
            r.total_time_min,
            r.difficulty,
            r.tags,
            r.quality_score,
            r.servings,
            r.photo_url,
            re.embedding <=> :taste_vec::vector AS distance
        FROM recipes r
        JOIN recipe_embeddings re ON re.recipe_id = r.id
        WHERE r.quality_score >= :quality_min
          AND (re.total_time_min IS NULL OR re.total_time_min <= :time_max)
          {excluded_tags_clause}
          {excluded_ids_clause}
        ORDER BY re.embedding <=> :taste_vec::vector
        LIMIT :k
    """

    result = await session.execute(text(sql), params)
    rows = result.mappings().all()

    return [dict(row) for row in rows]


async def _retrieve_by_quality(
    session: AsyncSession,
    constraints: HouseholdConstraints,
    recent_ids: list[str],
    k: int,
) -> list[dict]:
    """
    Fallback : classement par quality_score pour les nouveaux foyers.

    Args:
        session: Session SQLAlchemy async.
        constraints: Contraintes du foyer.
        recent_ids: IDs à exclure.
        k: Nombre de candidates.

    Returns:
        Liste de dicts recettes candidates.
    """
    params: dict = {
        "time_max": constraints.time_max_min,
        "quality_min": 0.6,
        "k": k,
    }

    excluded_ids_clause = ""
    if recent_ids:
        excluded_ids_clause = "AND r.id::text != ALL(:recent_ids)"
        params["recent_ids"] = recent_ids

    excluded_tags_clause = ""
    if constraints.excluded_tags:
        excluded_tags_clause = "AND NOT (re.tags && :excluded_tags)"
        params["excluded_tags"] = constraints.excluded_tags

    # FIX Phase 1 mature (review 2026-04-12) — BUG #3 :
    # re.total_time_min dans WHERE est correct : colonne dénormalisée sur recipe_embeddings.
    # r.total_time_min dans SELECT est correct : colonne générée sur recipes.
    sql = f"""
        SELECT
            r.id::text,
            r.title,
            r.cuisine_type,
            r.prep_time_min,
            r.cook_time_min,
            r.total_time_min,
            r.difficulty,
            r.tags,
            r.quality_score,
            r.servings,
            r.photo_url,
            0.0 AS distance
        FROM recipes r
        JOIN recipe_embeddings re ON re.recipe_id = r.id
        WHERE r.quality_score >= :quality_min
          AND (re.total_time_min IS NULL OR re.total_time_min <= :time_max)
          {excluded_tags_clause}
          {excluded_ids_clause}
        ORDER BY r.quality_score DESC, RANDOM()
        LIMIT :k
    """

    result = await session.execute(text(sql), params)
    rows = result.mappings().all()

    return [dict(row) for row in rows]
