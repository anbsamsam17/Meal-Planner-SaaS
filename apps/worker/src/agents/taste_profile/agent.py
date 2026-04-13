"""
Agent TASTE_PROFILE v0 — moteur de recommandation personnalisé.

Construit un vecteur de goût (384 dims, espace all-MiniLM-L6-v2) pour
chaque membre à partir de ses feedbacks sur les recettes.

Algorithme v0 (content-based filtering simple) :
1. Récupère tous les feedbacks du membre depuis recipe_feedbacks
2. Pour chaque recette aimée (rating >= 4 ou type "cooked"/"favorited") :
   récupère son embedding depuis recipe_embeddings
3. Calcule la moyenne pondérée des embeddings positifs (poids = rating/5)
4. Soustrait légèrement les embeddings des recettes skippées (poids = -0.2)
5. Normalise le vecteur résultant (norme L2 = 1)
6. Insère/met à jour dans member_taste_vectors

Limitations v0 (prévues pour Phase 2) :
- Pas de collaborative filtering (cold-start non géré)
- Poids linéaires simples (pas d'apprentissage par renforcement)
- Pas de décroissance temporelle des feedbacks anciens
- Pas de gestion des contraintes alimentaires

Table cible :
    member_taste_vectors (
        member_id UUID PK FK → household_members,
        taste_vector vector(384),
        num_feedbacks_used INT,
        updated_at TIMESTAMP
    )
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import numpy as np
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Poids appliqués selon le type de feedback et la note
WEIGHT_FAVORITED = 1.0      # Favori = signal fort positif
WEIGHT_COOKED_HIGH = 0.8    # Cuisiné avec note >= 4 = positif
WEIGHT_COOKED_MED = 0.4     # Cuisiné avec note < 4 = signal faible
WEIGHT_SKIPPED = -0.2       # Skippé = signal légèrement négatif


class TasteProfileAgent:
    """
    Agent TASTE_PROFILE v0 — mise à jour du vecteur de goût d'un membre.

    Une instance peut traiter plusieurs membres dans le même run.
    La session DB est passée à la méthode run() pour permettre
    la réutilisation du pool de connexions Celery.

    Usage :
        agent = TasteProfileAgent(session_factory=AsyncSessionLocal)
        result = await agent.run(member_id=uuid)
    """

    def __init__(self, session_factory: async_sessionmaker | None = None) -> None:
        """
        Initialise l'agent TASTE_PROFILE.

        Args:
            session_factory: Factory SQLAlchemy async. Si None,
                             importe AsyncSessionLocal depuis mealplanner_db.
        """
        self._session_factory = session_factory

    def _get_session_factory(self) -> async_sessionmaker:
        """Retourne la factory de sessions DB (import lazy pour Celery)."""
        if self._session_factory is not None:
            return self._session_factory
        from mealplanner_db.session import AsyncSessionLocal
        return AsyncSessionLocal

    async def run(self, member_id: UUID) -> dict[str, Any]:
        """
        Met à jour le vecteur de goût d'un membre.

        Récupère les feedbacks, calcule la moyenne pondérée des embeddings,
        normalise et insère dans member_taste_vectors.

        Args:
            member_id: UUID du membre dont le vecteur doit être mis à jour.

        Returns:
            Dict avec les clés :
            - status: "updated" | "no_feedback" | "no_positive_feedback" | "error"
            - vector_updated: bool
            - num_feedbacks: int (total des feedbacks trouvés)
            - num_positive: int (feedbacks utilisés pour le vecteur)
        """
        logger.info("taste_profile_run_start", member_id=str(member_id))

        session_factory = self._get_session_factory()

        try:
            async with session_factory() as session:
                feedbacks = await self._get_feedbacks(member_id, session)

                if not feedbacks:
                    logger.info(
                        "taste_profile_no_feedback",
                        member_id=str(member_id),
                    )
                    return {
                        "status": "no_feedback",
                        "vector_updated": False,
                        "num_feedbacks": 0,
                        "num_positive": 0,
                    }

                result = await self._compute_and_upsert(
                    member_id=member_id,
                    feedbacks=feedbacks,
                    session=session,
                )

        except Exception as exc:
            logger.error(
                "taste_profile_run_error",
                member_id=str(member_id),
                error=str(exc),
            )
            return {
                "status": "error",
                "vector_updated": False,
                "num_feedbacks": 0,
                "num_positive": 0,
                "error": str(exc),
            }

        logger.info(
            "taste_profile_run_complete",
            member_id=str(member_id),
            **result,
        )
        return result

    async def _get_feedbacks(
        self,
        member_id: UUID,
        session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """
        Récupère tous les feedbacks d'un membre depuis recipe_feedbacks.

        Retourne uniquement les feedbacks ayant un embedding disponible
        dans recipe_embeddings (jointure LEFT pour conserver les stats).

        Args:
            member_id: UUID du membre.
            session: Session SQLAlchemy async.

        Returns:
            Liste de dicts avec recipe_id, feedback_type, rating, embedding.
        """
        result = await session.execute(
            text(
                """
                SELECT
                    rf.recipe_id,
                    rf.feedback_type,
                    rf.rating,
                    re.embedding::text AS embedding_text
                FROM recipe_feedbacks rf
                LEFT JOIN recipe_embeddings re ON re.recipe_id = rf.recipe_id
                WHERE rf.member_id = :member_id
                ORDER BY rf.created_at DESC
                """
            ),
            {"member_id": str(member_id)},
        )
        return [dict(row) for row in result.mappings().all()]

    async def _get_recipe_embedding(
        self,
        recipe_id: str,
        session: AsyncSession,
    ) -> list[float] | None:
        """
        Récupère l'embedding d'une recette depuis recipe_embeddings.

        Args:
            recipe_id: UUID de la recette.
            session: Session SQLAlchemy async.

        Returns:
            Vecteur 384 dims ou None si absent.
        """
        result = await session.execute(
            text(
                """
                SELECT embedding::text AS embedding_text
                FROM recipe_embeddings
                WHERE recipe_id = :recipe_id
                LIMIT 1
                """
            ),
            {"recipe_id": recipe_id},
        )
        row = result.fetchone()
        if row is None or row[0] is None:
            return None
        return _parse_pgvector(row[0])

    async def _compute_and_upsert(
        self,
        member_id: UUID,
        feedbacks: list[dict[str, Any]],
        session: AsyncSession,
    ) -> dict[str, Any]:
        """
        Calcule le vecteur de goût et le persiste en base.

        Algorithme :
        1. Sépare les feedbacks positifs et négatifs
        2. Calcule la moyenne pondérée des embeddings
        3. Normalise le vecteur (norme L2)
        4. UPSERT dans member_taste_vectors

        Args:
            member_id: UUID du membre.
            feedbacks: Liste de feedbacks avec embeddings.
            session: Session SQLAlchemy async.

        Returns:
            Dict de résultat avec status et métriques.
        """
        positive_vecs: list[np.ndarray] = []
        negative_vecs: list[np.ndarray] = []
        num_no_embedding = 0

        for fb in feedbacks:
            embedding_text = fb.get("embedding_text")
            if embedding_text is None:
                num_no_embedding += 1
                continue

            embedding = _parse_pgvector(embedding_text)
            if embedding is None:
                num_no_embedding += 1
                continue

            vec = np.array(embedding, dtype=np.float32)
            fb_type = fb.get("feedback_type", "")
            rating = fb.get("rating")

            if fb_type == "favorited":
                positive_vecs.append(vec * WEIGHT_FAVORITED)
            elif fb_type == "cooked":
                if rating is not None and float(rating) >= 4.0:
                    positive_vecs.append(vec * WEIGHT_COOKED_HIGH)
                else:
                    positive_vecs.append(vec * WEIGHT_COOKED_MED)
            elif fb_type == "skipped":
                negative_vecs.append(vec * WEIGHT_SKIPPED)

        if not positive_vecs:
            logger.info(
                "taste_profile_no_positive_feedback",
                member_id=str(member_id),
                total_feedbacks=len(feedbacks),
                no_embedding=num_no_embedding,
            )
            return {
                "status": "no_positive_feedback",
                "vector_updated": False,
                "num_feedbacks": len(feedbacks),
                "num_positive": 0,
            }

        # Moyenne pondérée de tous les vecteurs (positifs + négatifs)
        all_vecs = positive_vecs + negative_vecs
        combined = np.mean(all_vecs, axis=0)

        # Normalisation L2 → vecteur unitaire
        norm = np.linalg.norm(combined)
        if norm == 0:
            logger.warning(
                "taste_profile_zero_norm",
                member_id=str(member_id),
            )
            return {
                "status": "error",
                "vector_updated": False,
                "num_feedbacks": len(feedbacks),
                "num_positive": len(positive_vecs),
                "error": "Norme nulle après combinaison des vecteurs.",
            }

        normalized = combined / norm
        await self._upsert_taste_vector(member_id, normalized.tolist(), session)

        return {
            "status": "updated",
            "vector_updated": True,
            "num_feedbacks": len(feedbacks),
            "num_positive": len(positive_vecs),
            "num_negative": len(negative_vecs),
            "num_no_embedding": num_no_embedding,
        }

    async def _upsert_taste_vector(
        self,
        member_id: UUID,
        vector: list[float],
        session: AsyncSession,
    ) -> None:
        """
        Insère ou met à jour le vecteur de goût dans member_taste_vectors.

        Utilise ON CONFLICT (member_id) DO UPDATE pour l'idempotence.
        La tâche Celery peut être rejouée sans risque de doublon.

        Args:
            member_id: UUID du membre.
            vector: Vecteur normalisé 384 dims.
            session: Session SQLAlchemy async.
        """
        embedding_str = "[" + ",".join(str(round(v, 6)) for v in vector) + "]"

        await session.execute(
            text(
                """
                INSERT INTO member_taste_vectors (
                    member_id, taste_vector, num_feedbacks_used, updated_at
                )
                SELECT
                    :member_id,
                    :embedding::vector,
                    (
                        SELECT COUNT(*) FROM recipe_feedbacks
                        WHERE member_id = :member_id
                    ),
                    NOW()
                ON CONFLICT (member_id) DO UPDATE SET
                    taste_vector = EXCLUDED.taste_vector,
                    num_feedbacks_used = EXCLUDED.num_feedbacks_used,
                    updated_at = NOW()
                """
            ),
            {
                "member_id": str(member_id),
                "embedding": embedding_str,
            },
        )
        await session.commit()

        logger.info(
            "taste_profile_vector_upserted",
            member_id=str(member_id),
            vector_dim=len(vector),
        )


# ---- Fonctions utilitaires ----

def _parse_pgvector(text_repr: str) -> list[float] | None:
    """
    Parse la représentation texte d'un vecteur pgvector.

    Le format pgvector retourné via ::text est : "[0.1,0.2,...,0.384]"

    Args:
        text_repr: Représentation textuelle du vecteur.

    Returns:
        Liste de floats ou None si parsing impossible.
    """
    try:
        cleaned = text_repr.strip().lstrip("[").rstrip("]")
        return [float(v) for v in cleaned.split(",")]
    except (ValueError, AttributeError) as exc:
        logger.warning("taste_profile_parse_vector_error", error=str(exc))
        return None
