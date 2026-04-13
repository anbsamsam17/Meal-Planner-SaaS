"""
Fixtures pytest pour les tests du worker MealPlanner.

Fixtures disponibles :
- sample_marmiton_html : HTML Marmiton simulé pour les tests de parsing
- sample_raw_recipe : RawRecipe de test avec données complètes
- mock_gemini_validation_response : mock du client Gemini pour les tests validation LLM
- mock_gemini_tagging_response : mock du client Gemini pour les tests tagging LLM

Swap Anthropic → Gemini (2026-04-12) : mock_anthropic_* remplacés par mock_gemini_*.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def sample_marmiton_html() -> str:
    """
    HTML Marmiton simulé représentant une page recette complète.

    Reproduit la structure HTML réelle de Marmiton pour tester
    les sélecteurs CSS du parser sans dépendance réseau.
    """
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head><title>Poulet rôti aux herbes - Marmiton</title></head>
    <body>
        <h1 class="RTEXT__title" itemprop="name">Poulet rôti aux herbes de Provence</h1>

        <div class="recipe-details">
            <span itemprop="prepTime" content="PT15M">15 min</span>
            <span itemprop="cookTime" content="PT1H30M">1h 30</span>
            <span itemprop="recipeYield">4 personnes</span>
            <span class="difficulty">Facile</span>
        </div>

        <span itemprop="ratingValue" content="4.5">4.5/5</span>

        <img itemprop="image" src="https://assets.marmiton.org/poulet-roti.jpg"
             alt="Poulet rôti aux herbes"/>

        <ul class="ingredient-list">
            <li itemprop="recipeIngredient" class="ingredient-item">1 poulet entier (environ 1,5 kg)</li>
            <li itemprop="recipeIngredient" class="ingredient-item">3 gousses d'ail</li>
            <li itemprop="recipeIngredient" class="ingredient-item">2 branches de thym frais</li>
            <li itemprop="recipeIngredient" class="ingredient-item">1 citron</li>
            <li itemprop="recipeIngredient" class="ingredient-item">3 cuillères à soupe d'huile d'olive</li>
            <li itemprop="recipeIngredient" class="ingredient-item">Sel et poivre noir du moulin</li>
        </ul>

        <div itemprop="recipeInstructions">
            <li class="preparation-step">
                Préchauffez le four à 200°C (thermostat 6-7). Sortez le poulet du réfrigérateur
                30 minutes avant la cuisson pour qu'il soit à température ambiante.
            </li>
            <li class="preparation-step">
                Épluchez et écrasez légèrement les gousses d'ail. Coupez le citron en quartiers.
                Effeuillez le thym ou laissez les branches entières.
            </li>
            <li class="preparation-step">
                Farcissez l'intérieur du poulet avec l'ail, le thym et les quartiers de citron.
                Badigeonnez l'extérieur avec l'huile d'olive, salez et poivrez généreusement.
            </li>
            <li class="preparation-step">
                Placez le poulet dans un plat à rôtir. Enfournez pour 1h30 en arrosant
                régulièrement avec le jus de cuisson toutes les 20 minutes.
            </li>
            <li class="preparation-step">
                Vérifiez la cuisson en piquant la cuisse : le jus doit être clair.
                Laissez reposer 10 minutes sous papier aluminium avant de servir.
            </li>
        </div>

        <div class="tags">
            <a class="tag-link" href="#">Poulet</a>
            <a class="tag-link" href="#">Four</a>
            <a class="tag-link" href="#">Facile</a>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_raw_recipe():
    """
    RawRecipe de test représentant une recette complète et valide.

    Utilisé pour tester la normalisation, l'embedding et la validation
    sans dépendance aux scrapers ou aux APIs externes.
    """
    from src.agents.recipe_scout.scrapers.base import RawRecipe

    return RawRecipe(
        title="Poulet rôti aux herbes de Provence",
        source_url="https://www.marmiton.org/recettes/recette_poulet-roti_12345.aspx",
        source_name="marmiton",
        ingredients_raw=[
            "1 poulet entier (environ 1,5 kg)",
            "3 gousses d'ail",
            "2 branches de thym frais",
            "1 citron",
            "3 cuillères à soupe d'huile d'olive",
            "Sel et poivre",
        ],
        instructions_raw=[
            "Préchauffez le four à 200°C.",
            "Épluchez et écrasez légèrement les gousses d'ail.",
            "Farcissez l'intérieur du poulet avec l'ail et le thym.",
            "Badigeonnez l'extérieur avec l'huile d'olive, salez et poivrez.",
            "Enfournez pour 1h30 en arrosant régulièrement.",
        ],
        prep_time_min=15,
        cook_time_min=90,
        servings=4,
        difficulty="easy",
        rating=4.5,
        cuisine_type="française",
        tags_raw=["poulet", "four", "facile"],
    )


@pytest.fixture
def mock_gemini_validation_response():
    """
    Mock d'une réponse Gemini pour la validation qualité.

    Simule response_schema structured output avec quality_score = 0.85.
    Remplace mock_anthropic_validation_response (outil tool_use) supprimé
    lors du swap Anthropic → Gemini (2026-04-12).

    Le mock cible client.aio.models.generate_content() (appel async Gemini).
    """
    import json

    payload = {
        "quality_score": 0.85,
        "issues": [],
        "rejection_reason": "",
        "completeness_score": 0.90,
        "coherence_score": 0.80,
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(payload)

    # Gemini SDK : client.aio.models.generate_content() est un coroutine
    mock_aio_models = MagicMock()
    mock_aio_models.generate_content = AsyncMock(return_value=mock_response)

    mock_aio = MagicMock()
    mock_aio.models = mock_aio_models

    mock_client = MagicMock()
    mock_client.aio = mock_aio

    return mock_client


@pytest.fixture
def mock_gemini_tagging_response():
    """
    Mock d'une réponse Gemini pour le tagging de recette.

    Simule response_schema structured output avec les tags attendus.
    Remplace mock_anthropic_tagging_response supprimé lors du swap (2026-04-12).
    """
    import json

    payload = {
        "cuisine": "française",
        "diet_tags": [],
        "time_category": "long",
        "difficulty": "facile",
        "budget": "moyen",
        "occasions": ["quotidien", "week_end"],
        "raw_tags": ["poulet", "four"],
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(payload)

    mock_aio_models = MagicMock()
    mock_aio_models.generate_content = AsyncMock(return_value=mock_response)

    mock_aio = MagicMock()
    mock_aio.models = mock_aio_models

    mock_client = MagicMock()
    mock_client.aio = mock_aio

    return mock_client
