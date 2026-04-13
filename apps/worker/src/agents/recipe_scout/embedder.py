"""
Wrapper sentence-transformers pour la génération d'embeddings de recettes.

Modèle : all-MiniLM-L6-v2
- Dimension : 384 (compatible pgvector)
- Taille : ~90MB sur disque, ~350MB en RAM
- Latence : ~5ms/recette CPU, ~1ms/recette GPU
- Qualité : MTEB score 56.26 (excellent rapport qualité/coût)

Choix du modèle (décision documentée project-context.md) :
- Coût zéro (local) vs OpenAI text-embedding-3-small (payant)
- Suffisant pour la déduplication cosine et la recherche sémantique
- Dimension 384 vs 1536 → index HNSW 4x plus rapide

Singleton : le modèle est chargé une seule fois au démarrage du worker
pour éviter le rechargement à chaque tâche Celery.
"""

from typing import TYPE_CHECKING, ClassVar

import numpy as np
from loguru import logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

# ---- Constantes ----

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class RecipeEmbedder:
    """
    Wrapper singleton pour le modèle sentence-transformers.

    Le modèle est chargé une seule fois à la première utilisation (lazy loading)
    et conservé en mémoire pour toutes les tâches suivantes.

    Usage :
        embedder = RecipeEmbedder.get_instance()
        vector = embedder.embed_text("Poulet rôti aux herbes de Provence")
        vectors = embedder.embed_batch(["Recette 1", "Recette 2"])
    """

    _instance: ClassVar["RecipeEmbedder | None"] = None
    _model: "SentenceTransformer | None" = None

    @classmethod
    def get_instance(cls) -> "RecipeEmbedder":
        """
        Retourne l'instance singleton du embedder.

        Crée l'instance si elle n'existe pas encore.
        Thread-safe pour Celery (chaque worker est un process séparé).
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self) -> "SentenceTransformer":
        """
        Charge le modèle sentence-transformers en mémoire.

        Le chargement prend 2-5 secondes la première fois.
        Les téléchargements du modèle (~90MB) sont mis en cache par Hugging Face.

        Returns:
            Instance SentenceTransformer prête à l'emploi.
        """
        if self._model is not None:
            return self._model

        logger.info("embedder_model_loading", model=MODEL_NAME)

        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(MODEL_NAME)

        # Vérification de la dimension — critique pour pgvector
        test_embedding = self._model.encode("test", convert_to_numpy=True)
        actual_dim = len(test_embedding)

        if actual_dim != EMBEDDING_DIM:
            raise ValueError(
                f"Dimension d'embedding incorrecte : attendu {EMBEDDING_DIM}, "
                f"obtenu {actual_dim}. "
                "Vérifier que le modèle est bien all-MiniLM-L6-v2."
            )

        logger.info("embedder_model_loaded", model=MODEL_NAME, dim=actual_dim)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """
        Génère le vecteur d'embedding d'un texte.

        Args:
            text: Texte à vectoriser (titre de recette, description, etc.).

        Returns:
            Liste de 384 floats représentant le vecteur d'embedding.
        """
        model = self._load_model()

        # Tronquer si trop long (all-MiniLM-L6-v2 max 256 tokens)
        text = text[:2000] if text else ""

        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Génère les embeddings pour une liste de textes en batch.

        Le traitement en batch est significativement plus rapide que
        les appels individuels (pipeline GPU optimisé).

        Args:
            texts: Liste de textes à vectoriser.
            batch_size: Taille du batch (32 est optimal pour CPU/GPU).

        Returns:
            Liste de vecteurs 384 dims, dans le même ordre que l'entrée.
        """
        if not texts:
            return []

        model = self._load_model()

        # Tronquer les textes trop longs
        texts_truncated = [t[:2000] if t else "" for t in texts]

        logger.debug(
            "embedder_batch_start",
            batch_size=len(texts_truncated),
            model=MODEL_NAME,
        )

        embeddings: np.ndarray = model.encode(
            texts_truncated,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        logger.debug(
            "embedder_batch_complete",
            count=len(embeddings),
            dim=embeddings.shape[1] if len(embeddings) > 0 else 0,
        )

        return embeddings.tolist()

    def build_recipe_text(
        self,
        title: str,
        ingredients: list[str] | None = None,
        cuisine_type: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """
        Construit le texte d'entrée pour l'embedding d'une recette.

        Combine plusieurs champs pour maximiser la pertinence sémantique.
        La structure est optimisée pour la déduplication et la recherche.

        Args:
            title: Titre de la recette (champ le plus important).
            ingredients: Liste de noms canoniques d'ingrédients.
            cuisine_type: Type de cuisine.
            tags: Tags de la recette.

        Returns:
            Texte combiné prêt pour l'embedding.
        """
        parts = [title]

        if cuisine_type:
            parts.append(f"cuisine {cuisine_type}")

        if tags:
            # Prendre les 5 premiers tags les plus pertinents
            parts.extend(tags[:5])

        if ingredients:
            # Ingrédients principaux (les 10 premiers sont suffisants)
            parts.append("ingrédients : " + ", ".join(ingredients[:10]))

        return " | ".join(parts)

    @staticmethod
    def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """
        Calcule la similarité cosine entre deux vecteurs.

        Utilisé pour la déduplication locale (sans pgvector).
        Pour la déduplication à grande échelle, utiliser dedup.py (pgvector).

        Args:
            vec1: Premier vecteur (384 dims).
            vec2: Second vecteur (384 dims).

        Returns:
            Score de similarité entre -1 et 1 (1 = identique).
        """
        a = np.array(vec1)
        b = np.array(vec2)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))
