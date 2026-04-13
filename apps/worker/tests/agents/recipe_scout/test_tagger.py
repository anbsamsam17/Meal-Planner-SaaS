"""
Tests unitaires pour le tagger de recettes Gemini.

Stratégie : mock de google.genai.Client pour tester sans appel réseau.
Le structured output Gemini retourne du JSON via response.text — mock trivial.

AAA pattern : Arrange → Act → Assert.
Swap Anthropic → Gemini (2026-04-12).
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.recipe_scout.tagger import (
    VALID_CUISINES,
    VALID_DIFFICULTIES,
    RecipeTags,
    merge_tags_to_list,
    tag_recipe,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_gemini_mock(payload: dict) -> MagicMock:
    """Construit un mock google.genai.Client avec une réponse JSON donnée."""
    mock_response = MagicMock()
    mock_response.text = json.dumps(payload)

    mock_aio_models = MagicMock()
    mock_aio_models.generate_content = AsyncMock(return_value=mock_response)

    mock_aio = MagicMock()
    mock_aio.models = mock_aio_models

    mock_client = MagicMock()
    mock_client.aio = mock_aio
    return mock_client


@pytest.fixture
def recipe_poulet() -> dict:
    """Recette de test poulet rôti."""
    return {
        "title": "Poulet rôti aux herbes de Provence",
        "ingredients": [
            "1 poulet entier",
            "3 gousses d'ail",
            "thym frais",
            "huile d'olive",
            "sel, poivre",
        ],
        "instructions": [
            "Préchauffez le four à 200°C.",
            "Badigeonnez le poulet d'huile.",
            "Enfournez 1h30.",
        ],
        "prep_time_min": 15,
        "cook_time_min": 90,
    }


# ── Tests tagging nominal ────────────────────────────────────────────────────

class TestTagRecipeNominal:
    """Tests du flow nominal de tagging avec mock Gemini."""

    @pytest.mark.asyncio
    async def test_tags_cuisines_correctement_mappees(self, recipe_poulet: dict) -> None:
        """La cuisine retournée par Gemini doit être conservée si dans VALID_CUISINES."""
        payload = {
            "cuisine": "française",
            "diet_tags": [],
            "time_category": "long",
            "difficulty": "facile",
            "budget": "moyen",
            "occasions": ["quotidien"],
            "raw_tags": ["poulet", "four"],
        }
        mock_client = _make_gemini_mock(payload)

        with patch(
            "src.agents.recipe_scout.tagger._get_gemini_client",
            return_value=mock_client,
        ):
            result = await tag_recipe(**recipe_poulet, api_key="fake-key")

        assert result.cuisine == "française"
        assert result.time_category == "long"
        assert result.difficulty == "facile"
        assert result.budget == "moyen"

    @pytest.mark.asyncio
    async def test_diet_tags_filtres_si_invalides(self, recipe_poulet: dict) -> None:
        """Les diet_tags hors VALID_DIETS doivent être filtrés silencieusement."""
        payload = {
            "cuisine": "française",
            "diet_tags": ["végétarien", "tag_invalide_xyz", "keto"],
            "time_category": "long",
            "difficulty": "facile",
            "budget": "moyen",
            "occasions": [],
            "raw_tags": [],
        }
        mock_client = _make_gemini_mock(payload)

        with patch(
            "src.agents.recipe_scout.tagger._get_gemini_client",
            return_value=mock_client,
        ):
            result = await tag_recipe(**recipe_poulet, api_key="fake-key")

        # "tag_invalide_xyz" doit être rejeté, les deux valides conservées
        assert "tag_invalide_xyz" not in result.diet_tags
        assert "végétarien" in result.diet_tags
        assert "keto" in result.diet_tags

    @pytest.mark.asyncio
    async def test_raw_tags_limites_a_5(self, recipe_poulet: dict) -> None:
        """Les raw_tags doivent être limités à 5 même si Gemini en retourne plus."""
        payload = {
            "cuisine": "française",
            "diet_tags": [],
            "time_category": "long",
            "difficulty": "facile",
            "budget": "moyen",
            "occasions": [],
            "raw_tags": ["a", "b", "c", "d", "e", "f", "g"],  # 7 tags
        }
        mock_client = _make_gemini_mock(payload)

        with patch(
            "src.agents.recipe_scout.tagger._get_gemini_client",
            return_value=mock_client,
        ):
            result = await tag_recipe(**recipe_poulet, api_key="fake-key")

        assert len(result.raw_tags) <= 5

    @pytest.mark.asyncio
    async def test_cuisine_invalide_fallback_internationale(self, recipe_poulet: dict) -> None:
        """Si Gemini retourne une cuisine hors liste, fallback sur 'internationale'."""
        payload = {
            "cuisine": "cuisine_inconnue_xyz",
            "diet_tags": [],
            "time_category": "normal",
            "difficulty": "moyen",
            "budget": "moyen",
            "occasions": [],
            "raw_tags": [],
        }
        mock_client = _make_gemini_mock(payload)

        with patch(
            "src.agents.recipe_scout.tagger._get_gemini_client",
            return_value=mock_client,
        ):
            result = await tag_recipe(**recipe_poulet, api_key="fake-key")

        assert result.cuisine == "internationale"

    @pytest.mark.asyncio
    async def test_json_invalide_retourne_fallback_tags(self, recipe_poulet: dict) -> None:
        """JSON non-parseable → fallback tags sans planter (résilience batch nocturne)."""
        mock_response = MagicMock()
        mock_response.text = "INVALID_JSON"

        mock_aio_models = MagicMock()
        mock_aio_models.generate_content = AsyncMock(return_value=mock_response)
        mock_aio = MagicMock()
        mock_aio.models = mock_aio_models
        mock_client = MagicMock()
        mock_client.aio = mock_aio

        with patch(
            "src.agents.recipe_scout.tagger._get_gemini_client",
            return_value=mock_client,
        ):
            result = await tag_recipe(**recipe_poulet, api_key="fake-key")

        # Fallback : valeurs par défaut conservatrices
        assert result.cuisine == "internationale"
        assert result.difficulty == "moyen"
        # Temps long car cook_time=90 > 60
        assert result.time_category == "long"


# ── Tests merge_tags_to_list ─────────────────────────────────────────────────

class TestMergeTagsToList:
    """Tests de la conversion RecipeTags → liste plate DB."""

    def test_format_prefixe_cuisine(self) -> None:
        """Les tags cuisine doivent avoir le préfixe 'cuisine:'."""
        tags = RecipeTags(cuisine="japonaise")
        result = merge_tags_to_list(tags)
        assert "cuisine:japonaise" in result

    def test_format_prefixe_regime(self) -> None:
        """Les diet_tags doivent avoir le préfixe 'regime:'."""
        tags = RecipeTags(cuisine="française", diet_tags=["végétarien", "sans_gluten"])
        result = merge_tags_to_list(tags)
        assert "regime:végétarien" in result
        assert "regime:sans_gluten" in result

    def test_format_prefixe_occasion(self) -> None:
        """Les occasions doivent avoir le préfixe 'occasion:'."""
        tags = RecipeTags(cuisine="française", occasions=["quotidien", "week_end"])
        result = merge_tags_to_list(tags)
        assert "occasion:quotidien" in result
        assert "occasion:week_end" in result

    def test_raw_tags_sans_prefixe(self) -> None:
        """Les raw_tags sont ajoutés sans préfixe."""
        tags = RecipeTags(cuisine="française", raw_tags=["cocorico", "terroir"])
        result = merge_tags_to_list(tags)
        assert "cocorico" in result
        assert "terroir" in result

    def test_tous_champs_obligatoires_presents(self) -> None:
        """Les 4 champs obligatoires (cuisine, temps, difficulte, budget) sont toujours là."""
        tags = RecipeTags()
        result = merge_tags_to_list(tags)
        assert any(t.startswith("cuisine:") for t in result)
        assert any(t.startswith("temps:") for t in result)
        assert any(t.startswith("difficulte:") for t in result)
        assert any(t.startswith("budget:") for t in result)
