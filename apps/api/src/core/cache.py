"""
Cache Redis centralisé pour Presto API.

Ce module résout deux problèmes de performance :

PERF-01 — Latence Redis élevée (801ms) :
  La connexion `aioredis.from_url()` sans pool explicite crée une nouvelle
  connexion TCP à chaque requête. Un ConnectionPool partagé (singleton) maintient
  des connexions réutilisables → latence < 10ms en régime établi.

PERF-02 — Pas de cache sur les endpoints recettes :
  591 recettes quasi-statiques → full scan PostgreSQL à chaque GET.
  Le helper `cache_response()` implémente le pattern cache-aside :
    1. Lecture Redis (hit → retour immédiat, pas de hit DB)
    2. Si miss → query DB, stockage Redis avec TTL, retour
    3. Si Redis down → fallback transparent sur DB (fail-open)

Politique de clés :
  Préfixe : `presto:cache:`
  Exemples :
    presto:cache:recipe:550e8400-e29b-41d4-a716-446655440000  (TTL 1h)
    presto:cache:recipes:q=poulet&page=1&per_page=20          (TTL 5min)

Invalidation :
  TODO(scraper) : appeler `await invalidate_recipes_cache(redis)` après chaque
  import de nouvelles recettes dans le worker (apps/worker/src/scripts/).
  Point d'entrée suggéré : apps/worker/src/scripts/scrape_*.py après bulk insert.
"""

import json
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import redis.asyncio as aioredis
from loguru import logger

# FIX BUG P0 (2026-04-16) : syntaxe `async def cache_response[T]` (PEP 695)
# incompatible avec Python 3.11. Remplacé par TypeVar classique (compatible 3.9+).
T = TypeVar("T")

# -------------------------------------------------------------------------
# Configuration des TTLs (en secondes)
# -------------------------------------------------------------------------
CACHE_TTL_RECIPE_DETAIL = 3600      # 1h — recette individuelle (quasi-statique)
CACHE_TTL_RECIPE_LIST = 300         # 5min — liste/recherche (pagination volatile)

# Préfixe de namespace pour éviter les collisions avec d'autres clés Redis
CACHE_KEY_PREFIX = "presto:cache:"


# -------------------------------------------------------------------------
# PERF-01 — Singleton Redis avec ConnectionPool
# -------------------------------------------------------------------------

def create_redis_pool(redis_url: str) -> aioredis.Redis:
    """
    Crée un client Redis avec un ConnectionPool partagé.

    Un ConnectionPool maintient un ensemble de connexions TCP réutilisables,
    évitant la latence de handshake TCP+TLS (~500-800ms) à chaque requête.

    Configuration du pool :
      - max_connections=20 : aligné avec pool_size DB (10) + overflow (10).
        Au-delà, les requêtes attendent qu'une connexion se libère.
      - socket_timeout=2.0 : timeout lecture Redis — évite les blocages si Redis lag.
      - socket_connect_timeout=2.0 : timeout connexion initiale.
      - retry_on_timeout=True : une tentative de reconnexion automatique.
      - health_check_interval=30 : vérifie les connexions idle toutes les 30s.

    Args:
        redis_url: URL Redis (ex: redis://localhost:6379 ou rediss://...).

    Returns:
        Client Redis async avec pool de connexions configuré.
    """
    pool = aioredis.ConnectionPool.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
        socket_timeout=2.0,
        socket_connect_timeout=2.0,
        retry_on_timeout=True,
        health_check_interval=30,
    )
    return aioredis.Redis(connection_pool=pool)


# -------------------------------------------------------------------------
# PERF-02 — Helper cache-aside avec fallback gracieux
# -------------------------------------------------------------------------

def _build_cache_key(key_suffix: str) -> str:
    """Construit la clé Redis complète avec le préfixe de namespace."""
    return f"{CACHE_KEY_PREFIX}{key_suffix}"


async def cache_response(
    redis: aioredis.Redis | None,
    cache_key: str,
    ttl: int,
    fallback: Callable[[], Awaitable[T]],
) -> T:
    """
    Pattern cache-aside générique avec fallback gracieux sur DB.

    Algorithme :
      1. Si Redis est None ou indisponible → exécuter fallback directement.
      2. Tentative de lecture Redis (GET) :
         - Hit → désérialiser JSON et retourner (0 hit DB).
         - Miss → exécuter fallback (query DB).
      3. Stocker le résultat en Redis (SETEX) avec le TTL fourni.
      4. Toute erreur Redis → log WARNING + exécuter fallback (jamais de 500).

    Le paramètre `cache_key` doit déjà contenir le préfixe `presto:cache:`.
    Utilise `_build_cache_key()` pour construire la clé depuis un suffix.

    Args:
        redis: Client Redis async (peut être None en mode test sans Redis).
        cache_key: Clé Redis complète (avec préfixe).
        ttl: Durée de vie en secondes (ex: CACHE_TTL_RECIPE_DETAIL).
        fallback: Coroutine async à appeler si le cache est vide ou indisponible.

    Returns:
        Résultat sérialisable en JSON (dict, list, etc.).
    """
    # Redis non configuré (ex: tests unitaires sans Redis) → bypass
    if redis is None:
        return await fallback()

    # ---- Tentative de lecture du cache ----
    try:
        cached_raw = await redis.get(cache_key)
        if cached_raw is not None:
            logger.debug("cache_hit", key=cache_key)
            return json.loads(cached_raw)  # type: ignore[return-value]
    except Exception as exc:
        # Redis down ou erreur réseau — on continue vers le fallback
        logger.warning("cache_read_error", key=cache_key, error=str(exc))

    # ---- Cache miss ou Redis indisponible → exécuter le fallback ----
    result = await fallback()

    # ---- Stockage en cache (best-effort — jamais bloquant) ----
    try:
        await redis.setex(
            cache_key,
            ttl,
            json.dumps(result, default=str),  # default=str pour UUID/datetime
        )
        logger.debug("cache_set", key=cache_key, ttl=ttl)
    except Exception as exc:
        # Écriture échouée — le résultat est quand même retourné
        logger.warning("cache_write_error", key=cache_key, error=str(exc))

    return result


def build_recipe_detail_key(recipe_id: str) -> str:
    """Clé cache pour le détail d'une recette (TTL 1h)."""
    return _build_cache_key(f"recipe:{recipe_id}")


def build_recipe_list_key(
    q: str,
    page: int,
    per_page: int,
    cuisine: str | None,
    max_time: int | None,
    budget: str | None,
    min_difficulty: int | None,
    max_difficulty: int | None,
    diet: list[str] | None,
    season: str | None,
    course: str | None = None,
) -> str:
    """
    Clé cache pour la liste/recherche de recettes (TTL 5min).

    Inclut tous les paramètres de filtre pour garantir l'isolation des résultats.
    Le tri des paramètres diet est stable (sorted) pour que les mêmes filtres
    dans un ordre différent produisent la même clé de cache.
    """
    diet_str = ",".join(sorted(diet)) if diet else ""
    suffix = (
        f"recipes:q={q}&page={page}&per_page={per_page}"
        f"&cuisine={cuisine or ''}&max_time={max_time or ''}"
        f"&budget={budget or ''}&min_diff={min_difficulty or ''}"
        f"&max_diff={max_difficulty or ''}&diet={diet_str}&season={season or ''}"
        f"&course={course or ''}"
    )
    return _build_cache_key(suffix)


async def invalidate_recipes_cache(redis: aioredis.Redis) -> int:
    """
    Invalide toutes les clés de cache recettes.

    À appeler après un import de nouvelles recettes par le scraper.
    Utilise SCAN + DEL en batch pour éviter de bloquer Redis avec KEYS *.

    Args:
        redis: Client Redis async.

    Returns:
        Nombre de clés supprimées.
    """
    pattern = f"{CACHE_KEY_PREFIX}recipe*"
    deleted = 0
    try:
        async for key in redis.scan_iter(pattern, count=100):
            await redis.delete(key)
            deleted += 1
        logger.info("cache_invalidated_recipes", deleted=deleted, pattern=pattern)
    except Exception as exc:
        logger.error("cache_invalidation_error", pattern=pattern, error=str(exc))
    return deleted


# -------------------------------------------------------------------------
# Helpers de sérialisation Pydantic → dict JSON-safe
# -------------------------------------------------------------------------

def pydantic_to_cache(model: Any) -> dict[str, Any]:
    """
    Convertit un modèle Pydantic en dict JSON-serialisable pour le cache.

    Utilise model_dump() de Pydantic v2 avec mode='json' pour que les UUID
    et datetime soient sérialisés en string (compatible json.dumps).
    """
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")  # Pydantic v2
    return dict(model)  # fallback dict brut
