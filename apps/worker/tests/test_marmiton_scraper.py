"""
Tests du scraper Marmiton sur HTML mocké.

Ces tests valident les sélecteurs CSS et la logique de parsing
sans dépendance réseau. Ils utilisent le HTML de la fixture `sample_marmiton_html`.

Couverture :
- Extraction du titre
- Extraction des ingrédients
- Extraction des instructions
- Parsing des temps (ISO 8601, format humain)
- Parsing de la difficulté
- Cas limites (page sans titre, page sans ingrédients)
"""

import pytest

from src.agents.recipe_scout.scrapers.marmiton import (
    MarmitonScraper,
    parse_marmiton_page,
    _parse_time_minutes,
    _parse_difficulty,
)
from src.agents.recipe_scout.scrapers.base import RawRecipe, BaseRecipeScraper


class TestParseTimeMintes:
    """Tests pour le parsing des temps de cuisson."""

    def test_parse_iso_8601_minutes_only(self):
        """
        Parse le format ISO 8601 avec minutes uniquement.

        Arrange : "PT30M"
        Act : _parse_time_minutes
        Assert : 30
        """
        result = _parse_time_minutes("PT30M")

        assert result == 30

    def test_parse_iso_8601_hours_and_minutes(self):
        """
        Parse le format ISO 8601 avec heures et minutes.

        Arrange : "PT1H30M"
        Act : _parse_time_minutes
        Assert : 90
        """
        result = _parse_time_minutes("PT1H30M")

        assert result == 90

    def test_parse_french_format_hm(self):
        """
        Parse le format français "1h30".

        Arrange : "1h30"
        Act : _parse_time_minutes
        Assert : 90
        """
        result = _parse_time_minutes("1h30")

        assert result == 90

    def test_parse_french_format_minutes(self):
        """
        Parse le format "45 min".

        Arrange : "45 min"
        Act : _parse_time_minutes
        Assert : 45
        """
        result = _parse_time_minutes("45 min")

        assert result == 45

    def test_parse_none_returns_none(self):
        """
        None en entrée retourne None.

        Arrange : None
        Act : _parse_time_minutes
        Assert : None
        """
        result = _parse_time_minutes(None)

        assert result is None

    def test_parse_empty_string_returns_none(self):
        """
        Chaîne vide retourne None.

        Arrange : ""
        Act : _parse_time_minutes
        Assert : None
        """
        result = _parse_time_minutes("")

        assert result is None


class TestParseDifficulty:
    """Tests pour le parsing de la difficulté."""

    def test_parse_facile(self):
        """
        Normalise 'Facile' vers 'easy'.

        Arrange : "Facile"
        Act : _parse_difficulty
        Assert : "easy"
        """
        result = _parse_difficulty("Facile")

        assert result == "easy"

    def test_parse_tres_facile(self):
        """
        Normalise 'Très facile' vers 'very_easy'.

        Arrange : "Très facile"
        Act : _parse_difficulty
        Assert : "very_easy"
        """
        result = _parse_difficulty("Très facile")

        assert result == "very_easy"

    def test_parse_niveau_moyen(self):
        """
        Normalise 'Niveau moyen' vers 'medium'.

        Arrange : "Niveau moyen"
        Act : _parse_difficulty
        Assert : "medium"
        """
        result = _parse_difficulty("Niveau moyen")

        assert result == "medium"

    def test_parse_none_returns_none(self):
        """
        None en entrée retourne None.

        Arrange : None
        Act : _parse_difficulty
        Assert : None
        """
        result = _parse_difficulty(None)

        assert result is None


class TestParseMarmitonPage:
    """Tests pour le parser HTML de pages Marmiton."""

    def test_parse_extracts_title(self, sample_marmiton_html):
        """
        Extrait correctement le titre de la recette.

        Arrange : HTML Marmiton avec h1.RTEXT__title.
        Act : parse_marmiton_page.
        Assert : titre correct.
        """
        result = parse_marmiton_page(
            sample_marmiton_html,
            "https://www.marmiton.org/recettes/recette_poulet-roti_12345.aspx",
        )

        assert result is not None
        assert "Poulet rôti" in result.title

    def test_parse_extracts_ingredients(self, sample_marmiton_html):
        """
        Extrait la liste des ingrédients.

        Arrange : HTML avec 6 ingrédients listés.
        Act : parse_marmiton_page.
        Assert : au moins 3 ingrédients extraits.
        """
        result = parse_marmiton_page(
            sample_marmiton_html,
            "https://www.marmiton.org/recettes/recette_poulet-roti_12345.aspx",
        )

        assert result is not None
        assert len(result.ingredients_raw) >= 3

    def test_parse_extracts_instructions(self, sample_marmiton_html):
        """
        Extrait les étapes de préparation.

        Arrange : HTML avec 5 étapes de préparation.
        Act : parse_marmiton_page.
        Assert : au moins 2 étapes extraites.
        """
        result = parse_marmiton_page(
            sample_marmiton_html,
            "https://www.marmiton.org/recettes/recette_poulet-roti_12345.aspx",
        )

        assert result is not None
        assert len(result.instructions_raw) >= 2

    def test_parse_extracts_cook_time(self, sample_marmiton_html):
        """
        Extrait le temps de cuisson au format ISO 8601.

        Arrange : HTML avec cookTime="PT1H30M".
        Act : parse_marmiton_page.
        Assert : cook_time_min=90.
        """
        result = parse_marmiton_page(
            sample_marmiton_html,
            "https://www.marmiton.org/recettes/recette_poulet-roti_12345.aspx",
        )

        assert result is not None
        assert result.cook_time_min == 90

    def test_parse_extracts_prep_time(self, sample_marmiton_html):
        """
        Extrait le temps de préparation.

        Arrange : HTML avec prepTime="PT15M".
        Act : parse_marmiton_page.
        Assert : prep_time_min=15.
        """
        result = parse_marmiton_page(
            sample_marmiton_html,
            "https://www.marmiton.org/recettes/recette_poulet-roti_12345.aspx",
        )

        assert result is not None
        assert result.prep_time_min == 15

    def test_parse_extracts_servings(self, sample_marmiton_html):
        """
        Extrait le nombre de portions.

        Arrange : HTML avec recipeYield="4 personnes".
        Act : parse_marmiton_page.
        Assert : servings=4.
        """
        result = parse_marmiton_page(
            sample_marmiton_html,
            "https://www.marmiton.org/recettes/recette_poulet-roti_12345.aspx",
        )

        assert result is not None
        assert result.servings == 4

    def test_parse_page_without_title_returns_none(self):
        """
        Retourne None si la page n'a pas de titre de recette.

        Simule une page d'erreur ou de listing sans recette.

        Arrange : HTML sans h1.RTEXT__title.
        Act : parse_marmiton_page.
        Assert : None.
        """
        html = "<html><body><h1>Page d'accueil Marmiton</h1></body></html>"

        result = parse_marmiton_page(html, "https://www.marmiton.org/")

        assert result is None

    def test_parse_sets_source_name(self, sample_marmiton_html):
        """
        La source_name est toujours 'marmiton'.

        Permet l'attribution des recettes à leur source d'origine.

        Arrange : HTML Marmiton quelconque.
        Act : parse_marmiton_page.
        Assert : source_name="marmiton".
        """
        result = parse_marmiton_page(
            sample_marmiton_html,
            "https://www.marmiton.org/recettes/recette_poulet-roti_12345.aspx",
        )

        assert result is not None
        assert result.source_name == "marmiton"

    def test_parse_sets_source_url(self, sample_marmiton_html):
        """
        L'URL de la page est correctement stockée dans source_url.

        Arrange : URL spécifique passée à parse_marmiton_page.
        Act : parse_marmiton_page.
        Assert : source_url = URL passée en paramètre.
        """
        url = "https://www.marmiton.org/recettes/recette_poulet-roti_12345.aspx"
        result = parse_marmiton_page(sample_marmiton_html, url)

        assert result is not None
        assert result.source_url == url


class TestBaseRecipeScraper:
    """Tests pour la classe abstraite BaseRecipeScraper."""

    def test_is_valid_raw_recipe_rejects_no_title(self):
        """
        is_valid_raw_recipe rejette une recette sans titre.

        Arrange : RawRecipe avec titre vide.
        Act : is_valid_raw_recipe.
        Assert : False.
        """
        scraper = MarmitonScraper()
        recipe = RawRecipe(
            title="",
            source_url="https://example.com",
            source_name="test",
            ingredients_raw=["200g farine", "2 oeufs"],
            instructions_raw=["Mélanger."],
        )

        assert scraper.is_valid_raw_recipe(recipe) is False

    def test_is_valid_raw_recipe_rejects_no_ingredients(self):
        """
        is_valid_raw_recipe rejette une recette sans ingrédients.

        Arrange : RawRecipe avec liste d'ingrédients vide.
        Act : is_valid_raw_recipe.
        Assert : False.
        """
        scraper = MarmitonScraper()
        recipe = RawRecipe(
            title="Gâteau mystère",
            source_url="https://example.com",
            source_name="test",
            ingredients_raw=[],
            instructions_raw=["Mélanger.", "Cuire."],
        )

        assert scraper.is_valid_raw_recipe(recipe) is False

    def test_is_valid_raw_recipe_accepts_complete_recipe(self, sample_raw_recipe):
        """
        is_valid_raw_recipe accepte une recette complète.

        Arrange : RawRecipe avec titre, ingrédients et instructions.
        Act : is_valid_raw_recipe.
        Assert : True.
        """
        scraper = MarmitonScraper()

        assert scraper.is_valid_raw_recipe(sample_raw_recipe) is True
