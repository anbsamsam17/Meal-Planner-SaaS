"""
Tests du service OFFMapper — mapping ingrédients → Open Food Facts.

Stratégie :
- Mock du client OpenFoodFactsClient pour éviter les appels réseau
- Tests du batch processing et de la logique de mise en cache
- Tests des ingrédients génériques (exclusion)
- Tests de la mise à jour en base (mock DB session)

Architecture AAA (Arrange → Act → Assert).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.agents.recipe_scout.off_mapper import OFFMapper
from src.agents.recipe_scout.connectors.openfoodfacts import OFFProduct, OpenFoodFactsClient


# ---- Fixtures ----

@pytest.fixture
def mock_off_product() -> OFFProduct:
    """Produit OFF de test."""
    return OFFProduct(
        off_id="3017620422003",
        name="Lait entier",
        category="Produits laitiers",
        brand="Président",
        completeness=0.85,
        unique_scans_n=5000,
    )


@pytest.fixture
def mock_session_factory() -> MagicMock:
    """Mock de la factory de sessions SQLAlchemy."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session

    return mock_factory


@pytest.fixture
def mapper_avec_mock_session(mock_session_factory: MagicMock) -> OFFMapper:
    """Instance OFFMapper avec session DB mockée."""
    mapper = OFFMapper(session_factory=mock_session_factory)
    return mapper


# ---- Tests OpenFoodFactsClient (cache) ----

class TestOpenFoodFactsClientCache:
    """Tests du cache LRU du client OFF."""

    def test_cache_hit_evite_appel_reseau(self) -> None:
        """Un hit de cache ne doit pas déclencher d'appel HTTP."""
        client = OpenFoodFactsClient()

        # Pré-remplir le cache manuellement
        client._cache["fr:lait"] = OFFProduct(
            off_id="3017620422003",
            name="Lait entier",
            category="Produits laitiers",
            brand="Président",
            completeness=0.85,
            unique_scans_n=5000,
        )

        with patch.object(client, "_fetch_product") as mock_fetch:
            result = client.search_product("lait", locale="fr")

        # Aucun appel réseau si cache hit
        mock_fetch.assert_not_called()
        assert result is not None
        assert result.off_id == "3017620422003"

    def test_cache_miss_declenche_appel_reseau(self, mock_off_product: OFFProduct) -> None:
        """Un miss de cache doit déclencher un appel HTTP."""
        client = OpenFoodFactsClient()

        with patch.object(client, "_fetch_product", return_value=mock_off_product) as mock_fetch:
            result = client.search_product("poulet", locale="fr")

        mock_fetch.assert_called_once_with("poulet", "fr")
        assert result == mock_off_product

    def test_cache_none_evite_double_appel(self) -> None:
        """Un None en cache évite les appels répétés pour les misses."""
        client = OpenFoodFactsClient()
        client._cache["fr:ingredient-introuvable"] = None

        with patch.object(client, "_fetch_product") as mock_fetch:
            result = client.search_product("ingredient-introuvable", locale="fr")

        mock_fetch.assert_not_called()
        assert result is None

    def test_stats_cache(self, mock_off_product: OFFProduct) -> None:
        """Les statistiques de cache doivent être correctement incrémentées."""
        client = OpenFoodFactsClient()

        with patch.object(client, "_fetch_product", return_value=mock_off_product):
            client.search_product("lait", locale="fr")  # miss
            client.search_product("lait", locale="fr")  # hit

        stats = client.cache_stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] >= 1


# ---- Tests OFFMapper._map_single_ingredient ----

class TestOFFMapperSingleIngredient:
    """Tests du mapping d'un ingrédient unique."""

    @pytest.mark.asyncio
    async def test_ingredient_generique_skip(
        self, mapper_avec_mock_session: OFFMapper
    ) -> None:
        """Les ingrédients génériques (sel, eau) doivent être skippés."""
        ingredient_id = str(uuid4())

        with patch.object(
            mapper_avec_mock_session.off_client,
            "search_product",
        ) as mock_search:
            result = await mapper_avec_mock_session._map_single_ingredient(
                ingredient_id=ingredient_id,
                canonical_name="sel",
                category="épicerie",
            )

        # Pas d'appel OFF pour les ingrédients génériques
        mock_search.assert_not_called()
        assert result == "no_match"

    @pytest.mark.asyncio
    async def test_ingredient_trouve_retourne_matched(
        self, mapper_avec_mock_session: OFFMapper, mock_off_product: OFFProduct
    ) -> None:
        """Un ingrédient trouvé en OFF doit retourner 'matched'."""
        ingredient_id = str(uuid4())

        with patch.object(
            mapper_avec_mock_session.off_client,
            "search_product",
            return_value=mock_off_product,
        ):
            result = await mapper_avec_mock_session._map_single_ingredient(
                ingredient_id=ingredient_id,
                canonical_name="lait entier",
                category="produits laitiers",
            )

        assert result == "matched"

    @pytest.mark.asyncio
    async def test_ingredient_non_trouve_retourne_no_match(
        self, mapper_avec_mock_session: OFFMapper
    ) -> None:
        """Un ingrédient sans résultat OFF doit retourner 'no_match'."""
        ingredient_id = str(uuid4())

        with patch.object(
            mapper_avec_mock_session.off_client,
            "search_product",
            return_value=None,
        ):
            result = await mapper_avec_mock_session._map_single_ingredient(
                ingredient_id=ingredient_id,
                canonical_name="ingrédient-inexistant-xyz",
                category=None,
            )

        assert result == "no_match"

    @pytest.mark.asyncio
    async def test_update_off_id_appele(
        self, mapper_avec_mock_session: OFFMapper, mock_off_product: OFFProduct
    ) -> None:
        """La mise à jour en DB doit être appelée après un match."""
        ingredient_id = str(uuid4())

        with patch.object(
            mapper_avec_mock_session.off_client,
            "search_product",
            return_value=mock_off_product,
        ), patch.object(
            mapper_avec_mock_session,
            "_update_off_id",
            new_callable=AsyncMock,
        ) as mock_update:
            await mapper_avec_mock_session._map_single_ingredient(
                ingredient_id=ingredient_id,
                canonical_name="lait",
                category="laitier",
            )

        mock_update.assert_called_once_with(ingredient_id, mock_off_product.off_id)


# ---- Tests OFFMapper.map_missing_ingredients (batch) ----

class TestOFFMapperBatch:
    """Tests du batch mapping."""

    @pytest.mark.asyncio
    async def test_batch_vide_retourne_zero(
        self, mapper_avec_mock_session: OFFMapper
    ) -> None:
        """Un batch vide doit retourner des stats à zéro."""
        # Mock : aucun ingrédient en base
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mapper_avec_mock_session.session_factory.return_value.execute = AsyncMock(
            return_value=mock_result
        )

        stats = await mapper_avec_mock_session.map_missing_ingredients(batch_size=50)

        assert stats["total_processed"] == 0
        assert stats["matched"] == 0
        assert stats["no_match"] == 0

    @pytest.mark.asyncio
    async def test_stats_aggregees_correctement(
        self, mapper_avec_mock_session: OFFMapper, mock_off_product: OFFProduct
    ) -> None:
        """Les statistiques de batch doivent agréger correctement."""
        # Arrange : 2 ingrédients, 1 matchera, 1 ne matchera pas
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {"id": uuid4(), "canonical_name": "lait", "category": "laitier"},
            {"id": uuid4(), "canonical_name": "ingrédient-xyz-inexistant", "category": None},
        ]
        mapper_avec_mock_session.session_factory.return_value.execute = AsyncMock(
            return_value=mock_result
        )

        def search_side_effect(query: str, locale: str) -> OFFProduct | None:
            if "lait" in query:
                return mock_off_product
            return None

        with patch.object(
            mapper_avec_mock_session.off_client,
            "search_product",
            side_effect=search_side_effect,
        ), patch.object(
            mapper_avec_mock_session,
            "_update_off_id",
            new_callable=AsyncMock,
        ):
            stats = await mapper_avec_mock_session.map_missing_ingredients(batch_size=50)

        assert stats["total_processed"] == 2
        assert stats["matched"] == 1
        assert stats["no_match"] == 1
        assert stats["errors"] == 0


# ---- Tests _score_product ----

class TestScoreProduct:
    """Tests du scoring de pertinence des produits OFF."""

    def test_produit_populaire_score_eleve(self) -> None:
        from src.agents.recipe_scout.connectors.openfoodfacts import _score_product

        produit_populaire = {
            "unique_scans_n": 10000,
            "completeness": 1.0,
            "brands": "Président",
        }
        produit_inconnu = {
            "unique_scans_n": 1,
            "completeness": 0.1,
            "brands": None,
        }

        assert _score_product(produit_populaire) > _score_product(produit_inconnu)

    def test_completeness_influence_score(self) -> None:
        from src.agents.recipe_scout.connectors.openfoodfacts import _score_product

        bien_documente = {"unique_scans_n": 100, "completeness": 0.9, "brands": None}
        peu_documente = {"unique_scans_n": 100, "completeness": 0.1, "brands": None}

        assert _score_product(bien_documente) > _score_product(peu_documente)
