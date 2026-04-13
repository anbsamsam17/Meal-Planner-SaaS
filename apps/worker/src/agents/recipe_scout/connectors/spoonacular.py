"""
Client HTTP async pour l'API Spoonacular.

Spoonacular fournit ~380 000 recettes avec données nutritionnelles complètes.
Free tier : 150 requêtes/jour — surveiller le quota attentivement.

Fonctionnalités implémentées (v0) :
- Recherche de recettes par mots-clés
- Récupération du détail d'une recette
- Gestion automatique du quota (150 req/j)
- Retry avec tenacity (backoff exponentiel)
- Conversion vers RawRecipe

Documentation API : https://spoonacular.com/food-api/docs
"""

import os
from datetime import date
from typing import Any

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.agents.recipe_scout.scrapers.base import RawRecipe

# ---- Constantes ----

SPOONACULAR_BASE_URL = "https://api.spoonacular.com"

# Limite quotidienne du free tier
SPOONACULAR_DAILY_LIMIT = 150

# Compteur de requêtes quotidiennes (en mémoire — réinitialisé au redémarrage)
# En Phase 1 mature : stocker dans Redis pour persister entre les redémarrages
_daily_request_count: dict[str, int] = {}


def _get_today_key() -> str:
    """Retourne la clé de date pour le compteur quotidien."""
    return date.today().isoformat()


def _increment_request_counter() -> int:
    """
    Incrémente le compteur de requêtes quotidiennes.

    Returns:
        Nombre de requêtes effectuées aujourd'hui.
    """
    today = _get_today_key()
    _daily_request_count[today] = _daily_request_count.get(today, 0) + 1
    return _daily_request_count[today]


def _get_request_count() -> int:
    """Retourne le nombre de requêtes effectuées aujourd'hui."""
    return _daily_request_count.get(_get_today_key(), 0)


class SpoonacularQuotaExceeded(Exception):
    """Levée quand la limite quotidienne Spoonacular est atteinte."""
    pass


class SpoonacularAPIError(Exception):
    """Levée pour les erreurs HTTP de l'API Spoonacular."""
    pass


class SpoonacularClient:
    """
    Client async pour l'API Spoonacular.

    Gère l'authentification, le quota quotidien, les retries automatiques
    et la conversion des réponses vers le format interne RawRecipe.

    Usage :
        async with SpoonacularClient() as client:
            recipes = await client.search_recipes("poulet rôti", max_results=10)
    """

    def __init__(self, api_key: str | None = None) -> None:
        """
        Initialise le client Spoonacular.

        Args:
            api_key: Clé API Spoonacular. Si None, lit SPOONACULAR_API_KEY.
        """
        self.api_key = api_key or os.getenv("SPOONACULAR_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "SPOONACULAR_API_KEY manquante. "
                "Définir la variable d'environnement ou passer api_key."
            )

        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "SpoonacularClient":
        """Ouvre la connexion HTTP persistante."""
        self._client = httpx.AsyncClient(
            base_url=SPOONACULAR_BASE_URL,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                "Accept": "application/json",
                "User-Agent": "PrestoBot/1.0 (+https://presto.fr/bot)",
            },
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Ferme la connexion HTTP proprement."""
        if self._client:
            await self._client.aclose()

    def _check_quota(self) -> None:
        """
        Vérifie que le quota quotidien n'est pas dépassé.

        Raises:
            SpoonacularQuotaExceeded si 150 req/j atteint.
        """
        count = _get_request_count()
        if count >= SPOONACULAR_DAILY_LIMIT:
            logger.error(
                "spoonacular_quota_exceeded",
                daily_count=count,
                limit=SPOONACULAR_DAILY_LIMIT,
            )
            raise SpoonacularQuotaExceeded(
                f"Quota Spoonacular atteint : {count}/{SPOONACULAR_DAILY_LIMIT} req/jour. "
                "Réessayer demain."
            )

        # Alerte à 80% du quota
        if count >= SPOONACULAR_DAILY_LIMIT * 0.8:
            logger.warning(
                "spoonacular_quota_approaching",
                daily_count=count,
                limit=SPOONACULAR_DAILY_LIMIT,
                percent=round(count / SPOONACULAR_DAILY_LIMIT * 100),
            )

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        reraise=True,
    )
    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """
        Effectue une requête GET avec retry automatique.

        Tenacity retry sur les erreurs HTTP 5xx et les timeouts.
        Pas de retry sur les 4xx (quota, auth) — erreurs permanentes.

        Args:
            endpoint: Chemin de l'endpoint (ex: "/recipes/complexSearch").
            params: Paramètres de requête.

        Returns:
            Corps JSON de la réponse.

        Raises:
            SpoonacularAPIError pour les erreurs HTTP.
        """
        if self._client is None:
            raise RuntimeError(
                "Utiliser le client dans un contexte async with : "
                "async with SpoonacularClient() as client: ..."
            )

        self._check_quota()
        count = _increment_request_counter()

        query_params = {"apiKey": self.api_key, **(params or {})}

        logger.debug(
            "spoonacular_request",
            endpoint=endpoint,
            daily_count=count,
        )

        response = await self._client.get(endpoint, params=query_params)

        if response.status_code == 402:
            raise SpoonacularQuotaExceeded(
                "Quota Spoonacular dépassé (HTTP 402 Payment Required)."
            )

        if response.status_code == 401:
            raise SpoonacularAPIError(
                "Clé API Spoonacular invalide (HTTP 401). "
                "Vérifier SPOONACULAR_API_KEY."
            )

        response.raise_for_status()
        return response.json()

    async def search_recipes(
        self,
        query: str,
        max_results: int = 20,
        cuisine: str | None = None,
        diet: str | None = None,
        max_ready_time: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recherche des recettes par mots-clés.

        Args:
            query: Terme de recherche (ex: "poulet rôti", "pasta").
            max_results: Nombre maximum de résultats (max 100 par appel).
            cuisine: Filtre cuisine (ex: "French", "Italian").
            diet: Filtre régime (ex: "vegetarian", "vegan").
            max_ready_time: Temps de préparation max en minutes.

        Returns:
            Liste de dicts avec les données brutes de l'API Spoonacular.
        """
        params: dict[str, Any] = {
            "query": query,
            "number": min(max_results, 100),
            "addRecipeInformation": True,
            "addRecipeNutrition": False,  # Économiser les appels API
            "language": "fr",
        }

        if cuisine:
            params["cuisine"] = cuisine
        if diet:
            params["diet"] = diet
        if max_ready_time:
            params["maxReadyTime"] = max_ready_time

        data = await self._get("/recipes/complexSearch", params)
        results = data.get("results", [])

        logger.info(
            "spoonacular_search",
            query=query,
            results_count=len(results),
            total_results=data.get("totalResults", 0),
        )

        return results

    async def get_recipe_by_id(self, recipe_id: int) -> dict[str, Any] | None:
        """
        Récupère les détails complets d'une recette par son ID Spoonacular.

        Args:
            recipe_id: ID numérique Spoonacular de la recette.

        Returns:
            Dict avec toutes les données de la recette, ou None si non trouvée.
        """
        try:
            data = await self._get(
                f"/recipes/{recipe_id}/information",
                params={"includeNutrition": False},
            )
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.debug("spoonacular_recipe_not_found", recipe_id=recipe_id)
                return None
            raise

    def convert_to_raw_recipe(self, spoonacular_data: dict[str, Any]) -> RawRecipe:
        """
        Convertit une réponse Spoonacular en RawRecipe.

        La conversion respecte le format interne — les champs non disponibles
        sont laissés à None (le normalizer gère les valeurs manquantes).

        Args:
            spoonacular_data: Dict retourné par l'API Spoonacular.

        Returns:
            RawRecipe compatible avec le pipeline RECIPE_SCOUT.
        """
        # Ingrédients : format "quantité + unité + nom"
        ingredients_raw: list[str] = []
        for ing in spoonacular_data.get("extendedIngredients", []):
            original = ing.get("original", "")
            if original:
                ingredients_raw.append(original)

        # Instructions : extraction des étapes
        instructions_raw: list[str] = []
        for instruction_block in spoonacular_data.get("analyzedInstructions", []):
            for step in instruction_block.get("steps", []):
                step_text = step.get("step", "")
                if step_text:
                    instructions_raw.append(step_text)

        # Si pas d'instructions analysées, utiliser le résumé HTML
        if not instructions_raw and spoonacular_data.get("instructions"):
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(spoonacular_data["instructions"], "lxml")
            instructions_raw = [
                p.get_text(strip=True)
                for p in soup.find_all(["p", "li"])
                if p.get_text(strip=True)
            ]

        # Cuisines Spoonacular → cuisine_type
        cuisines = spoonacular_data.get("cuisines", [])
        cuisine_type = cuisines[0].lower() if cuisines else None

        # Diets → tags
        diets = spoonacular_data.get("diets", [])
        dish_types = spoonacular_data.get("dishTypes", [])
        tags_raw = diets + dish_types

        return RawRecipe(
            title=spoonacular_data.get("title", ""),
            source_url=spoonacular_data.get("sourceUrl", ""),
            source_name="spoonacular",
            ingredients_raw=ingredients_raw,
            instructions_raw=instructions_raw,
            prep_time_min=spoonacular_data.get("preparationMinutes"),
            cook_time_min=spoonacular_data.get("cookingMinutes"),
            servings=spoonacular_data.get("servings"),
            difficulty=None,  # Spoonacular n'a pas de champ difficulté
            photo_url=spoonacular_data.get("image"),
            rating=spoonacular_data.get("spoonacularScore"),
            cuisine_type=cuisine_type,
            tags_raw=tags_raw,
            extra={"spoonacular_id": spoonacular_data.get("id")},
        )
