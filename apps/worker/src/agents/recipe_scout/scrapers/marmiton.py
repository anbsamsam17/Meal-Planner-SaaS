"""
Spider Scrapy pour Marmiton.fr — source principale de recettes françaises.

Marmiton contient ~70 000 recettes françaises avec notes, commentaires,
et métadonnées complètes. C'est la source prioritaire pour le catalogue FR.

Respect des conditions d'utilisation :
- Throttling 1 req/s (AutoThrottle Scrapy)
- User-Agent transparent identifiant PrestoBot
- Respect du robots.txt Marmiton
- Pas de bypass CAPTCHA
- Collecte uniquement des données publiques

Sélecteurs CSS/XPath basés sur le HTML Marmiton en avril 2026.
À mettre à jour si la structure HTML change (tester régulièrement).

Structure du spider :
1. `MarmitonSpider` : spider Scrapy pour l'extraction par URL
2. `MarmitonScraper` : wrapper `BaseRecipeScraper` qui orchestre le spider
"""

import contextlib
import re
from typing import Any
from urllib.parse import urljoin

import scrapy
from bs4 import BeautifulSoup
from loguru import logger

from src.agents.recipe_scout.scrapers.base import BaseRecipeScraper, RawRecipe

# ---- Constantes Marmiton ----

MARMITON_BASE_URL = "https://www.marmiton.org"
MARMITON_SEARCH_URL = "https://www.marmiton.org/recettes/recherche.aspx"
MARMITON_LISTING_URL = "https://www.marmiton.org/recettes/"

# Sélecteurs CSS basés sur la structure HTML Marmiton (2026-04)
# Documentés ici pour faciliter la maintenance lors des changements de layout
SELECTORS = {
    # Titre principal de la recette
    "title": "h1.RTEXT__title, h1[class*='recipe-title'], h1[itemprop='name']",
    # Bloc des ingrédients
    "ingredients_block": "[class*='ingredient'], [itemprop='recipeIngredient']",
    # Étapes de préparation
    "instructions": "[class*='preparation-step'], [itemprop='recipeInstructions'] li, [class*='step-text']",
    # Temps de préparation
    "prep_time": "[itemprop='prepTime'], [class*='preptime']",
    # Temps de cuisson
    "cook_time": "[itemprop='cookTime'], [class*='cooktime']",
    # Nombre de portions
    "servings": "[itemprop='recipeYield'], [class*='recipe-yield']",
    # Niveau de difficulté
    "difficulty": "[class*='difficulty'], [class*='level']",
    # Image principale
    "photo": "img[itemprop='image'], img[class*='recipe-photo'], [class*='hero-image'] img",
    # Note de la recette
    "rating": "[itemprop='ratingValue']",
    # Tags / mots-clés
    "tags": "[class*='tag-'], a[class*='keyword']",
}


def _parse_time_minutes(time_str: str | None) -> int | None:
    """
    Convertit une chaîne de temps en minutes.

    Gère les formats :
    - "PT30M" (ISO 8601 de Marmiton)
    - "1h30" / "1h 30min"
    - "45 min" / "45mn"

    Args:
        time_str: Chaîne de temps brute depuis le HTML.

    Returns:
        Nombre de minutes, ou None si non parsable.
    """
    if not time_str:
        return None

    time_str = time_str.strip()

    # Format ISO 8601 : PT1H30M ou PT30M
    iso_match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", time_str, re.IGNORECASE)
    if iso_match:
        hours = int(iso_match.group(1) or 0)
        minutes = int(iso_match.group(2) or 0)
        return hours * 60 + minutes

    # Format "1h30" ou "1h 30min" ou "1h30min"
    hm_match = re.match(r"(\d+)\s*h\s*(\d+)?", time_str, re.IGNORECASE)
    if hm_match:
        hours = int(hm_match.group(1))
        minutes = int(hm_match.group(2) or 0)
        return hours * 60 + minutes

    # Format "45 min" ou "45mn" ou "45 minutes"
    min_match = re.match(r"(\d+)\s*(?:min|mn|minute)", time_str, re.IGNORECASE)
    if min_match:
        return int(min_match.group(1))

    return None


def _parse_difficulty(difficulty_str: str | None) -> str | None:
    """
    Normalise le niveau de difficulté Marmiton vers un format canonique.

    Marmiton utilise : "Très facile", "Facile", "Niveau moyen", "Difficile"

    Args:
        difficulty_str: Chaîne de difficulté brute.

    Returns:
        Chaîne normalisée ou None.
    """
    if not difficulty_str:
        return None

    difficulty_str = difficulty_str.strip().lower()

    mapping = {
        "très facile": "very_easy",
        "facile": "easy",
        "niveau moyen": "medium",
        "moyen": "medium",
        "difficile": "hard",
        "très difficile": "very_hard",
    }

    for key, value in mapping.items():
        if key in difficulty_str:
            return value

    return difficulty_str


def parse_marmiton_page(html: str, url: str) -> RawRecipe | None:
    """
    Parse le HTML d'une page recette Marmiton.

    Fonction pure (testable sans Scrapy) qui extrait les données structurées
    depuis le HTML brut. Les sélecteurs CSS sont documentés dans SELECTORS.

    Args:
        html: Contenu HTML complet de la page.
        url: URL de la page (pour les métadonnées source).

    Returns:
        RawRecipe avec les données extraites, ou None si page invalide.
    """
    soup = BeautifulSoup(html, "lxml")

    # ---- Titre ----
    title_el = soup.select_one(SELECTORS["title"])
    if not title_el:
        logger.debug("marmiton_parse_no_title", url=url)
        return None

    title = title_el.get_text(strip=True)
    if not title:
        return None

    # ---- Ingrédients ----
    # Marmiton structure les ingrédients dans des éléments avec quantité + libellé
    ingredients_raw: list[str] = []
    for el in soup.select(SELECTORS["ingredients_block"]):
        text = el.get_text(separator=" ", strip=True)
        if text and len(text) > 2:  # Filtrer les éléments vides
            ingredients_raw.append(text)

    # ---- Instructions ----
    instructions_raw: list[str] = []
    for el in soup.select(SELECTORS["instructions"]):
        text = el.get_text(separator=" ", strip=True)
        if text and len(text) > 10:  # Filtrer les numéros seuls
            instructions_raw.append(text)

    # ---- Temps ----
    prep_el = soup.select_one(SELECTORS["prep_time"])
    prep_time_min = _parse_time_minutes(
        prep_el.get("content") or prep_el.get_text(strip=True) if prep_el else None
    )

    cook_el = soup.select_one(SELECTORS["cook_time"])
    cook_time_min = _parse_time_minutes(
        cook_el.get("content") or cook_el.get_text(strip=True) if cook_el else None
    )

    # ---- Portions ----
    servings_el = soup.select_one(SELECTORS["servings"])
    servings: int | None = None
    if servings_el:
        servings_text = servings_el.get("content") or servings_el.get_text(strip=True)
        match = re.search(r"(\d+)", servings_text or "")
        if match:
            servings = int(match.group(1))

    # ---- Difficulté ----
    difficulty_el = soup.select_one(SELECTORS["difficulty"])
    difficulty = _parse_difficulty(
        difficulty_el.get_text(strip=True) if difficulty_el else None
    )

    # ---- Photo ----
    photo_el = soup.select_one(SELECTORS["photo"])
    photo_url: str | None = None
    if photo_el:
        photo_url = photo_el.get("src") or photo_el.get("data-src")
        if photo_url and photo_url.startswith("/"):
            photo_url = urljoin(MARMITON_BASE_URL, photo_url)

    # ---- Note ----
    rating_el = soup.select_one(SELECTORS["rating"])
    rating: float | None = None
    if rating_el:
        with contextlib.suppress(ValueError, TypeError):
            rating = float(rating_el.get("content") or rating_el.get_text(strip=True))

    # ---- Tags ----
    tags_raw: list[str] = [
        el.get_text(strip=True)
        for el in soup.select(SELECTORS["tags"])
        if el.get_text(strip=True)
    ]

    return RawRecipe(
        title=title,
        source_url=url,
        source_name="marmiton",
        ingredients_raw=ingredients_raw,
        instructions_raw=instructions_raw,
        prep_time_min=prep_time_min,
        cook_time_min=cook_time_min,
        servings=servings,
        difficulty=difficulty,
        photo_url=photo_url,
        rating=rating,
        tags_raw=tags_raw,
    )


class MarmitonSpider(scrapy.Spider):
    """
    Spider Scrapy pour la collecte de recettes Marmiton.

    Navigue les pages de listing Marmiton et extrait les données
    de chaque page de recette. Respecte le robots.txt automatiquement
    (Scrapy active ROBOTSTXT_OBEY par défaut).

    Usage :
        from scrapy.crawler import CrawlerProcess
        process = CrawlerProcess(settings)
        process.crawl(MarmitonSpider, url_list=["https://..."])
        process.start()
    """

    name = "marmiton"
    allowed_domains = ["www.marmiton.org"]

    # Paramètres Scrapy pour le respect des règles de scraping
    custom_settings: dict[str, Any] = {
        # Respect des robots.txt Marmiton (OBLIGATOIRE)
        "ROBOTSTXT_OBEY": True,
        # Throttling : 1 requête par seconde maximum
        "DOWNLOAD_DELAY": 1.0,
        # AutoThrottle : ajuste automatiquement selon la charge serveur
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.0,
        "AUTOTHROTTLE_MAX_DELAY": 5.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        # User-Agent transparent
        "USER_AGENT": (
            "PrestoBot/1.0 (+https://presto.fr/bot; "
            "collecte@presto.fr)"
        ),
        # Pas de cookies (évite le tracking)
        "COOKIES_ENABLED": False,
        # Retry limité pour ne pas surcharger Marmiton
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        # Respect du Crawl-Delay dans robots.txt
        "DOWNLOAD_WARNSIZE": 5 * 1024 * 1024,  # 5MB max par page
    }

    def __init__(self, url_list: list[str] | None = None, **kwargs: Any) -> None:
        """
        Initialise le spider avec une liste d'URLs à scraper.

        Args:
            url_list: Liste d'URLs de pages recettes Marmiton.
                      Si None, utilise les URLs de listing par défaut.
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
        Parse une page de recette Marmiton.

        Utilise `parse_marmiton_page` pour l'extraction des données
        (séparation de la logique de parsing de la logique Scrapy).

        Args:
            response: Réponse HTTP Scrapy.

        Yields:
            Dict avec les données de la recette (compatible Scrapy pipeline).
        """
        if response.status != 200:
            logger.warning(
                "marmiton_http_error",
                url=response.url,
                status=response.status,
            )
            return

        recipe = parse_marmiton_page(response.text, response.url)

        if recipe is None:
            logger.debug("marmiton_parse_failed", url=response.url)
            return

        if not recipe.ingredients_raw or not recipe.instructions_raw:
            logger.debug(
                "marmiton_incomplete_recipe",
                url=response.url,
                title=recipe.title,
                has_ingredients=bool(recipe.ingredients_raw),
                has_instructions=bool(recipe.instructions_raw),
            )
            return

        # Stocker dans la liste de résultats pour récupération post-crawl
        self.scraped_recipes.append(recipe)

        logger.info(
            "marmiton_recipe_scraped",
            title=recipe.title,
            url=response.url,
            ingredients_count=len(recipe.ingredients_raw),
        )

        # Yield pour le pipeline Scrapy (peut être utilisé avec des Item pipelines)
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
            "tags_raw": recipe.tags_raw,
        }

    def handle_error(self, failure: Any) -> None:
        """
        Gère les erreurs réseau lors du scraping.

        Log l'erreur sans faire planter le spider.
        Les erreurs 429 (rate limit Marmiton) sont attendues et normales.

        Args:
            failure: Objet Failure Scrapy avec les détails de l'erreur.
        """
        logger.warning(
            "marmiton_request_failed",
            url=failure.request.url,
            error=str(failure.value),
        )


class MarmitonScraper(BaseRecipeScraper):
    """
    Wrapper BaseRecipeScraper autour du spider Scrapy Marmiton.

    Fournit l'interface standard `scrape_url()` et `get_listing_urls()`
    pour l'agent RECIPE_SCOUT.

    Usage par l'agent :
        scraper = MarmitonScraper()
        urls = scraper.get_listing_urls(max_pages=5)
        for url in urls:
            recipe = scraper.scrape_url(url)
            if recipe:
                # Normaliser, valider, insérer...
    """

    source_name = "marmiton"
    default_delay_seconds = 1.0

    def scrape_url(self, url: str) -> RawRecipe | None:
        """
        Scrape une URL Marmiton en utilisant requests + BeautifulSoup.

        Note : pour le batch Celery, utiliser `MarmitonSpider` via Scrapy
        qui gère le throttling et le retry automatiquement.
        Cette méthode est pour les appels unitaires (tests, debug).

        Args:
            url: URL de la page recette Marmiton.

        Returns:
            RawRecipe ou None si erreur.
        """
        import time
        import urllib.request

        try:
            # User-Agent obligatoire pour identifier notre bot
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept-Language": "fr-FR,fr;q=0.9",
                },
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                html = response.read().decode("utf-8", errors="replace")

            # Throttling respecté
            time.sleep(self.default_delay_seconds)

            return parse_marmiton_page(html, url)

        except Exception as exc:
            logger.warning("marmiton_scrape_url_failed", url=url, error=str(exc))
            return None

    def get_listing_urls(self, max_pages: int = 10) -> list[str]:
        """
        Retourne des URLs de recettes Marmiton depuis les pages de listing.

        Navigue les pages de résultats de recherche et extrait les URLs
        des pages de recettes individuelles.

        Args:
            max_pages: Nombre maximum de pages de listing.

        Returns:
            Liste d'URLs de pages recettes Marmiton.
        """
        import time
        import urllib.request

        collected_urls: list[str] = []

        for page_num in range(1, max_pages + 1):
            # URL de listing Marmiton avec pagination
            listing_url = f"{MARMITON_LISTING_URL}?&start={(page_num - 1) * 20}"

            try:
                request = urllib.request.Request(
                    listing_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept-Language": "fr-FR,fr;q=0.9",
                    },
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    html = response.read().decode("utf-8", errors="replace")

                soup = BeautifulSoup(html, "lxml")

                # Sélecteur des liens vers les pages recettes
                # Format Marmiton : /recettes/recette_<slug>_<id>.aspx
                recipe_links = soup.select(
                    "a[href*='/recettes/recette_'], a[class*='recipe-card-link']"
                )

                page_urls = []
                for link in recipe_links:
                    href = link.get("href", "")
                    if "/recettes/recette_" in href:
                        full_url = urljoin(MARMITON_BASE_URL, href)
                        if full_url not in collected_urls:
                            page_urls.append(full_url)
                            collected_urls.append(full_url)

                logger.info(
                    "marmiton_listing_page",
                    page=page_num,
                    urls_found=len(page_urls),
                    total_collected=len(collected_urls),
                )

                if not page_urls:
                    # Pas de nouvelles URLs → fin du listing
                    break

                # Throttling entre les pages de listing
                time.sleep(self.default_delay_seconds)

            except Exception as exc:
                logger.warning(
                    "marmiton_listing_failed",
                    page=page_num,
                    error=str(exc),
                )
                break

        return collected_urls
