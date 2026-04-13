"""
Tests du scraper Allrecipes.

Stratégie :
- Fixtures JSON-LD locales (approche prioritaire Allrecipes)
- Tests du mapping cuisine_type international
- Tests des cas d'erreur (JSON-LD malformé, absent)

Architecture AAA (Arrange → Act → Assert).
"""

import json
import pytest

from src.agents.recipe_scout.scrapers.allrecipes import (
    AllRecipesScraper,
    parse_allrecipes_page,
    _map_cuisine,
    _parse_time_iso,
    _extract_jsonld_recipe,
    _parse_servings,
)
from src.agents.recipe_scout.scrapers.base import RawRecipe
from bs4 import BeautifulSoup


# ---- Fixtures JSON-LD Allrecipes ----

ALLRECIPES_JSONLD_CHICKEN_TIKKA = {
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Chicken Tikka Masala",
    "prepTime": "PT20M",
    "cookTime": "PT30M",
    "recipeYield": "4 servings",
    "recipeCuisine": "Indian",
    "recipeCategory": ["Main Dish", "Chicken"],
    "keywords": "chicken, tikka, masala, curry, indian",
    "recipeIngredient": [
        "2 pounds skinless, boneless chicken breast halves",
        "1 cup yogurt",
        "2 tablespoons lemon juice",
        "2 teaspoons ground cumin",
        "2 teaspoons ground cinnamon",
        "2 teaspoons cayenne pepper",
        "2 tablespoons butter",
        "1 (28 ounce) can crushed tomatoes",
        "1 cup heavy cream",
    ],
    "recipeInstructions": [
        {
            "@type": "HowToStep",
            "text": "In a bowl, combine yogurt, lemon juice, cumin, cinnamon and cayenne pepper.",
        },
        {
            "@type": "HowToStep",
            "text": "Stir in the chicken, cover and marinate for at least 1 hour in refrigerator.",
        },
        {
            "@type": "HowToStep",
            "text": "Grill chicken until cooked through, about 5 minutes on each side.",
        },
        {
            "@type": "HowToStep",
            "text": "Melt butter in a skillet over medium heat. Add tomato sauce and cream.",
        },
        {
            "@type": "HowToStep",
            "text": "Add grilled chicken pieces and simmer for 10 minutes.",
        },
    ],
    "image": [
        {"@type": "ImageObject", "url": "https://www.allrecipes.com/chicken-tikka.jpg"}
    ],
    "aggregateRating": {"ratingValue": "4.8", "ratingCount": "12450"},
}

ALLRECIPES_JSONLD_PASTA = {
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Classic Spaghetti Carbonara",
    "prepTime": "PT10M",
    "cookTime": "PT20M",
    "recipeYield": ["6"],
    "recipeCuisine": "Italian",
    "recipeIngredient": [
        "1 pound spaghetti",
        "4 ounces pancetta",
        "4 large eggs",
        "1 cup grated Parmesan cheese",
        "1/2 cup grated Romano cheese",
        "2 cloves garlic",
        "Salt and black pepper",
    ],
    "recipeInstructions": "Cook spaghetti. Fry pancetta with garlic. Beat eggs with cheese. Combine all ingredients.",
    "aggregateRating": {"ratingValue": "4.6"},
}


@pytest.fixture
def html_chicken_tikka() -> str:
    """HTML Allrecipes avec JSON-LD Chicken Tikka Masala."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Chicken Tikka Masala - Allrecipes</title>
    <script type="application/ld+json">{json.dumps(ALLRECIPES_JSONLD_CHICKEN_TIKKA)}</script>
</head>
<body>
    <h1 class="article-heading">Chicken Tikka Masala</h1>
</body>
</html>"""


@pytest.fixture
def html_carbonara() -> str:
    """HTML Allrecipes avec JSON-LD Carbonara (instructions en chaîne simple)."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Spaghetti Carbonara - Allrecipes</title>
    <script type="application/ld+json">{json.dumps(ALLRECIPES_JSONLD_PASTA)}</script>
</head>
<body></body>
</html>"""


@pytest.fixture
def html_no_jsonld() -> str:
    """HTML Allrecipes sans JSON-LD."""
    return """<!DOCTYPE html>
<html lang="en">
<body>
    <h1 class="article-heading">Simple Salad</h1>
    <ul class="mntl-structured-ingredients__list">
        <li class="mntl-structured-ingredients__list-item">Lettuce</li>
        <li class="mntl-structured-ingredients__list-item">Tomatoes</li>
        <li class="mntl-structured-ingredients__list-item">Cucumber</li>
    </ul>
    <ol class="mntl-sc-block-group--OL">
        <li>Wash and chop the vegetables.</li>
        <li>Mix in a bowl and serve with dressing.</li>
    </ol>
</body>
</html>"""


# ---- Tests _map_cuisine ----

class TestMapCuisine:
    """Tests du mapping des types de cuisine."""

    def test_indian_vers_indienne(self) -> None:
        assert _map_cuisine("Indian") == "indienne"

    def test_italian_vers_italienne(self) -> None:
        assert _map_cuisine("Italian") == "italienne"

    def test_mexican_vers_mexicaine(self) -> None:
        assert _map_cuisine("Mexican") == "mexicaine"

    def test_french_vers_française(self) -> None:
        assert _map_cuisine("French") == "française"

    def test_liste_prend_premier_element(self) -> None:
        assert _map_cuisine(["Italian", "Pasta"]) == "italienne"

    def test_none_retourne_none(self) -> None:
        assert _map_cuisine(None) is None

    def test_cuisine_inconnue_conservee(self) -> None:
        # Les cuisines non mappées sont conservées telles quelles
        result = _map_cuisine("Ethiopian")
        assert result == "Ethiopian"


# ---- Tests _parse_servings ----

class TestParseServings:
    """Tests de l'extraction du nombre de portions."""

    def test_entier_direct(self) -> None:
        assert _parse_servings(4) == 4

    def test_chaine_avec_texte(self) -> None:
        assert _parse_servings("6 servings") == 6

    def test_liste_avec_chaine(self) -> None:
        assert _parse_servings(["6"]) == 6

    def test_none(self) -> None:
        assert _parse_servings(None) is None


# ---- Tests parsing JSON-LD Allrecipes ----

class TestParseAllrecipesJsonLd:
    """Tests du parsing JSON-LD Allrecipes avec cuisine internationale."""

    def test_titre_chicken_tikka(self, html_chicken_tikka: str) -> None:
        recipe = parse_allrecipes_page(html_chicken_tikka, "https://www.allrecipes.com/recipe/45345/chicken-tikka-masala/")
        assert recipe is not None
        assert recipe.title == "Chicken Tikka Masala"

    def test_cuisine_type_mappee_vers_francais(self, html_chicken_tikka: str) -> None:
        """Le type de cuisine doit être mappé vers le format français."""
        recipe = parse_allrecipes_page(html_chicken_tikka, "https://www.allrecipes.com/recipe/45345/")
        assert recipe is not None
        assert recipe.cuisine_type == "indienne"

    def test_ingredients_extraits(self, html_chicken_tikka: str) -> None:
        recipe = parse_allrecipes_page(html_chicken_tikka, "https://www.allrecipes.com/recipe/45345/")
        assert recipe is not None
        assert len(recipe.ingredients_raw) == 9

    def test_instructions_howto_step(self, html_chicken_tikka: str) -> None:
        """Les instructions HowToStep doivent être dépaquetées."""
        recipe = parse_allrecipes_page(html_chicken_tikka, "https://www.allrecipes.com/recipe/45345/")
        assert recipe is not None
        assert len(recipe.instructions_raw) == 5
        assert "yogurt" in recipe.instructions_raw[0].lower()

    def test_temps_preparation(self, html_chicken_tikka: str) -> None:
        recipe = parse_allrecipes_page(html_chicken_tikka, "https://www.allrecipes.com/recipe/45345/")
        assert recipe is not None
        assert recipe.prep_time_min == 20
        assert recipe.cook_time_min == 30

    def test_portions(self, html_chicken_tikka: str) -> None:
        recipe = parse_allrecipes_page(html_chicken_tikka, "https://www.allrecipes.com/recipe/45345/")
        assert recipe is not None
        assert recipe.servings == 4

    def test_note(self, html_chicken_tikka: str) -> None:
        recipe = parse_allrecipes_page(html_chicken_tikka, "https://www.allrecipes.com/recipe/45345/")
        assert recipe is not None
        assert recipe.rating == pytest.approx(4.8, 0.01)

    def test_tags_depuis_keywords_et_categories(self, html_chicken_tikka: str) -> None:
        recipe = parse_allrecipes_page(html_chicken_tikka, "https://www.allrecipes.com/recipe/45345/")
        assert recipe is not None
        assert len(recipe.tags_raw) > 0
        # Keywords et categories doivent être fusionnés
        all_tags = " ".join(recipe.tags_raw).lower()
        assert "chicken" in all_tags or "main dish" in all_tags

    def test_source_name(self, html_chicken_tikka: str) -> None:
        recipe = parse_allrecipes_page(html_chicken_tikka, "https://www.allrecipes.com/recipe/45345/")
        assert recipe is not None
        assert recipe.source_name == "allrecipes"

    def test_instructions_en_chaine_simple(self, html_carbonara: str) -> None:
        """Les instructions en chaîne simple doivent être traitées."""
        recipe = parse_allrecipes_page(html_carbonara, "https://www.allrecipes.com/recipe/11691/")
        assert recipe is not None
        assert len(recipe.instructions_raw) == 1  # Une seule chaîne

    def test_portions_depuis_liste(self, html_carbonara: str) -> None:
        """Les portions depuis une liste JSON-LD doivent être extraites."""
        recipe = parse_allrecipes_page(html_carbonara, "https://www.allrecipes.com/recipe/11691/")
        assert recipe is not None
        assert recipe.servings == 6


# ---- Tests fallback CSS ----

class TestAllrecipesFallbackCss:
    """Tests du fallback CSS Allrecipes."""

    def test_fallback_titre(self, html_no_jsonld: str) -> None:
        recipe = parse_allrecipes_page(html_no_jsonld, "https://www.allrecipes.com/recipe/99/")
        assert recipe is not None
        assert "Salad" in recipe.title

    def test_fallback_ingredients(self, html_no_jsonld: str) -> None:
        recipe = parse_allrecipes_page(html_no_jsonld, "https://www.allrecipes.com/recipe/99/")
        assert recipe is not None
        assert len(recipe.ingredients_raw) >= 2


# ---- Tests cas limites ----

class TestAllrecipesCasLimites:
    """Tests des cas d'erreur."""

    def test_page_vide_retourne_none(self) -> None:
        recipe = parse_allrecipes_page("<html><body></body></html>", "https://example.com")
        assert recipe is None

    def test_scraper_is_valid(self) -> None:
        scraper = AllRecipesScraper()
        recette = RawRecipe(
            title="Test",
            source_url="https://allrecipes.com/recipe/1",
            source_name="allrecipes",
            ingredients_raw=["ing1", "ing2", "ing3"],
            instructions_raw=["step 1", "step 2"],
        )
        assert scraper.is_valid_raw_recipe(recette) is True

    def test_jsonld_absent_type_incorrect(self) -> None:
        """JSON-LD d'un autre type (@type: WebPage) ne doit pas être parsé comme recette."""
        html = """<html><head>
            <script type="application/ld+json">{"@type": "WebPage", "name": "Test"}</script>
        </head><body></body></html>"""
        recipe = parse_allrecipes_page(html, "https://example.com")
        assert recipe is None
