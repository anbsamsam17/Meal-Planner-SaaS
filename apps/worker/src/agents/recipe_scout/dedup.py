"""
Déduplication des recettes par similarité cosine via pgvector.

Stratégie :
1. Calculer l'embedding de la nouvelle recette (titre + ingrédients clés)
2. Requêter pgvector avec cosine distance < 0.08 (= similarité ≥ 0.92)
3. Si un doublon est trouvé → rejeter la nouvelle recette
4. Si aucun doublon → insérer et indexer

Seuil de déduplication : 0.92 (ROADMAP section 03)
- 0.92 = recettes quasi-identiques (même plat, variante mineure d'ingrédients)
- < 0.90 = recettes similaires mais distinctes (garder les deux)
- < 0.80 = recettes dans la même catégorie (pas de déduplication)

Note : la table recipe_embeddings utilise un index HNSW pour la recherche
approximative. En dessous de 10 000 recettes, une recherche exacte (IVFFlat)
peut être préférée pour la précision. Cf. phase-0/database/02-indexes.sql.
"""

from dataclasses import dataclass
from typing import Any

from loguru import logger

# Seuil de similarité cosine pour considérer deux recettes comme doublons
DEDUP_SIMILARITY_THRESHOLD = 0.92

# Distance cosine correspondante (pgvector utilise <=> pour la distance cosine)
# distance = 1 - similarity → similarity 0.92 = distance 0.08
DEDUP_COSINE_DISTANCE_THRESHOLD = 1.0 - DEDUP_SIMILARITY_THRESHOLD


@dataclass
class DedupResult:
    """Résultat d'une vérification de déduplication."""

    is_duplicate: bool
    similar_recipe_id: str | None = None
    similarity_score: float | None = None


async def find_similar_recipe(
    embedding: list[float],
    db_session: Any,
    exclude_recipe_id: str | None = None,
) -> DedupResult:
    """
    Recherche une recette similaire dans la base via pgvector.

    Utilise la distance cosine (opérateur <=>) sur la table recipe_embeddings.
    La requête exploite l'index HNSW pour des performances optimales.

    Args:
        embedding: Vecteur 384 dims de la recette à vérifier.
        db_session: Session SQLAlchemy async (service_role pour bypass RLS).
        exclude_recipe_id: ID de recette à exclure (pour les mises à jour).

    Returns:
        DedupResult indiquant si un doublon existe et lequel.
    """
    from sqlalchemy import text

    # Conversion en chaîne au format pgvector : [0.1, 0.2, ..., 0.384]
    embedding_str = "[" + ",".join(str(round(v, 6)) for v in embedding) + "]"

    # FIX #7 (review Phase 1 2026-04-12) : supprimer le WHERE sur la distance cosine
    # Le filtre "WHERE 1 - (embedding <=> ...) >= threshold" calcule la distance deux fois
    # ET empêche PostgreSQL d'utiliser l'index HNSW (scan séquentiel 76 MB à 50k recettes).
    # Pattern correct pgvector : ORDER BY ... LIMIT k, puis filtrer le seuil en Python.
    # Gain estimé : 80-400ms → 15-40ms avec index HNSW ef_search=40.
    query = text(
        """
        SELECT
            recipe_id,
            embedding <=> :embedding::vector AS distance
        FROM recipe_embeddings
        {exclude_clause}
        ORDER BY embedding <=> :embedding::vector
        LIMIT 1
        """.replace(
            "{exclude_clause}",
            "WHERE recipe_id != :exclude_id" if exclude_recipe_id else "",
        )
    )

    params: dict[str, Any] = {
        "embedding": embedding_str,
    }

    if exclude_recipe_id:
        params["exclude_id"] = exclude_recipe_id

    result = await db_session.execute(query, params)
    row = result.mappings().one_or_none()

    if row is None:
        return DedupResult(is_duplicate=False)

    # Filtre du seuil en Python (post-requête) — l'index HNSW a déjà réduit le scan
    similarity_score = 1.0 - float(row["distance"])
    if similarity_score < DEDUP_SIMILARITY_THRESHOLD:
        return DedupResult(is_duplicate=False)

    logger.info(
        "dedup_duplicate_found",
        similar_recipe_id=str(row["recipe_id"]),
        similarity_score=round(similarity_score, 4),
        threshold=DEDUP_SIMILARITY_THRESHOLD,
    )

    return DedupResult(
        is_duplicate=True,
        similar_recipe_id=str(row["recipe_id"]),
        similarity_score=similarity_score,
    )


async def is_recipe_duplicate(
    embedding: list[float],
    db_session: Any,
    recipe_title: str = "",
) -> bool:
    """
    Vérifie rapidement si une recette est un doublon.

    Wrapper pratique autour de `find_similar_recipe` pour un usage simple.

    Args:
        embedding: Vecteur 384 dims de la recette.
        db_session: Session DB async.
        recipe_title: Titre pour le logging.

    Returns:
        True si doublon, False sinon.
    """
    result = await find_similar_recipe(embedding, db_session)

    if result.is_duplicate:
        logger.info(
            "dedup_recipe_rejected",
            title=recipe_title[:80],
            similar_id=result.similar_recipe_id,
            similarity=result.similarity_score,
        )
        return True

    return False


def compute_batch_dedup(
    embeddings: list[list[float]],
    similarity_threshold: float = DEDUP_SIMILARITY_THRESHOLD,
) -> list[int]:
    """
    Déduplication locale en mémoire pour un batch de recettes.

    Utilisé avant l'insertion en DB pour éviter les doublons intra-batch.
    Complexité O(n²) — acceptable pour des batches < 1000 recettes.
    Au-delà, utiliser la déduplication pgvector.

    Args:
        embeddings: Liste de vecteurs à comparer entre eux.
        similarity_threshold: Seuil de similarité pour considérer un doublon.

    Returns:
        Indices des embeddings uniques (les doublons sont exclus).
    """
    import numpy as np

    if not embeddings:
        return []

    unique_indices: list[int] = [0]  # Le premier est toujours unique

    for i in range(1, len(embeddings)):
        vec_i = np.array(embeddings[i])
        norm_i = np.linalg.norm(vec_i)
        if norm_i == 0:
            continue

        is_dup = False
        for j in unique_indices:
            vec_j = np.array(embeddings[j])
            norm_j = np.linalg.norm(vec_j)
            if norm_j == 0:
                continue

            similarity = float(np.dot(vec_i, vec_j) / (norm_i * norm_j))
            if similarity >= similarity_threshold:
                is_dup = True
                logger.debug(
                    "dedup_batch_duplicate",
                    index_new=i,
                    index_existing=j,
                    similarity=round(similarity, 4),
                )
                break

        if not is_dup:
            unique_indices.append(i)

    dedup_count = len(embeddings) - len(unique_indices)
    if dedup_count > 0:
        logger.info(
            "dedup_batch_complete",
            total=len(embeddings),
            unique=len(unique_indices),
            duplicates_removed=dedup_count,
        )

    return unique_indices
