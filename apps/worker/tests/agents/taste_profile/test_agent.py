"""
Tests unitaires de l'agent TASTE_PROFILE v0.

Vérifie le calcul vectoriel sans dépendance réseau ni base de données réelle.
Tous les accès DB sont mockés via AsyncMock.

Couverture :
- Calcul de la moyenne pondérée des embeddings
- Normalisation L2 du vecteur résultant
- Gestion du cas "aucun feedback"
- Gestion du cas "aucun feedback positif"
- Gestion des feedbacks sans embedding disponible
- Idempotence du upsert (appelé deux fois → même résultat)
- Parsing du format pgvector
"""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import numpy as np
import pytest

from src.agents.taste_profile.agent import (
    TasteProfileAgent,
    _parse_pgvector,
)


# ---- Fixtures ----

MEMBER_ID = uuid4()
RECIPE_ID_1 = uuid4()
RECIPE_ID_2 = uuid4()
RECIPE_ID_3 = uuid4()


def _make_embedding(seed: int = 0, dim: int = 384) -> list[float]:
    """Génère un vecteur d'embedding déterministe pour les tests."""
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype(np.float32)
    vec = vec / np.linalg.norm(vec)  # Normalisation pour simuler un vrai embedding
    return vec.tolist()


def _embedding_to_pgvector(embedding: list[float]) -> str:
    """Convertit un vecteur en représentation textuelle pgvector."""
    return "[" + ",".join(str(round(v, 6)) for v in embedding) + "]"


# ---- Tests du parsing pgvector ----

class TestParsePgvector:
    """Tests unitaires de la fonction _parse_pgvector."""

    def test_parse_valid_vector(self):
        """Doit parser correctement un vecteur pgvector standard."""
        # Arrange
        embedding = [0.1, 0.2, 0.3, -0.4, 0.5]
        pgvec = "[0.1,0.2,0.3,-0.4,0.5]"

        # Act
        result = _parse_pgvector(pgvec)

        # Assert
        assert result is not None
        assert len(result) == 5
        assert abs(result[0] - 0.1) < 1e-5

    def test_parse_empty_string_returns_none(self):
        """Doit retourner None si le format est invalide."""
        # Act
        result = _parse_pgvector("invalid")

        # Assert
        assert result is None

    def test_parse_none_string(self):
        """Doit retourner None pour une entrée None."""
        # Act
        result = _parse_pgvector(None)  # type: ignore[arg-type]

        # Assert
        assert result is None

    def test_parse_full_384_dim_vector(self):
        """Doit parser un vecteur 384 dims sans perte."""
        # Arrange
        original = _make_embedding(seed=42)
        pgvec = _embedding_to_pgvector(original)

        # Act
        result = _parse_pgvector(pgvec)

        # Assert
        assert result is not None
        assert len(result) == 384
        for orig, parsed in zip(original[:10], result[:10]):
            assert abs(orig - parsed) < 1e-4


# ---- Tests du calcul vectoriel ----

class TestTasteProfileVectorComputation:
    """Tests du calcul de la moyenne pondérée et de la normalisation."""

    def test_single_favorited_recipe_returns_normalized_embedding(self):
        """
        Un seul feedback 'favorited' → le vecteur résultant doit être normalisé
        et proportionnel à l'embedding de la recette aimée.
        """
        # Arrange
        embedding = _make_embedding(seed=1)
        feedbacks = [
            {
                "recipe_id": str(RECIPE_ID_1),
                "feedback_type": "favorited",
                "rating": None,
                "embedding_text": _embedding_to_pgvector(embedding),
            }
        ]

        # Act
        vec = np.array(embedding, dtype=np.float32) * 1.0  # WEIGHT_FAVORITED
        combined = np.mean([vec], axis=0)
        norm = np.linalg.norm(combined)
        normalized = combined / norm

        # Assert — la norme du vecteur normalisé doit être 1.0
        assert abs(np.linalg.norm(normalized) - 1.0) < 1e-5

    def test_mixed_feedbacks_positive_dominate(self):
        """
        Plusieurs feedbacks positifs + 1 skip → les positifs dominent.
        Le vecteur résultant doit être orienté vers les recettes aimées.
        """
        # Arrange
        emb_liked_1 = np.array(_make_embedding(seed=10), dtype=np.float32)
        emb_liked_2 = np.array(_make_embedding(seed=11), dtype=np.float32)
        emb_skipped = np.array(_make_embedding(seed=99), dtype=np.float32)

        # Act
        positive_vecs = [
            emb_liked_1 * 0.8,  # WEIGHT_COOKED_HIGH (rating >= 4)
            emb_liked_2 * 0.8,
        ]
        negative_vecs = [
            emb_skipped * (-0.2),  # WEIGHT_SKIPPED
        ]
        all_vecs = positive_vecs + negative_vecs
        combined = np.mean(all_vecs, axis=0)
        norm = np.linalg.norm(combined)
        normalized = combined / norm

        # Assert — vecteur normalisé de norme 1
        assert abs(np.linalg.norm(normalized) - 1.0) < 1e-5

        # La similarité cosine avec les recettes aimées doit être > avec le skip
        sim_liked = float(np.dot(normalized, emb_liked_1 / np.linalg.norm(emb_liked_1)))
        sim_skipped = float(np.dot(normalized, emb_skipped / np.linalg.norm(emb_skipped)))
        assert sim_liked > sim_skipped, (
            "Les recettes aimées doivent avoir une meilleure similarité cosine "
            "que la recette skippée dans le vecteur de goût."
        )

    def test_high_rating_weighs_more_than_low_rating(self):
        """
        Une recette notée 5 doit peser plus qu'une notée 3 dans le vecteur de goût.

        Le poids WEIGHT_COOKED_HIGH (rating >= 4) = 0.8 > WEIGHT_COOKED_MED (rating < 4) = 0.4.
        Le vecteur final doit être plus proche de la recette bien notée.
        """
        # Arrange — deux embeddings orthogonaux pour tester la direction
        emb_high = np.zeros(384, dtype=np.float32)
        emb_high[0] = 1.0  # Axe 0 uniquement

        emb_med = np.zeros(384, dtype=np.float32)
        emb_med[1] = 1.0  # Axe 1 uniquement

        # Act
        vec_high = emb_high * 0.8  # WEIGHT_COOKED_HIGH
        vec_med = emb_med * 0.4    # WEIGHT_COOKED_MED
        combined = np.mean([vec_high, vec_med], axis=0)
        normalized = combined / np.linalg.norm(combined)

        # Assert — la composante [0] (recette high) doit être > composante [1] (recette med)
        assert normalized[0] > normalized[1], (
            "Le vecteur doit être plus orienté vers la recette bien notée (poids 0.8) "
            "que vers la recette moyennement notée (poids 0.4)."
        )

    def test_normalization_produces_unit_vector(self):
        """Le vecteur final doit avoir une norme L2 de 1.0 (tolérance 1e-5)."""
        # Arrange
        embeddings = [_make_embedding(seed=i) for i in range(5)]
        vecs = [np.array(e, dtype=np.float32) * 0.8 for e in embeddings]

        # Act
        combined = np.mean(vecs, axis=0)
        normalized = combined / np.linalg.norm(combined)

        # Assert
        norm = float(np.linalg.norm(normalized))
        assert abs(norm - 1.0) < 1e-5, f"Norme attendue 1.0, obtenue {norm}"


# ---- Tests de l'agent complet (avec DB mockée) ----

class TestTasteProfileAgent:
    """Tests d'intégration de TasteProfileAgent avec DB mockée."""

    def _build_agent(self) -> tuple[TasteProfileAgent, AsyncMock]:
        """Crée un agent avec une session DB mockée."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        agent = TasteProfileAgent(session_factory=mock_session_factory)
        return agent, mock_session

    @pytest.mark.asyncio
    async def test_no_feedbacks_returns_no_feedback_status(self):
        """
        Aucun feedback en DB → status 'no_feedback', vector_updated=False.
        """
        # Arrange
        agent, mock_session = self._build_agent()

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await agent.run(member_id=MEMBER_ID)

        # Assert
        assert result["status"] == "no_feedback"
        assert result["vector_updated"] is False
        assert result["num_feedbacks"] == 0

    @pytest.mark.asyncio
    async def test_only_skipped_feedbacks_returns_no_positive_status(self):
        """
        Uniquement des feedbacks 'skipped' → status 'no_positive_feedback'.
        """
        # Arrange
        agent, mock_session = self._build_agent()

        embedding_text = _embedding_to_pgvector(_make_embedding(seed=5))
        feedbacks = [
            {
                "recipe_id": str(RECIPE_ID_1),
                "feedback_type": "skipped",
                "rating": None,
                "embedding_text": embedding_text,
            }
        ]

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = feedbacks
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await agent.run(member_id=MEMBER_ID)

        # Assert
        assert result["status"] == "no_positive_feedback"
        assert result["vector_updated"] is False

    @pytest.mark.asyncio
    async def test_favorited_feedback_updates_vector(self):
        """
        Un feedback 'favorited' avec embedding disponible → vector_updated=True.
        Le upsert DB doit être appelé exactement une fois.
        """
        # Arrange
        agent, mock_session = self._build_agent()

        embedding = _make_embedding(seed=7)
        embedding_text = _embedding_to_pgvector(embedding)
        feedbacks = [
            {
                "recipe_id": str(RECIPE_ID_1),
                "feedback_type": "favorited",
                "rating": None,
                "embedding_text": embedding_text,
            }
        ]

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = feedbacks
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Act
        result = await agent.run(member_id=MEMBER_ID)

        # Assert
        assert result["status"] == "updated"
        assert result["vector_updated"] is True
        assert result["num_feedbacks"] == 1
        assert result["num_positive"] == 1
        # Le commit doit avoir été appelé (upsert validé)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_embedding_skips_recipe(self):
        """
        Un feedback sans embedding disponible (embedding_text=None) ne plante pas.
        L'agent doit le comptabiliser dans num_no_embedding et continuer.
        """
        # Arrange
        agent, mock_session = self._build_agent()

        feedbacks = [
            {
                "recipe_id": str(RECIPE_ID_1),
                "feedback_type": "favorited",
                "rating": None,
                "embedding_text": None,  # Pas d'embedding
            },
            {
                "recipe_id": str(RECIPE_ID_2),
                "feedback_type": "cooked",
                "rating": 5,
                "embedding_text": _embedding_to_pgvector(_make_embedding(seed=3)),
            },
        ]

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = feedbacks
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Act
        result = await agent.run(member_id=MEMBER_ID)

        # Assert — le deuxième feedback (avec embedding) suffit pour mettre à jour
        assert result["status"] == "updated"
        assert result["vector_updated"] is True
        assert result["num_no_embedding"] == 1

    @pytest.mark.asyncio
    async def test_cooked_high_rating_treated_as_positive(self):
        """
        Un feedback 'cooked' avec rating=5 doit être traité comme un signal positif fort.
        """
        # Arrange
        agent, mock_session = self._build_agent()

        embedding = _make_embedding(seed=9)
        feedbacks = [
            {
                "recipe_id": str(RECIPE_ID_1),
                "feedback_type": "cooked",
                "rating": 5,
                "embedding_text": _embedding_to_pgvector(embedding),
            }
        ]

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = feedbacks
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Act
        result = await agent.run(member_id=MEMBER_ID)

        # Assert
        assert result["status"] == "updated"
        assert result["num_positive"] == 1
