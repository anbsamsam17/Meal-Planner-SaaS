"""
Spider Scrapy pour Allrecipes.com — source internationale de recettes.

Allrecipes est l'une des plus grandes bases de recettes mondiales.
La stratégie de parsing privilégie le JSON-LD schema.org/Recipe
qui est systématiquement présent dans les pages Allrecipes,
garantissant la fiabilité du scraping.

Positionnement dans le ROADMAP :
- Source internationale (mexicain, italien, indien, asiatique...)
- Mapping vers cuisine_type pour le filtrage WEEKLY_PLANNER
- Complément indispensable aux sources françaises (Marmiton, 750g)

Respect des conditions d'utilisation :
- Throttling 1 req/s (AutoThrottle Scrapy)
- User-Agent transparent identifiant PrestoBot
- Respect du robots.txt Allrecipes
- Pas de bypass CAPTCHA
"""

import json
import re
from typing import Any
from urllib.parse import urljoin

import scrapy
from bs4 import BeautifulSoup
from loguru import logger

from src.agents.recipe_scout.scrapers.base import BaseRecipeScraper, RawRecipe

# ---- Constantes Allrecipes ----

ALLRECIPES_BASE_URL = "https://www.allrecipes.com"
ALLRECIPES_SEARCH_URL = "https://www.allrecipes.com/search"

# User-Agent conforme ROADMAP
MEALPLANNER_USER_AGENT = "Presto-Bot/0.1 (+https://presto.fr)"

# Sélecteurs CSS fallback si JSON-LD absent
SELECTORS_FALLBACK = {
    "title": "h1.article-heading, h1[class*='recipe-title'], h1",
    "ingredients": "[class*='mntl-structured-ingredients__list-item'], [class*='ingredient']",
    "instructions": "[class*='mntl-sc-block-group--OL'] li, [class*='instructions-section__markdown']",
    "prep_time": "[class*='prep-time'] [datetime], [class*='prep-time']",
    "cook_time": "[class*='cook-time'] [datetime], [class*='cook-time']",
    "total_time": "[class*='total-time'] [datetime], [class*='total-time']",
    "servings": "[class*='recipe-yield__label-arrow'] + *, [class*='servings']",
    "photo": "img[class*='primary-image'], img[class*='recipe-image']",
    "rating": "[class*='rating__value'], [id*='ratingValue']",
}

# Mapping des cuisines Allrecipes vers le format canonique Presto
CUISINE_MAPPING: dict[str, str] = {
    "mexican": "mexicaine",
    "italian": "italienne",
    "indian": "indienne",
    "asian": "asiatique",
    "chinese": "chinoise",
    "japanese": "japonaise",
    "thai": "thaïlandaise",
    "french": "française",
    "american": "américaine",
    "mediterranean": "méditerranéenne",
    "greek": "grecque",
    "middle eastern": "moyen-orientale",
    "african": "africaine",
    "spanish": "espagnole",
    "vietnamese": "vietnamienne",
    "korean": "coréenne",
}


def _map_cuisine(cuisine_raw: str | list[str] | None) -> str | None:
    """
    Normalise le type de cuisine Allrecipes vers le format canonique.

    Args:
        cuisine_raw: Valeur brute depuis le JSON-LD (str ou liste).

    Returns:
        Type de cuisine normalisé ou None.
    """
    if not cuisine_raw:
        return None

    if isinstance(cuisine_raw, list):
        cuisine_raw = cuisine_raw[0] if cuisine_raw else ""

    if not isinstance(cuisine_raw, str):
        return None

    lower = cuisine_raw.strip().lower()
    return CUISINE_MAPPING.get(lower, cuisine_raw.strip())


def _parse_time_iso(time_str: str | None) -> int | None:
    """
    Convertit une durée ISO 8601 en minutes.

    Gère les formats :
    - "PT1H30M" (ISO 8601)
    - "PT45M"

    Args:
        time_str: Chaîne de durée ISO 8601.

    Returns:
        Nombre de minutes, ou None si non parsable.
    """
    if not time_str:
        return None

    iso_match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", time_str.strip(), re.IGNORECASE)
    if iso_match and (iso_match.group(1) or iso_match.group(2)):
        hours = int(iso_match.group(1) or 0)
        minutes = int(iso_match.group(2) or 0)
        return hours * 60 + minutes

    return None


def _extract_jsonld_recipe(soup: BeautifulSoup) -> dict[str, Any] | None:
    """
    Extrait le JSON-LD schema.org/Recipe depuis le HTML Allrecipes.

    Allrecipes intègre systématiquement un JSON-LD Recipe dans ses pages.
    C'est la méthode la plus fiable et la moins sensible aux changements de layout.

    Args:
        soup: Objet BeautifulSoup de la page.

    Returns:
        Dict JSON-LD de la recette, ou None si absent.
    """
    for script_tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script_tag.string or "")

            # JSON-LD peut être une liste ou un objet
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") in ("Recipe",):
                        return item
            elif isinstance(data, dict):
                if data.get("@type") == "Recipe":
                    return data
                # Certaines pages emballent dans @graph
                if "@graph" in data:
                    for item in data.get("@graph", []):
                        if isinstance(item, dict) and item.get("@type") == "Recipe":
                            return item

        except (json.JSONDecodeError, AttributeError):
            continue

    return None


def _parse_servings(yield_value: Any) -> int | None:
    """
    Extrait le nombre de portions depuis la valeur recipeYield JSON-LD.

    Allrecipes peut retourner un entier, une chaîne ou une liste.

    Args:
        yield_value: Valeur brute recipeYield.

    Returns:
        Entier ou None.
    """
    if yield_value is None:
        return None

    if isinstance(yield_value, int):
        return yield_value if yield_value > 0 else None

    if isinstance(yield_value, list) and yield_value:
        yield_value = yield_value[0]

    if isinstance(yield_value, (str, float)):
        match = re.search(r"(\d+)", str(yield_value))
        return int(match.group(1)) if match else None

    return None


def parse_allrecipes_page(html: str, url: str) -> RawRecipe | None:
    """
    Parse le HTML d'une page recette Allrecipes.

    Priorité JSON-LD (fiable) avec fallback CSS.
    Mapping cuisine_type vers les valeurs canoniques.

    Args:
        html: Contenu HTML complet de la page.
        url: URL de la page source.

    Returns:
        RawRecipe avec les données extraites, ou None si page invalide.
    """
    soup = BeautifulSoup(html, "lxml")

    # Tentative JSON-LD (approche prioritaire)
    jsonld = _extract_jsonld_recipe(soup)

    if jsonld:
        return _parse_from_jsonld(jsonld, url)

    # Fallback CSS
    logger.debug("allrecipes_jsonld_absent_fallback_css", url=url)
    return _parse_from_css(soup, url)


def _parse_from_jsonld(data: dict[str, Any], url: str) -> RawRecipe | None:
    """
    Construit une RawRecipe depuis le JSON-LD Allrecipes.

    Args:
        data: Dict JSON-LD schema.org/Recipe.
        url: URL source.

    Returns:
        RawRecipe ou None si données insuffisantes.
    """
    title = data.get("name", "").strip()
    if not title:
        return None

    # Ingrédients
    ingredients_raw: list[str] = [
        str(ing).strip()
        for ing in data.get("recipeIngredient", [])
        if str(ing).strip()
    ]

    # Instructions : peut être une liste d'HowToStep, une liste de chaînes, ou une chaîne
    instructions_raw: list[str] = []
    raw_instructions = data.get("recipeInstructions", [])

    if isinstance(raw_instructions, str):
        instructions_raw = [raw_instructions.strip()]
    elif isinstance(raw_instructions, list):
        for item in raw_instructions:
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, dict):
                # HowToStep contient { "@type": "HowToStep", "text": "..." }
                text = item.get("text", "").strip()
                # Parfois les instructions sont dans des sections HowToSection
                if not text and item.get("@type") == "HowToSection":
                    for step in item.get("itemListElement", []):
                        if isinstance(step, dict):
                            step_text = step.get("text", "").strip()
                            if step_text and len(step_text) > 5:
                                instructions_raw.append(step_text)
                    continue
            else:
                text = ""

            if text and len(text) > 5:
                instructions_raw.append(text)

    # Temps
    prep_time_min = _parse_time_iso(data.get("prepTime"))
    cook_time_min = _parse_time_iso(data.get("cookTime"))

    # Portions
    servings = _parse_servings(data.get("recipeYield"))

    # Cuisine type (mapping vers le format canonique)
    cuisine_type = _map_cuisine(data.get("recipeCuisine"))

    # Photo
    photo_url: str | None = None
    image_data = data.get("image")
    if isinstance(image_data, list) and image_data:
        image_data = image_data[0]
    if isinstance(image_data, str):
        photo_url = image_data
    elif isinstance(image_data, dict):
        photo_url = image_data.get("url")

    # Note
    rating: float | None = None
    aggregate_rating = data.get("aggregateRating", {})
    if isinstance(aggregate_rating, dict):
        try:
            rating_val = aggregate_rating.get("ratingValue", 0)
            rating = float(rating_val) if rating_val else None
        except (ValueError, TypeError):
            pass

    # Tags/mots-clés
    keywords = data.get("keywords", "")
    if isinstance(keywords, str):
        tags_raw = [t.strip() for t in keywords.split(",") if t.strip()]
    elif isinstance(keywords, list):
        tags_raw = [str(t).strip() for t in keywords if str(t).strip()]
    else:
        tags_raw = []

    # Catégorie de recette → ajouter aux tags
    categories = data.get("recipeCategory", [])
    if isinstance(categories, str):
        categories = [categories]
    tags_raw.extend([str(c).strip() for c in categories if str(c).strip()])

    return RawRecipe(
        title=title,
        source_url=url,
        source_name="allrecipes",
        ingredients_raw=ingredients_raw,
        instructions_raw=instructions_raw,
        prep_time_min=prep_time_min,
        cook_time_min=cook_time_min,
        servings=servings,
        cuisine_type=cuisine_type,
        photo_url=photo_url,
        rating=rating,
        tags_raw=list(set(tags_raw)),  # Déduplication des tags
    )


def _parse_from_css(soup: BeautifulSoup, url: str) -> RawRecipe | None:
    """
    Fallback : extraction via sélecteurs CSS Allrecipes.

    Allrecipes refactorise régulièrement ses classes CSS — ce fallback
    est moins fiable et doit être mis à jour si le site change de layout.

    Args:
        soup: Objet BeautifulSoup de la page.
        url: URL source.

    Returns:
        RawRecipe ou None.
    """
    title_el = soup.select_one(SELECTORS_FALLBACK["title"])
    if not title_el:
        return None
    title = title_el.get_text(strip=True)
    if not title:
        return None

    ingredients_raw = [
        el.get_text(separator=" ", strip=True)
        for el in soup.select(SELECTORS_FALLBACK["ingredients"])
        if el.get_text(strip=True) and len(el.get_text(strip=True)) > 2
    ]

    instructions_raw = [
        el.get_text(separator=" ", strip=True)
        for el in soup.select(SELECTORS_FALLBACK["instructions"])
        if el.get_text(strip=True) and len(el.get_text(strip=True)) > 10
    ]

    # Temps depuis l'attribut datetime (ISO 8601)
    prep_el = soup.select_one(SELECTORS_FALLBACK["prep_time"])
    prep_time_min = _parse_time_iso(
        prep_el.get("datetime") if prep_el else None
    ) if prep_el else None

    cook_el = soup.select_one(SELECTORS_FALLBACK["cook_time"])
    cook_time_min = _parse_time_iso(
        cook_el.get("datetime") if cook_el else None
    ) if cook_el else None

    return RawRecipe(
        title=title,
        source_url=url,
        source_name="allrecipes",
        ingredients_raw=ingredients_raw,
        instructions_raw=instructions_raw,
        prep_time_min=prep_time_min,
        cook_time_min=cook_time_min,
    )


class AllRecipesSpider(scrapy.Spider):
    """
    Spider Scrapy pour Allrecipes.com.

    Collecte les recettes internationales depuis Allrecipes.
    Parsing JSON-LD prioritaire pour la fiabilité.
    Supporte les cuisines du monde (mexicain, indien, asiatique...).
    """

    name = "allrecipes"
    allowed_domains = ["www.allrecipes.com", "allrecipes.com"]

    custom_settings: dict[str, Any] = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1.0,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.0,
        "AUTOTHROTTLE_MAX_DELAY": 5.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "USER_AGENT": MEALPLANNER_USER_AGENT,
        "COOKIES_ENABLED": False,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
    }

    def __init__(self, url_list: list[str] | None = None, **kwargs: Any) -> None:
        """
        Initialise le spider avec une liste d'URLs à scraper.

        Args:
            url_list: URLs de recettes Allrecipes à scraper.
        """
        super().__init__(**kwargs)
        self.url_list = url_list or []
        self.scraped_recipes: list[RawRecipe] = []

    def start_requests(self) -> Any:
        """Génère les requêtes initiales."""
        for url in self.url_list:
            yield scrapy.Request(
                url=url,
                callback=self.parse_recipe,
                errback=self.handle_error,
                meta={"source_url": url},
            )

    def parse_recipe(self, response: scrapy.http.Response) -> Any:
        """
        Parse une page recette Allrecipes.

        Args:
            response: Réponse HTTP Scrapy.

        Yields:
            Dict recette pour le pipeline Scrapy.
        """
        if response.status != 200:
            logger.warning(
                "allrecipes_http_error",
                url=response.url,
                status=response.status,
            )
            return

        recipe = parse_allrecipes_page(response.text, response.url)

        if recipe is None:
            logger.debug("allrecipes_parse_failed", url=response.url)
            return

        if not recipe.ingredients_raw or not recipe.instructions_raw:
            logger.debug(
                "allrecipes_incomplete_recipe",
                url=response.url,
                title=recipe.title,
            )
            return

        self.scraped_recipes.append(recipe)

        logger.info(
            "allrecipes_recipe_scraped",
            title=recipe.title,
            url=response.url,
            cuisine_type=recipe.cuisine_type,
            ingredients_count=len(recipe.ingredients_raw),
        )

        yield {
            "title": recipe.title,
            "source_url": recipe.source_url,
            "source_name": recipe.source_name,
            "ingredients_raw": recipe.ingredients_raw,
            "instructions_raw": recipe.instructions_raw,
            "prep_time_min": recipe.prep_time_min,
            "cook_time_min": recipe.cook_time_min,
            "servings": recipe.servings,
            "difficulty": recipe.difficulty,
            "photo_url": recipe.photo_url,
            "rating": recipe.rating,
            "cuisine_type": recipe.cuisine_type,
            "tags_raw": recipe.tags_raw,
        }

    def handle_error(self, failure: Any) -> None:
        """
        Gère les erreurs réseau.

        Args:
            failure: Objet Failure Scrapy.
        """
        logger.warning(
            "allrecipes_request_failed",
            url=failure.request.url,
            error=str(failure.value),
        )


class AllRecipesScraper(BaseRecipeScraper):
    """
    Wrapper BaseRecipeScraper autour du spider Scrapy Allrecipes.

    Fournit l'interface standard scrape_url() et get_listing_urls()
    pour l'agent RECIPE_SCOUT.
    """

    source_name = "allrecipes"
    default_delay_seconds = 1.0

    def scrape_url(self, url: str) -> RawRecipe | None:
        """
        Scrape une URL Allrecipes.

        Args:
            url: URL de la page recette Allrecipes.

        Returns:
            RawRecipe ou None si erreur.
        """
        import time
        import urllib.request

        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": MEALPLANNER_USER_AGENT,
                    "Accept-Language": "fr-FR,fr;q=0.5,en-US;q=0.3",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                html = response.read().decode("utf-8", errors="replace")

            time.sleep(self.default_delay_seconds)
            return parse_allrecipes_page(html, url)

        except Exception as exc:
            logger.warning("allrecipes_scrape_url_failed", url=url, error=str(exc))
            return None

    def get_listing_urls(self, max_pages: int = 10) -> list[str]:
        """
        Retourne des URLs de recettes depuis les pages de recherche Allrecipes.

        Utilise les pages de catégories pour une meilleure diversité culinaire.

        Args:
            max_pages: Nombre de pages à parcourir.

        Returns:
            Liste d'URLs de pages recettes.
        """
        import time
        import urllib.request

        # Catégories diversifiées pour couvrir la cuisine internationale
        categories = [
            "/recipes/84/healthy-recipes/",
            "/recipes/76/appetizers-and-snacks/",
            "/recipes/17562/dinner/",
            "/recipes/80/main-dish/",
            "/recipes/1116/pasta-and-noodles/",
        ]

        collected_urls: list[str] = []
        pages_done = 0

        for category in categories:
            if pages_done >= max_pages:
                break

            category_url = urljoin(ALLRECIPES_BASE_URL, category)
            try:
                request = urllib.request.Request(
                    category_url,
                    headers={
                        "User-Agent": MEALPLANNER_USER_AGENT,
                        "Accept-Language": "fr-FR,fr;q=0.5,en-US;q=0.3",
                    },
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    html = response.read().decode("utf-8", errors="replace")

                soup = BeautifulSoup(html, "lxml")

                # Allrecipes utilise des liens /recipe/<id>/<slug>/ pour les recettes
                recipe_links = soup.select(
                    "a[href*='/recipe/'], [class*='card__detailsContainer'] a"
                )

                page_urls: list[str] = []
                for link in recipe_links:
                    href = str(link.get("href", ""))
                    if "/recipe/" in href:
                        full_url = urljoin(ALLRECIPES_BASE_URL, href)
                        if full_url not in collected_urls:
                            page_urls.append(full_url)
                            collected_urls.append(full_url)

                logger.info(
                    "allrecipes_listing_category",
                    category=category,
                    urls_found=len(page_urls),
                    total_collected=len(collected_urls),
                )

                pages_done += 1
                time.sleep(self.default_delay_seconds)

            except Exception as exc:
                logger.warning(
                    "allrecipes_listing_failed",
                    category=category,
                    error=str(exc),
                )

        return collected_urls
