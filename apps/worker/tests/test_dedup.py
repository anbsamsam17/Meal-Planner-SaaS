"""
Tests de la déduplication par similarité cosine.

Couverture :
- Déduplication intra-batch (sans pgvector)
- Calcul de la similarité cosine
- Détection des doublons évidents (même recette)
- Non-détection des recettes distinctes
"""

import pytest
import numpy as np

from src.agents.recipe_scout.dedup import (
    DEDUP_SIMILARITY_THRESHOLD,
    compute_batch_dedup,
    DedupResult,
)


class TestComputeBatchDedup:
    """Tests pour la déduplication en mémoire intra-batch."""

    def test_identical_embeddings_are_deduplicated(self):
        """
        Deux vecteurs identiques sont détectés comme doublons.

        Arrange : deux vecteurs 100% identiques.
        Act : compute_batch_dedup.
        Assert : seul 1 vecteur est retenu.
        """
        vec = [0.1, 0.2, 0.3] * 128  # 384 dims

        unique_indices = compute_batch_dedup([vec, vec])

        assert len(unique_indices) == 1
        assert unique_indices == [0]

    def test_distinct_embeddings_all_kept(self):
        """
        Des vecteurs orthogonaux (similarité 0) sont tous gardés.

        Arrange : 3 vecteurs orthogonaux (aucune similarité).
        Act : compute_batch_dedup.
        Assert : 3 vecteurs retenus.
        """
        # Vecteurs unitaires dans des directions orthogonales
        vec1 = [1.0] + [0.0] * 383
        vec2 = [0.0, 1.0] + [0.0] * 382
        vec3 = [0.0, 0.0, 1.0] + [0.0] * 381

        unique_indices = compute_batch_dedup([vec1, vec2, vec3])

        assert len(unique_indices) == 3

    def test_first_element_always_unique(self):
        """
        Le premier élément est toujours retenu (référence).

        Arrange : n'importe quel vecteur.
        Act : compute_batch_dedup([vec]).
        Assert : index 0 toujours dans la liste.
        """
        vec = [0.5] * 384
        unique_indices = compute_batch_dedup([vec])

        assert 0 in unique_indices

    def test_empty_list_returns_empty(self):
        """
        Une liste vide retourne une liste vide sans erreur.

        Arrange : [].
        Act : compute_batch_dedup([]).
        Assert : [].
        """
        result = compute_batch_dedup([])

        assert result == []

    def test_near_duplicate_above_threshold_removed(self):
        """
        Un vecteur très proche (>= 0.92 de similarité) est considéré doublon.

        Arrange : deux vecteurs quasi-identiques avec perturbation minimale.
        Act : compute_batch_dedup.
        Assert : seul 1 vecteur retenu (le premier).
        """
        # Créer un vecteur de base normalisé
        base = np.random.rand(384)
        base = base / np.linalg.norm(base)

        # Créer une perturbation minime (similarité ~0.999)
        noise = np.random.rand(384) * 0.001
        near_duplicate = base + noise
        near_duplicate = near_duplicate / np.linalg.norm(near_duplicate)

        # Vérifier que la similarité est bien au-dessus du seuil
        similarity = float(np.dot(base, near_duplicate))
        assert similarity >= DEDUP_SIMILARITY_THRESHOLD, (
            f"La perturbation est trop grande ({similarity:.4f} < {DEDUP_SIMILARITY_THRESHOLD})"
        )

        unique_indices = compute_batch_dedup([base.tolist(), near_duplicate.tolist()])

        assert len(unique_indices) == 1

    def test_below_threshold_both_kept(self):
        """
        Deux vecteurs en dessous du seuil sont tous les deux gardés.

        Arrange : vecteur et sa version fortement perturbée (similarité ~0.7).
        Act : compute_batch_dedup.
        Assert : 2 vecteurs retenus.
        """
        base = np.random.rand(384)
        base = base / np.linalg.norm(base)

        # Perturbation forte pour descendre en dessous de 0.92
        different = np.random.rand(384)
        different = different / np.linalg.norm(different)

        # S'assurer que la similarité est < seuil
        similarity = float(np.dot(base, different))
        # Si par hasard la similarité est trop haute, créer un vecteur orthogonal
        if similarity >= DEDUP_SIMILARITY_THRESHOLD:
            different = np.zeros(384)
            different[0] = 1.0  # Orthogonal à quasi tout

        unique_indices = compute_batch_dedup([base.tolist(), different.tolist()])

        assert len(unique_indices) == 2

    def test_batch_of_10_with_duplicates(self):
        """
        Déduplique correctement un batch avec plusieurs doublons.

        Arrange : 10 vecteurs avec 3 doublons (identiques au premier).
        Act : compute_batch_dedup.
        Assert : 7 vecteurs uniques retenus.
        """
        unique_vecs = [np.random.rand(384) for _ in range(7)]
        unique_vecs = [v / np.linalg.norm(v) for v in unique_vecs]

        # Répéter le premier vecteur 3 fois → 3 doublons
        duplicates = [unique_vecs[0].copy() for _ in range(3)]

        all_vecs = [v.tolist() for v in unique_vecs] + [v.tolist() for v in duplicates]

        unique_indices = compute_batch_dedup(all_vecs)

        assert len(unique_indices) == 7


class TestDedupResult:
    """Tests pour la dataclass DedupResult."""

    def test_dedup_result_not_duplicate(self):
        """
        DedupResult correctement initialisé pour un non-doublon.

        Arrange : is_duplicate=False.
        Act : création DedupResult.
        Assert : champs cohérents.
        """
        result = DedupResult(is_duplicate=False)

        assert result.is_duplicate is False
        assert result.similar_recipe_id is None
        assert result.similarity_score is None

    def test_dedup_result_is_duplicate(self):
        """
        DedupResult correctement initialisé pour un doublon.

        Arrange : is_duplicate=True avec ID et score.
        Act : création DedupResult.
        Assert : champs cohérents.
        """
        result = DedupResult(
            is_duplicate=True,
            similar_recipe_id="uuid-123",
            similarity_score=0.95,
        )

        assert result.is_duplicate is True
        assert result.similar_recipe_id == "uuid-123"
        assert result.similarity_score == 0.95


class TestDeduplicationThreshold:
    """Tests sur le seuil de déduplication."""

    def test_threshold_value(self):
        """
        Le seuil de déduplication est bien 0.92 (ROADMAP non-négociable).

        Arrange : valeur constante.
        Act : lecture de DEDUP_SIMILARITY_THRESHOLD.
        Assert : == 0.92.
        """
        assert DEDUP_SIMILARITY_THRESHOLD == 0.92, (
            f"Le seuil de déduplication doit être 0.92 (ROADMAP). "
            f"Valeur actuelle : {DEDUP_SIMILARITY_THRESHOLD}"
        )
