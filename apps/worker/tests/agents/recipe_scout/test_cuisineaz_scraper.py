"""
Tests du scraper 750g (CuisineAz).

Stratégie :
- Fixtures HTML locales pour les tests sans dépendance réseau
- Tester parsing JSON-LD (approche prioritaire) et fallback CSS
- Tester les cas limites (JSON-LD absent, champs manquants)

Architecture AAA (Arrange → Act → Assert).
"""

import json
import pytest

# FIX : la fonction s'appelle _extract_from_jsonld dans cuisine_az.py (pas _extract_jsonld_recipe)
from src.agents.recipe_scout.scrapers.cuisine_az import (
    CuisineAzScraper,
    parse_cuisine_az_page,
    _parse_time_iso,
    _parse_difficulty_fr,
    _extract_from_jsonld as _extract_jsonld_recipe,
)
from src.agents.recipe_scout.scrapers.base import RawRecipe

from bs4 import BeautifulSoup


# ---- Fixtures HTML locales ----

JSONLD_RECIPE_DATA = {
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Gratin dauphinois traditionnel",
    "prepTime": "PT20M",
    "cookTime": "PT1H",
    "recipeYield": "6 personnes",
    "recipeIngredient": [
        "1 kg de pommes de terre",
        "50 cl de crème fraîche",
        "25 cl de lait",
        "1 gousse d'ail",
        "Noix de muscade",
        "Sel et poivre",
    ],
    "recipeInstructions": [
        {"@type": "HowToStep", "text": "Épluchez et tranchez finement les pommes de terre."},
        {"@type": "HowToStep", "text": "Frottez le plat avec la gousse d'ail coupée en deux."},
        {"@type": "HowToStep", "text": "Disposez les tranches de pommes de terre en couches."},
        {"@type": "HowToStep", "text": "Versez le mélange crème-lait sur les pommes de terre."},
        {"@type": "HowToStep", "text": "Enfournez à 180°C pendant 1 heure jusqu'à dorure."},
    ],
    "image": "https://cdn.750g.com/gratin-dauphinois.jpg",
    "aggregateRating": {"ratingValue": "4.7", "ratingCount": "245"},
    "keywords": "gratin, pommes de terre, dauphinois, plat du soir",
    "recipeCuisine": "française",
    "difficulty": "Facile",
}


@pytest.fixture
def html_with_jsonld() -> str:
    """HTML 750g avec JSON-LD complet."""
    jsonld_str = json.dumps(JSONLD_RECIPE_DATA)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <title>Gratin dauphinois traditionnel - 750g</title>
    <script type="application/ld+json">{jsonld_str}</script>
</head>
<body>
    <h1 class="recipe-title">Gratin dauphinois traditionnel</h1>
</body>
</html>"""


@pytest.fixture
def html_without_jsonld() -> str:
    """HTML 750g sans JSON-LD — force le fallback CSS."""
    return """<!DOCTYPE html>
<html lang="fr">
<head><title>Soupe à l'oignon - 750g</title></head>
<body>
    <h1 class="main-title" itemprop="name">Soupe à l'oignon gratinée</h1>

    <span itemprop="prepTime" content="PT15M">15 min</span>
    <span itemprop="cookTime" content="PT45M">45 min</span>
    <span itemprop="recipeYield">4 personnes</span>
    <span class="difficulty-level">Facile</span>

    <ul>
        <li itemprop="recipeIngredient" class="ingredient-item">4 gros oignons</li>
        <li itemprop="recipeIngredient" class="ingredient-item">50 g de beurre</li>
        <li itemprop="recipeIngredient" class="ingredient-item">1 litre de bouillon de bœuf</li>
        <li itemprop="recipeIngredient" class="ingredient-item">4 tranches de pain</li>
        <li itemprop="recipeIngredient" class="ingredient-item">100 g de gruyère râpé</li>
    </ul>

    <div itemprop="recipeInstructions">
        <li class="preparation-step">Émincez finement les oignons et faites-les revenir dans le beurre.</li>
        <li class="preparation-step">Ajoutez le bouillon chaud et laissez mijoter 30 minutes.</li>
        <li class="preparation-step">Versez la soupe dans des bols, ajoutez le pain et le fromage.</li>
        <li class="preparation-step">Passez sous le grill 5 minutes jusqu'à gratinage.</li>
    </div>
</body>
</html>"""


@pytest.fixture
def html_empty() -> str:
    """HTML sans recette — doit retourner None."""
    return """<!DOCTYPE html>
<html><head><title>Page d'accueil 750g</title></head>
<body><p>Bienvenue sur 750g</p></body>
</html>"""


# ---- Tests _parse_time_iso ----

class TestParseTimeIso:
    """Tests de la fonction _parse_time_iso."""

    def test_iso_heures_minutes(self) -> None:
        """Teste le parsing ISO 8601 PT1H30M."""
        # Arrange
        time_str = "PT1H30M"
        # Act
        result = _parse_time_iso(time_str)
        # Assert
        assert result == 90

    def test_iso_minutes_seulement(self) -> None:
        """Teste le parsing ISO 8601 PT45M."""
        assert _parse_time_iso("PT45M") == 45

    def test_format_h_min(self) -> None:
        """Teste le format '1h30'."""
        assert _parse_time_iso("1h30") == 90

    def test_format_minutes(self) -> None:
        """Teste le format '20 min'."""
        assert _parse_time_iso("20 min") == 20

    def test_valeur_none(self) -> None:
        """None doit retourner None."""
        assert _parse_time_iso(None) is None

    def test_chaine_vide(self) -> None:
        """Chaîne vide doit retourner None."""
        assert _parse_time_iso("") is None


# ---- Tests _parse_difficulty_fr ----

class TestParseDifficultyFr:
    """Tests du mapping de difficulté."""

    def test_facile(self) -> None:
        assert _parse_difficulty_fr("Facile") == "easy"

    def test_tres_facile(self) -> None:
        assert _parse_difficulty_fr("Très facile") == "very_easy"

    def test_moyen(self) -> None:
        assert _parse_difficulty_fr("Moyen") == "medium"

    def test_difficile(self) -> None:
        assert _parse_difficulty_fr("Difficile") == "hard"

    def test_none(self) -> None:
        assert _parse_difficulty_fr(None) is None

    def test_casse_insensible(self) -> None:
        assert _parse_difficulty_fr("FACILE") == "easy"


# ---- Tests parsing JSON-LD ----

class TestParseFromJsonLd:
    """Tests du parsing JSON-LD 750g."""

    def test_parse_jsonld_titre(self, html_with_jsonld: str) -> None:
        """Le titre doit être extrait depuis JSON-LD."""
        recipe = parse_cuisine_az_page(html_with_jsonld, "https://www.750g.com/gratin-dauphinois")
        assert recipe is not None
        assert recipe.title == "Gratin dauphinois traditionnel"

    def test_parse_jsonld_ingredients(self, html_with_jsonld: str) -> None:
        """Les ingrédients doivent être extraits."""
        recipe = parse_cuisine_az_page(html_with_jsonld, "https://www.750g.com/gratin-dauphinois")
        assert recipe is not None
        assert len(recipe.ingredients_raw) == 6
        assert any("pommes de terre" in ing for ing in recipe.ingredients_raw)

    def test_parse_jsonld_instructions(self, html_with_jsonld: str) -> None:
        """Les instructions doivent être extraites depuis HowToStep."""
        recipe = parse_cuisine_az_page(html_with_jsonld, "https://www.750g.com/gratin-dauphinois")
        assert recipe is not None
        assert len(recipe.instructions_raw) == 5
        assert "pommes de terre" in recipe.instructions_raw[0].lower()

    def test_parse_jsonld_temps(self, html_with_jsonld: str) -> None:
        """Les temps doivent être convertis en minutes."""
        recipe = parse_cuisine_az_page(html_with_jsonld, "https://www.750g.com/gratin-dauphinois")
        assert recipe is not None
        assert recipe.prep_time_min == 20
        assert recipe.cook_time_min == 60

    def test_parse_jsonld_portions(self, html_with_jsonld: str) -> None:
        """Les portions doivent être extraites."""
        recipe = parse_cuisine_az_page(html_with_jsonld, "https://www.750g.com/gratin-dauphinois")
        assert recipe is not None
        assert recipe.servings == 6

    def test_parse_jsonld_source(self, html_with_jsonld: str) -> None:
        """Le nom de source doit être '750g'."""
        recipe = parse_cuisine_az_page(html_with_jsonld, "https://www.750g.com/gratin-dauphinois")
        assert recipe is not None
        assert recipe.source_name == "750g"

    def test_parse_jsonld_rating(self, html_with_jsonld: str) -> None:
        """La note doit être extraite."""
        recipe = parse_cuisine_az_page(html_with_jsonld, "https://www.750g.com/gratin-dauphinois")
        assert recipe is not None
        assert recipe.rating == pytest.approx(4.7, 0.01)

    def test_parse_jsonld_tags(self, html_with_jsonld: str) -> None:
        """Les tags doivent être extraits depuis les keywords."""
        recipe = parse_cuisine_az_page(html_with_jsonld, "https://www.750g.com/gratin-dauphinois")
        assert recipe is not None
        assert "gratin" in recipe.tags_raw


# ---- Tests fallback CSS ----

class TestParseFromCss:
    """Tests du fallback CSS 750g (sans JSON-LD)."""

    def test_fallback_titre(self, html_without_jsonld: str) -> None:
        """Le titre doit être extrait depuis le HTML CSS."""
        recipe = parse_cuisine_az_page(html_without_jsonld, "https://www.750g.com/soupe-oignon")
        assert recipe is not None
        assert "Soupe" in recipe.title

    def test_fallback_ingredients(self, html_without_jsonld: str) -> None:
        """Les ingrédients doivent être extraits via CSS."""
        recipe = parse_cuisine_az_page(html_without_jsonld, "https://www.750g.com/soupe-oignon")
        assert recipe is not None
        assert len(recipe.ingredients_raw) >= 3

    def test_fallback_instructions(self, html_without_jsonld: str) -> None:
        """Les instructions doivent être extraites via CSS."""
        recipe = parse_cuisine_az_page(html_without_jsonld, "https://www.750g.com/soupe-oignon")
        assert recipe is not None
        assert len(recipe.instructions_raw) >= 2

    def test_fallback_temps(self, html_without_jsonld: str) -> None:
        """Les temps doivent être extraits depuis les attributs itemprop."""
        recipe = parse_cuisine_az_page(html_without_jsonld, "https://www.750g.com/soupe-oignon")
        assert recipe is not None
        assert recipe.prep_time_min == 15
        assert recipe.cook_time_min == 45


# ---- Tests cas limites ----

class TestCasLimites:
    """Tests des cas d'erreur et cas limites."""

    def test_page_sans_recette_retourne_none(self, html_empty: str) -> None:
        """Une page sans recette doit retourner None."""
        recipe = parse_cuisine_az_page(html_empty, "https://www.750g.com/")
        assert recipe is None

    def test_scraper_is_valid_raw_recipe(self) -> None:
        """is_valid_raw_recipe doit rejeter les recettes incomplètes."""
        scraper = CuisineAzScraper()

        recette_complete = RawRecipe(
            title="Test",
            source_url="https://example.com",
            source_name="750g",
            ingredients_raw=["ing1", "ing2"],
            instructions_raw=["étape 1"],
        )
        assert scraper.is_valid_raw_recipe(recette_complete) is True

        recette_sans_titre = RawRecipe(
            title="",
            source_url="https://example.com",
            source_name="750g",
            ingredients_raw=["ing1"],
            instructions_raw=["étape 1"],
        )
        assert scraper.is_valid_raw_recipe(recette_sans_titre) is False

        recette_sans_ingredients = RawRecipe(
            title="Test",
            source_url="https://example.com",
            source_name="750g",
            ingredients_raw=[],
            instructions_raw=["étape 1"],
        )
        assert scraper.is_valid_raw_recipe(recette_sans_ingredients) is False

    def test_extract_jsonld_graph_wrapper(self) -> None:
        """Doit extraire la recette depuis un @graph JSON-LD."""
        graph_data = {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebPage", "name": "Page"},
                {"@type": "Recipe", "name": "Test recette", "recipeIngredient": []},
            ],
        }
        html = f"""<html><head>
            <script type="application/ld+json">{json.dumps(graph_data)}</script>
        </head><body></body></html>"""
        soup = BeautifulSoup(html, "lxml")
        result = _extract_jsonld_recipe(soup)
        assert result is not None
        assert result.get("name") == "Test recette"
