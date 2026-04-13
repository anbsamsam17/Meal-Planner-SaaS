"""
Spider Scrapy pour 750g.com — source alternative de recettes françaises.

750g est l'un des sites de recettes les plus populaires en France avec
des centaines de milliers de recettes structurées et des données riches.

Respect des conditions d'utilisation :
- Throttling 1 req/s (AutoThrottle Scrapy)
- User-Agent transparent identifiant PrestoBot
- Respect du robots.txt 750g
- Pas de bypass CAPTCHA

Sélecteurs CSS/XPath basés sur la structure HTML 750g en avril 2026.
À mettre à jour si la structure HTML change (tester régulièrement).

Note d'implémentation :
750g utilise une combinaison de JSON-LD schema.org/Recipe et de HTML
traditionnel. La stratégie privilégie JSON-LD pour la fiabilité, avec
un fallback CSS si JSON-LD est absent. Le site ne nécessite pas Playwright
car le contenu principal est rendu côté serveur.
"""

import contextlib
import json
import re
from typing import Any
from urllib.parse import urljoin

import scrapy
from bs4 import BeautifulSoup
from loguru import logger

from src.agents.recipe_scout.scrapers.base import BaseRecipeScraper, RawRecipe

# ---- Constantes 750g ----

CUISINE_AZ_BASE_URL = "https://www.750g.com"
CUISINE_AZ_LISTING_URL = "https://www.750g.com/recettes_-cuisine.htm"

# Sélecteurs CSS de fallback (si JSON-LD absent)
SELECTORS = {
    "title": "h1.recipe-title, h1[itemprop='name'], h1.main-title",
    "ingredients_block": "[itemprop='recipeIngredient'], .ingredient-item, [class*='ingredient']",
    "instructions": "[itemprop='recipeInstructions'] li, .preparation-step, [class*='step']",
    "prep_time": "[itemprop='prepTime'], [class*='prep-time']",
    "cook_time": "[itemprop='cookTime'], [class*='cook-time']",
    "servings": "[itemprop='recipeYield'], [class*='servings'], [class*='yield']",
    "difficulty": "[class*='difficulty'], [class*='level'], [itemprop='difficulty']",
    "photo": "img[itemprop='image'], [class*='recipe-image'] img, [class*='hero'] img",
    "rating": "[itemprop='ratingValue'], [class*='rating-value']",
    "tags": "[class*='tag'], a[rel='tag'], [class*='keyword']",
}

# User-Agent conforme ROADMAP
MEALPLANNER_USER_AGENT = "Presto-Bot/0.1 (+https://presto.fr)"


def _parse_time_iso(time_str: str | None) -> int | None:
    """
    Convertit une durée ISO 8601 ou une chaîne lisible en minutes.

    Gère les formats :
    - "PT1H30M" (ISO 8601)
    - "PT45M"
    - "1h30" / "30 min" / "1 heure 30"

    Args:
        time_str: Chaîne de durée brute.

    Returns:
        Nombre de minutes, ou None si non parsable.
    """
    if not time_str:
        return None

    time_str = time_str.strip()

    # ISO 8601 : PT1H30M ou PT30M
    iso_match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", time_str, re.IGNORECASE)
    if iso_match and (iso_match.group(1) or iso_match.group(2)):
        hours = int(iso_match.group(1) or 0)
        minutes = int(iso_match.group(2) or 0)
        return hours * 60 + minutes

    # Format "1h30" ou "1h 30min"
    hm_match = re.match(r"(\d+)\s*h\s*(\d+)?", time_str, re.IGNORECASE)
    if hm_match:
        hours = int(hm_match.group(1))
        minutes = int(hm_match.group(2) or 0)
        return hours * 60 + minutes

    # Format "45 min" ou "45mn"
    min_match = re.match(r"(\d+)\s*(?:min|mn|minute)", time_str, re.IGNORECASE)
    if min_match:
        return int(min_match.group(1))

    return None


def _parse_difficulty_fr(difficulty_str: str | None) -> str | None:
    """
    Normalise la difficulté 750g vers le format canonique.

    750g utilise : "Très facile", "Facile", "Moyen", "Difficile", "Très difficile"

    Args:
        difficulty_str: Chaîne de difficulté brute.

    Returns:
        Chaîne canonique ou None.
    """
    if not difficulty_str:
        return None

    mapping = {
        "très facile": "very_easy",
        "facile": "easy",
        "moyen": "medium",
        "difficile": "hard",
        "très difficile": "very_hard",
    }

    lower = difficulty_str.strip().lower()
    for key, value in mapping.items():
        if key in lower:
            return value

    return None


def _extract_from_jsonld(soup: BeautifulSoup) -> dict[str, Any] | None:
    """
    Extrait les données de recette depuis le JSON-LD schema.org/Recipe.

    750g intègre un JSON-LD de type Recipe dans chaque page de recette.
    Cette approche est plus fiable que les sélecteurs CSS car moins
    sensible aux changements de layout.

    Args:
        soup: Objet BeautifulSoup de la page.

    Returns:
        Dict des données JSON-LD si trouvé, None sinon.
    """
    for script_tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script_tag.string or "")

            # Peut être un tableau ou un objet unique
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") in ("Recipe", "recipe"):
                        return item
            elif isinstance(data, dict):
                # GraphQL ou objet direct
                if data.get("@type") in ("Recipe", "recipe"):
                    return data
                # Parfois imbriqué dans @graph
                if "@graph" in data:
                    for item in data["@graph"]:
                        if isinstance(item, dict) and item.get("@type") in ("Recipe", "recipe"):
                            return item
        except (json.JSONDecodeError, AttributeError):
            continue

    return None


def parse_cuisine_az_page(html: str, url: str) -> RawRecipe | None:
    """
    Parse le HTML d'une page recette 750g.

    Stratégie :
    1. Tente d'extraire les données depuis le JSON-LD (fiable)
    2. Fallback sur les sélecteurs CSS si JSON-LD absent

    Args:
        html: Contenu HTML de la page.
        url: URL de la page source.

    Returns:
        RawRecipe ou None si la page n'est pas une recette valide.
    """
    soup = BeautifulSoup(html, "lxml")

    # ---- Tentative JSON-LD (approche prioritaire) ----
    jsonld = _extract_from_jsonld(soup)

    if jsonld:
        return _parse_from_jsonld(jsonld, url)

    # ---- Fallback CSS ----
    logger.debug("cuisine_az_jsonld_fallback", url=url)
    return _parse_from_css(soup, url)


def _parse_from_jsonld(data: dict[str, Any], url: str) -> RawRecipe | None:
    """
    Construit une RawRecipe depuis les données JSON-LD schema.org/Recipe.

    Args:
        data: Dict JSON-LD extrait de la page.
        url: URL source.

    Returns:
        RawRecipe ou None si données insuffisantes.
    """
    title = data.get("name", "").strip()
    if not title:
        logger.debug("cuisine_az_jsonld_no_title", url=url)
        return None

    # Ingrédients
    raw_ingredients = data.get("recipeIngredient", [])
    ingredients_raw: list[str] = [
        str(ing).strip() for ing in raw_ingredients if str(ing).strip()
    ]

    # Instructions (texte ou liste d'objets HowToStep)
    raw_instructions = data.get("recipeInstructions", [])
    instructions_raw: list[str] = []
    if isinstance(raw_instructions, str):
        instructions_raw = [raw_instructions]
    elif isinstance(raw_instructions, list):
        for step in raw_instructions:
            if isinstance(step, str):
                text = step.strip()
            elif isinstance(step, dict):
                text = step.get("text", "").strip()
            else:
                text = ""
            if text and len(text) > 5:
                instructions_raw.append(text)

    # Temps
    prep_time_min = _parse_time_iso(data.get("prepTime"))
    cook_time_min = _parse_time_iso(data.get("cookTime"))

    # Portions
    servings: int | None = None
    yield_str = data.get("recipeYield", "")
    if yield_str:
        yield_str = str(yield_str)
        match = re.search(r"(\d+)", yield_str)
        if match:
            servings = int(match.group(1))

    # Difficulté (extension propriétaire ou champ custom)
    difficulty_raw = data.get("difficulty") or data.get("recipeDifficulty")
    difficulty = _parse_difficulty_fr(str(difficulty_raw) if difficulty_raw else None)

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
        with contextlib.suppress(ValueError, TypeError):
            rating = float(aggregate_rating.get("ratingValue", 0) or 0)

    # Tags / mots-clés
    keywords = data.get("keywords", "")
    if isinstance(keywords, str):
        tags_raw = [t.strip() for t in keywords.split(",") if t.strip()]
    elif isinstance(keywords, list):
        tags_raw = [str(t).strip() for t in keywords if str(t).strip()]
    else:
        tags_raw = []

    # Cuisine type
    cuisine_type = data.get("recipeCuisine")
    if isinstance(cuisine_type, list):
        cuisine_type = cuisine_type[0] if cuisine_type else None

    return RawRecipe(
        title=title,
        source_url=url,
        source_name="750g",
        ingredients_raw=ingredients_raw,
        instructions_raw=instructions_raw,
        prep_time_min=prep_time_min,
        cook_time_min=cook_time_min,
        servings=servings,
        difficulty=difficulty,
        photo_url=photo_url,
        rating=rating if rating and rating > 0 else None,
        cuisine_type=cuisine_type,
        tags_raw=tags_raw,
    )


def _parse_from_css(soup: BeautifulSoup, url: str) -> RawRecipe | None:
    """
    Fallback : extrait les données depuis les sélecteurs CSS.

    Args:
        soup: Objet BeautifulSoup de la page.
        url: URL source.

    Returns:
        RawRecipe ou None.
    """
    # Titre
    title_el = soup.select_one(SELECTORS["title"])
    if not title_el:
        return None
    title = title_el.get_text(strip=True)
    if not title:
        return None

    # Ingrédients
    ingredients_raw = [
        el.get_text(separator=" ", strip=True)
        for el in soup.select(SELECTORS["ingredients_block"])
        if el.get_text(strip=True) and len(el.get_text(strip=True)) > 2
    ]

    # Instructions
    instructions_raw = [
        el.get_text(separator=" ", strip=True)
        for el in soup.select(SELECTORS["instructions"])
        if el.get_text(strip=True) and len(el.get_text(strip=True)) > 10
    ]

    # Temps
    prep_el = soup.select_one(SELECTORS["prep_time"])
    prep_time_min = _parse_time_iso(
        prep_el.get("content") or prep_el.get_text(strip=True) if prep_el else None
    )
    cook_el = soup.select_one(SELECTORS["cook_time"])
    cook_time_min = _parse_time_iso(
        cook_el.get("content") or cook_el.get_text(strip=True) if cook_el else None
    )

    # Portions
    servings: int | None = None
    servings_el = soup.select_one(SELECTORS["servings"])
    if servings_el:
        servings_text = servings_el.get("content") or servings_el.get_text(strip=True)
        match = re.search(r"(\d+)", servings_text or "")
        if match:
            servings = int(match.group(1))

    # Difficulté
    difficulty_el = soup.select_one(SELECTORS["difficulty"])
    difficulty = _parse_difficulty_fr(
        difficulty_el.get_text(strip=True) if difficulty_el else None
    )

    # Photo
    photo_url: str | None = None
    photo_el = soup.select_one(SELECTORS["photo"])
    if photo_el:
        src = photo_el.get("src") or photo_el.get("data-src")
        if src:
            photo_url = urljoin(CUISINE_AZ_BASE_URL, str(src)) if str(src).startswith("/") else str(src)

    # Tags
    tags_raw = [
        el.get_text(strip=True)
        for el in soup.select(SELECTORS["tags"])
        if el.get_text(strip=True)
    ]

    return RawRecipe(
        title=title,
        source_url=url,
        source_name="750g",
        ingredients_raw=ingredients_raw,
        instructions_raw=instructions_raw,
        prep_time_min=prep_time_min,
        cook_time_min=cook_time_min,
        servings=servings,
        difficulty=difficulty,
        photo_url=photo_url,
        tags_raw=tags_raw,
    )


class CuisineAzSpider(scrapy.Spider):
    """
    Spider Scrapy pour la collecte de recettes 750g.com.

    Navigue les pages de listing 750g et extrait les données de chaque recette.
    Respecte le robots.txt automatiquement (Scrapy active ROBOTSTXT_OBEY par défaut).

    Stratégie JSON-LD prioritaire pour la fiabilité, fallback CSS si absent.
    """

    name = "cuisineaz"
    allowed_domains = ["www.750g.com", "750g.com"]

    custom_settings: dict[str, Any] = {
        # Respect du robots.txt 750g
        "ROBOTSTXT_OBEY": True,
        # Throttling 1 req/s (ROADMAP)
        "DOWNLOAD_DELAY": 1.0,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.0,
        "AUTOTHROTTLE_MAX_DELAY": 5.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        # User-Agent Presto (ROADMAP)
        "USER_AGENT": MEALPLANNER_USER_AGENT,
        # Pas de cookies (évite le tracking)
        "COOKIES_ENABLED": False,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
    }

    def __init__(self, url_list: list[str] | None = None, **kwargs: Any) -> None:
        """
        Initialise le spider avec une liste d'URLs à scraper.

        Args:
            url_list: URLs de recettes 750g à scraper.
        """
        super().__init__(**kwargs)
        self.url_list = url_list or []
        self.scraped_recipes: list[RawRecipe] = []

    def start_requests(self) -> Any:
        """Génère les requêtes initiales depuis la liste d'URLs."""
        for url in self.url_list:
            yield scrapy.Request(
                url=url,
                callback=self.parse_recipe,
                errback=self.handle_error,
                meta={"source_url": url},
            )

    def parse_recipe(self, response: scrapy.http.Response) -> Any:
        """
        Parse une page recette 750g.

        Privilégie l'extraction JSON-LD. Skip les pages non-recettes silencieusement.

        Args:
            response: Réponse HTTP Scrapy.

        Yields:
            Dict recette normalisé compatible avec le pipeline.
        """
        if response.status != 200:
            logger.warning(
                "cuisine_az_http_error",
                url=response.url,
                status=response.status,
            )
            return

        recipe = parse_cuisine_az_page(response.text, response.url)

        if recipe is None:
            logger.debug("cuisine_az_parse_failed", url=response.url)
            return

        if not recipe.ingredients_raw or not recipe.instructions_raw:
            logger.debug(
                "cuisine_az_incomplete_recipe",
                url=response.url,
                title=recipe.title,
            )
            return

        self.scraped_recipes.append(recipe)

        logger.info(
            "cuisine_az_recipe_scraped",
            title=recipe.title,
            url=response.url,
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
        Gère les erreurs réseau lors du scraping.

        Log sans faire planter le spider — erreurs 429 attendues normales.

        Args:
            failure: Objet Failure Scrapy.
        """
        logger.warning(
            "cuisine_az_request_failed",
            url=failure.request.url,
            error=str(failure.value),
        )


class CuisineAzScraper(BaseRecipeScraper):
    """
    Wrapper BaseRecipeScraper autour du spider Scrapy 750g.

    Fournit l'interface standard scrape_url() et get_listing_urls()
    pour l'agent RECIPE_SCOUT.
    """

    source_name = "750g"
    default_delay_seconds = 1.0

    def scrape_url(self, url: str) -> RawRecipe | None:
        """
        Scrape une URL 750g via requests + BeautifulSoup.

        Args:
            url: URL de la page recette 750g.

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
                    "Accept-Language": "fr-FR,fr;q=0.9",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                html = response.read().decode("utf-8", errors="replace")

            time.sleep(self.default_delay_seconds)
            return parse_cuisine_az_page(html, url)

        except Exception as exc:
            logger.warning("cuisine_az_scrape_url_failed", url=url, error=str(exc))
            return None

    def get_listing_urls(self, max_pages: int = 10) -> list[str]:
        """
        Retourne des URLs de recettes depuis les pages de listing 750g.

        Args:
            max_pages: Nombre de pages de listing à parcourir.

        Returns:
            Liste d'URLs de pages recettes.
        """
        import time
        import urllib.request

        collected_urls: list[str] = []

        for page_num in range(1, max_pages + 1):
            # URL de listing 750g avec pagination
            listing_url = f"{CUISINE_AZ_LISTING_URL}?p={page_num}"

            try:
                request = urllib.request.Request(
                    listing_url,
                    headers={
                        "User-Agent": MEALPLANNER_USER_AGENT,
                        "Accept-Language": "fr-FR,fr;q=0.9",
                    },
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    html = response.read().decode("utf-8", errors="replace")

                soup = BeautifulSoup(html, "lxml")

                # Liens vers les pages recettes individuelles
                recipe_links = soup.select(
                    "a[href*='/recettes/'], a[class*='recipe-card'], [class*='recipe-link'] a"
                )

                page_urls: list[str] = []
                for link in recipe_links:
                    href = str(link.get("href", ""))
                    if "/recettes/" in href and href not in collected_urls:
                        full_url = urljoin(CUISINE_AZ_BASE_URL, href)
                        if full_url not in collected_urls:
                            page_urls.append(full_url)
                            collected_urls.append(full_url)

                logger.info(
                    "cuisine_az_listing_page",
                    page=page_num,
                    urls_found=len(page_urls),
                    total_collected=len(collected_urls),
                )

                if not page_urls:
                    break

                time.sleep(self.default_delay_seconds)

            except Exception as exc:
                logger.warning(
                    "cuisine_az_listing_failed",
                    page=page_num,
                    error=str(exc),
                )
                break

        return collected_urls
