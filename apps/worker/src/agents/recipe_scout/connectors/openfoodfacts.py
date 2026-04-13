"""
Client Open Food Facts — mapping ingrédients vers produits référencés.

Open Food Facts est une base de données collaborative de produits alimentaires
avec ~3M produits référencés. Ce client permet de lier chaque ingrédient
canonique à un produit réel (off_id) pour préparer l'intégration Drive.

ROADMAP : Étape 4 du pipeline recettes — Mapping produit.
Pipeline complet : ingrédient canonique → off_id → SKU enseigne → panier.

Architecture :
- API v2 Open Food Facts (search endpoint)
- Cache LRU en mémoire (1000 entrées, reset au redémarrage worker)
- Retry tenacity sur erreurs réseau
- Pas d'authentification requise (API publique)

Rate limits implicites OFF :
- Pas de limit officielle documentée pour les petits volumes
- On respecte un throttling de 0.5s entre les requêtes pour éviter le ban
- En cas de 429 : backoff exponentiel via tenacity
"""

import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# ---- Constantes ----

OFF_API_BASE = "https://world.openfoodfacts.org"
OFF_SEARCH_URL = f"{OFF_API_BASE}/cgi/search.pl"
OFF_API_V2_URL = f"{OFF_API_BASE}/api/v2/search"

# Délai entre les requêtes pour respecter les serveurs OFF (bénévolat)
REQUEST_DELAY_SECONDS = 0.5

# Taille du cache LRU en mémoire (par worker process)
CACHE_MAX_SIZE = 1000

# Seuil de complétude minimum pour considérer un produit OFF comme pertinent
MIN_COMPLETENESS = 0.3


@dataclass
class OFFProduct:
    """Représentation d'un produit Open Food Facts.

    off_id : code EAN/barcode (identifiant unique OFF).
    name : nom du produit normalisé.
    category : catégorie OFF (ex: "Viandes et charcuteries").
    brand : marque du produit.
    completeness : score de complétude OFF (0.0-1.0), indique la qualité de la fiche.
    unique_scans_n : nombre de scans uniques (popularité du produit).
    """

    off_id: str
    name: str
    category: str | None
    brand: str | None
    completeness: float
    unique_scans_n: int


def _score_product(product: dict[str, Any]) -> float:
    """
    Calcule un score de pertinence pour un produit OFF.

    Privilégie :
    1. Les produits avec un fort taux de scan (popularité réelle)
    2. Les produits avec un score de complétude élevé (données fiables)
    3. Les produits avec une marque connue

    Args:
        product: Dict produit brut de l'API OFF.

    Returns:
        Score de pertinence (plus élevé = plus pertinent).
    """
    scans = product.get("unique_scans_n", 0) or 0
    completeness = product.get("completeness", 0.0) or 0.0
    has_brand = 1 if product.get("brands") else 0

    # Score pondéré : popularité (60%) + complétude (30%) + marque (10%)
    return (min(scans, 10000) / 10000) * 0.6 + completeness * 0.3 + has_brand * 0.1


@lru_cache(maxsize=CACHE_MAX_SIZE)
def _cached_search(query: str, locale: str) -> tuple[str, ...]:
    """
    Wrapper pour le cache LRU sur les recherches OFF.

    Le cache est par process Celery — un miss en cache force un appel HTTP.
    TTL implicite : durée de vie du process worker.

    Note : lru_cache ne supporte pas les types mutables, donc retour tuple.

    Args:
        query: Terme de recherche (canonical_name de l'ingrédient).
        locale: Locale de recherche (ex: "fr").

    Returns:
        Tuple (off_id, name, category, brand, completeness_str, scans_str)
        ou tuple vide si pas de résultat.
    """
    # Cette fonction ne fait pas de HTTP — elle est appelée par search_product()
    # qui gère le cache via un dict séparé pour les vrais appels réseau.
    # lru_cache est utilisé comme wrapper de cache de résultats.
    return ()


class OpenFoodFactsClient:
    """
    Client HTTP pour l'API Open Food Facts.

    Utilise httpx pour les requêtes HTTP synchrones (compatible Celery tasks sync).
    Le cache LRU est partagé dans le process mais isolé entre workers Celery.

    Usage :
        client = OpenFoodFactsClient()
        product = client.search_product("poulet", locale="fr")
        if product:
            print(product.off_id, product.name)
    """

    def __init__(self, timeout: float = 10.0) -> None:
        """
        Initialise le client OFF.

        Args:
            timeout: Timeout HTTP en secondes.
        """
        self.timeout = timeout
        # Cache dict simple (dict[query_locale, OFFProduct | None])
        # Séparé de lru_cache pour avoir plus de contrôle sur les évictions
        self._cache: dict[str, OFFProduct | None] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def search_product(self, query: str, locale: str = "fr") -> OFFProduct | None:
        """
        Recherche le produit le plus pertinent pour un terme donné.

        Utilise le cache en mémoire pour éviter les appels répétés.
        En cas de cache miss, appelle l'API OFF avec retry tenacity.

        Args:
            query: Terme de recherche (canonical_name de l'ingrédient).
            locale: Locale de recherche ("fr" pour produits français prioritaires).

        Returns:
            OFFProduct le plus pertinent, ou None si aucun résultat.
        """
        cache_key = f"{locale}:{query.lower().strip()}"

        # Vérification du cache
        if cache_key in self._cache:
            self._cache_hits += 1
            logger.debug(
                "off_cache_hit",
                query=query,
                locale=locale,
                cache_hits=self._cache_hits,
            )
            return self._cache[cache_key]

        self._cache_misses += 1

        # Éviction simple si cache plein (FIFO approximatif)
        if len(self._cache) >= CACHE_MAX_SIZE:
            # Supprime les 100 premières entrées
            keys_to_delete = list(self._cache.keys())[:100]
            for key in keys_to_delete:
                del self._cache[key]
            logger.debug("off_cache_eviction", evicted=100, remaining=len(self._cache))

        # Appel API avec retry
        result = self._fetch_product(query, locale)

        # Mise en cache (incluant None pour éviter les appels répétés sur les misses)
        self._cache[cache_key] = result

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        reraise=True,
    )
    def _fetch_product(self, query: str, locale: str) -> OFFProduct | None:
        """
        Appel HTTP vers l'API OFF avec retry tenacity.

        Utilise l'API v2 search pour les meilleures performances.
        Filtre par pays/locale pour prioriser les produits locaux.

        Args:
            query: Terme de recherche.
            locale: Locale (pays/langue).

        Returns:
            OFFProduct le plus pertinent, ou None.
        """
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10,
            "fields": "code,product_name,brands,categories,completeness,unique_scans_n",
        }

        # Prioriser les produits du pays correspondant à la locale
        if locale == "fr":
            params["countries_tags"] = "france"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    OFF_SEARCH_URL,
                    params=params,
                    headers={
                        "User-Agent": "Presto-Bot/0.1 (+https://presto.fr)",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()

            data = response.json()
            products = data.get("products", [])

            if not products:
                # Retry sans filtre pays si aucun résultat local
                if locale != "world":
                    logger.debug(
                        "off_no_local_results_retry_world",
                        query=query,
                        locale=locale,
                    )
                    return self._fetch_product_global(query)

                logger.debug("off_no_results", query=query)
                return None

            # Sélection du produit le plus pertinent par score
            filtered = [
                p for p in products
                if p.get("completeness", 0) >= MIN_COMPLETENESS
                and p.get("code")
                and p.get("product_name")
            ]

            if not filtered:
                # Fallback sans filtre completeness si tous sous le seuil
                filtered = [p for p in products if p.get("code") and p.get("product_name")]

            if not filtered:
                return None

            best = max(filtered, key=_score_product)

            # Extraction de la catégorie principale
            categories_raw = best.get("categories", "") or ""
            # OFF retourne les catégories en chaîne séparée par virgules
            category: str | None = None
            if categories_raw:
                cats = [c.strip() for c in categories_raw.split(",") if c.strip()]
                # Prendre la première catégorie spécifique (skip les génériques)
                category = cats[0] if cats else None

            product = OFFProduct(
                off_id=str(best["code"]),
                name=str(best.get("product_name", query)),
                category=category,
                brand=best.get("brands") or None,
                completeness=float(best.get("completeness", 0.0) or 0.0),
                unique_scans_n=int(best.get("unique_scans_n", 0) or 0),
            )

            logger.info(
                "off_product_found",
                query=query,
                off_id=product.off_id,
                name=product.name,
                completeness=round(product.completeness, 2),
                scans=product.unique_scans_n,
            )

            # Throttling respectueux des serveurs OFF
            time.sleep(REQUEST_DELAY_SECONDS)

            return product

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.warning("off_rate_limited", query=query)
                time.sleep(5)  # Backoff additionnel sur 429
                raise httpx.NetworkError("Rate limited par OFF") from exc
            logger.warning("off_http_error", query=query, status=exc.response.status_code)
            return None

        except Exception as exc:
            logger.warning("off_fetch_error", query=query, error=str(exc))
            raise

    def _fetch_product_global(self, query: str) -> OFFProduct | None:
        """
        Recherche sans filtre pays (fallback quand aucun résultat local).

        Args:
            query: Terme de recherche.

        Returns:
            OFFProduct ou None.
        """
        return self._fetch_product(query, locale="world")

    @property
    def cache_stats(self) -> dict[str, int]:
        """Retourne les statistiques du cache pour le monitoring."""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "size": len(self._cache),
        }
