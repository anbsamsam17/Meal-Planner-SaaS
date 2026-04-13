"""
Client HTTP async pour l'API Edamam Recipe Search.

Edamam fournit ~2M de recettes avec données nutritionnelles précises.
Particulièrement utile pour la couverture internationale et les données nutrition.

Documentation API : https://developer.edamam.com/edamam-docs-recipe-api

Authentification : APP_ID + APP_KEY dans les paramètres de requête.
Quota : dépend du plan (Developer gratuit : 10 req/min, 10 000 req/mois).
"""

import os
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

EDAMAM_BASE_URL = "https://api.edamam.com/api/recipes/v2"


class EdamamAPIError(Exception):
    """Levée pour les erreurs HTTP de l'API Edamam."""
    pass


class EdamamClient:
    """
    Client async pour l'API Edamam Recipe Search v2.

    Usage :
        async with EdamamClient() as client:
            recipes = await client.search_recipes("chicken tikka masala")
    """

    def __init__(
        self,
        app_id: str | None = None,
        app_key: str | None = None,
    ) -> None:
        """
        Initialise le client Edamam.

        Args:
            app_id: Application ID Edamam. Si None, lit EDAMAM_APP_ID.
            app_key: Application Key Edamam. Si None, lit EDAMAM_APP_KEY.
        """
        self.app_id = app_id or os.getenv("EDAMAM_APP_ID", "")
        self.app_key = app_key or os.getenv("EDAMAM_APP_KEY", "")

        if not self.app_id or not self.app_key:
            raise ValueError(
                "EDAMAM_APP_ID et EDAMAM_APP_KEY sont obligatoires. "
                "Définir les variables d'environnement."
            )

        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "EdamamClient":
        """Ouvre la connexion HTTP persistante."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                "Accept": "application/json",
                "Accept-Language": "fr",
                "User-Agent": "PrestoBot/1.0 (+https://presto.fr/bot)",
            },
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Ferme la connexion HTTP proprement."""
        if self._client:
            await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        reraise=True,
    )
    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Effectue une requête GET avec authentification et retry.

        Args:
            params: Paramètres de la requête (sans les credentials).

        Returns:
            Corps JSON de la réponse Edamam.

        Raises:
            EdamamAPIError pour les erreurs HTTP non récupérables.
        """
        if self._client is None:
            raise RuntimeError(
                "Utiliser le client dans un contexte async with."
            )

        full_params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "type": "public",
            **params,
        }

        logger.debug("edamam_request", endpoint=EDAMAM_BASE_URL, params_keys=list(params.keys()))

        response = await self._client.get(EDAMAM_BASE_URL, params=full_params)

        if response.status_code == 401:
            raise EdamamAPIError(
                "Authentification Edamam échouée (HTTP 401). "
                "Vérifier EDAMAM_APP_ID et EDAMAM_APP_KEY."
            )

        if response.status_code == 429:
            logger.warning("edamam_rate_limited")
            raise httpx.HTTPStatusError(
                "Edamam rate limit (429)",
                request=response.request,
                response=response,
            )

        response.raise_for_status()
        return response.json()

    async def search_recipes(
        self,
        query: str,
        max_results: int = 20,
        diet: str | None = None,
        health: list[str] | None = None,
        cuisine_type: str | None = None,
        meal_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recherche des recettes par mots-clés.

        Args:
            query: Terme de recherche.
            max_results: Nombre max de résultats (max 20 par appel Edamam).
            diet: Filtre régime (ex: "balanced", "low-fat", "vegetarian").
            health: Labels de santé (ex: ["vegan", "gluten-free"]).
            cuisine_type: Type de cuisine (ex: "french", "japanese").
            meal_type: Type de repas (ex: "dinner", "lunch").

        Returns:
            Liste de dicts avec les données brutes Edamam (field "recipe").
        """
        params: dict[str, Any] = {
            "q": query,
        }

        if diet:
            params["diet"] = diet
        if health:
            params["health"] = health  # Liste acceptée par httpx
        if cuisine_type:
            params["cuisineType"] = cuisine_type
        if meal_type:
            params["mealType"] = meal_type

        data = await self._get(params)

        hits = data.get("hits", [])
        recipes_raw = [hit["recipe"] for hit in hits if "recipe" in hit]

        logger.info(
            "edamam_search",
            query=query,
            results_count=len(recipes_raw),
            total_results=data.get("count", 0),
        )

        return recipes_raw[:max_results]

    async def get_next_page(self, next_page_url: str) -> list[dict[str, Any]]:
        """
        Récupère la page suivante des résultats Edamam.

        Edamam utilise des URLs de pagination dans le champ "_links.next.href".

        Args:
            next_page_url: URL complète de la prochaine page.

        Returns:
            Liste de dicts de recettes.
        """
        if self._client is None:
            raise RuntimeError("Utiliser le client dans un contexte async with.")

        response = await self._client.get(next_page_url)
        response.raise_for_status()
        data = response.json()

        hits = data.get("hits", [])
        return [hit["recipe"] for hit in hits if "recipe" in hit]

    def convert_to_raw_recipe(self, edamam_recipe: dict[str, Any]) -> RawRecipe:
        """
        Convertit une recette Edamam en RawRecipe.

        Args:
            edamam_recipe: Dict du champ "recipe" d'un résultat Edamam.

        Returns:
            RawRecipe compatible avec le pipeline RECIPE_SCOUT.
        """
        # Ingrédients : Edamam fournit "ingredientLines" (lignes brutes)
        ingredients_raw: list[str] = edamam_recipe.get("ingredientLines", [])

        # Instructions : Edamam ne fournit PAS les étapes — lien vers la source uniquement
        # La source URL sera utilisée pour un scraping ultérieur si nécessaire
        instructions_raw: list[str] = []

        # Source URL : Edamam donne l'URL de la recette originale
        source_url = edamam_recipe.get("url", "")
        source_label = edamam_recipe.get("source", "edamam")

        # Cuisine type : Edamam fournit une liste
        cuisine_types = edamam_recipe.get("cuisineType", [])
        cuisine_type = cuisine_types[0] if cuisine_types else None

        # Diet labels → tags
        diet_labels = edamam_recipe.get("dietLabels", [])
        health_labels = edamam_recipe.get("healthLabels", [])
        meal_type = edamam_recipe.get("mealType", [])
        tags_raw = diet_labels + health_labels + meal_type

        # Temps de cuisson : Edamam fournit totalTime en minutes
        total_time = edamam_recipe.get("totalTime")
        cook_time_min: int | None = int(total_time) if total_time and total_time > 0 else None

        # Photo
        photo_url = (
            edamam_recipe.get("image")
            or (edamam_recipe.get("images", {}).get("LARGE", {}).get("url"))
        )

        return RawRecipe(
            title=edamam_recipe.get("label", ""),
            source_url=source_url,
            source_name=f"edamam_{source_label.lower().replace(' ', '_')}",
            ingredients_raw=ingredients_raw,
            instructions_raw=instructions_raw,  # Vide — Edamam ne fournit pas les instructions
            prep_time_min=None,  # Edamam ne distingue pas prep/cook time
            cook_time_min=cook_time_min,
            servings=edamam_recipe.get("yield"),
            difficulty=None,  # Edamam n'a pas de champ difficulté
            photo_url=photo_url,
            rating=None,
            cuisine_type=cuisine_type,
            tags_raw=tags_raw,
            extra={
                "edamam_uri": edamam_recipe.get("uri"),
                "calories": edamam_recipe.get("calories"),
                # Les instructions nécessitent un scraping de source_url
                "requires_scraping": not bool(instructions_raw),
            },
        )
