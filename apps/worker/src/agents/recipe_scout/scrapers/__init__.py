"""
Package scrapers — registre des spiders de recettes RECIPE_SCOUT.

Chaque scraper hérite de BaseRecipeScraper et implémente :
- scrape_url(url) -> RawRecipe | None
- get_listing_urls(max_pages) -> list[str]

Le registre AVAILABLE_SCRAPERS permet à l'agent RECIPE_SCOUT de
choisir dynamiquement le scraper selon la source configurée.

Usage :
    from src.agents.recipe_scout.scrapers import AVAILABLE_SCRAPERS

    scraper_class = AVAILABLE_SCRAPERS["marmiton"]
    scraper = scraper_class()
    recipe = scraper.scrape_url("https://www.marmiton.org/recettes/...")
"""

from src.agents.recipe_scout.scrapers.allrecipes import AllRecipesScraper, AllRecipesSpider
from src.agents.recipe_scout.scrapers.base import BaseRecipeScraper, RawRecipe
from src.agents.recipe_scout.scrapers.cuisine_az import CuisineAzScraper, CuisineAzSpider
from src.agents.recipe_scout.scrapers.marmiton import MarmitonScraper, MarmitonSpider

# Registre des scrapers disponibles
# Clé : identifiant source (utilisé dans la config agent)
# Valeur : classe scraper (pas le spider Scrapy — pour les tests unitaires)
AVAILABLE_SCRAPERS: dict[str, type[BaseRecipeScraper]] = {
    "marmiton": MarmitonScraper,
    "750g": CuisineAzScraper,
    "allrecipes": AllRecipesScraper,
}

# Registre des spiders Scrapy (pour le batch nocturne Celery)
AVAILABLE_SPIDERS = {
    "marmiton": MarmitonSpider,
    "750g": CuisineAzSpider,
    "allrecipes": AllRecipesSpider,
}

__all__ = [
    "AVAILABLE_SCRAPERS",
    "AVAILABLE_SPIDERS",
    "AllRecipesScraper",
    "AllRecipesSpider",
    "BaseRecipeScraper",
    "CuisineAzScraper",
    "CuisineAzSpider",
    "MarmitonScraper",
    "MarmitonSpider",
    "RawRecipe",
]
