"""
Rate limiting multi-niveau avec slowapi + Redis.

5 niveaux configurés (voir phase-0/infra/12-rate-limiting-design.md) :
  Niveau 1 — IP : 60 req/min (endpoints publics)
  Niveau 2 — User lecture : 300 req/min, écriture : 30 req/min
  Niveau 3 — Tenant (household) : 1000 req/min agrégés
  Niveau 4 — LLM coûteux : 10/h plan, 20/h recette, 5/h pdf (par user)
  Niveau 5 — Webhooks : 120 req/min (par IP source)

Stratégie fail-open : si Redis est indisponible, les requêtes passent
sans être comptées. Mieux vaut facturer légèrement plus que bloquer
le service pour tous les utilisateurs.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def get_user_key(request: Request) -> str:
    """
    Clé de rate limiting basée sur l'identité authentifiée.

    Niveau 2 : distingue chaque utilisateur individuellement.
    Fallback sur l'IP si l'utilisateur n'est pas authentifié (endpoints publics).

    Returns:
        Chaîne unique identifiant l'utilisateur ou l'IP.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


def get_household_key(request: Request) -> str:
    """
    Clé de rate limiting basée sur le tenant (household_id).

    Niveau 3 : agrège toutes les requêtes d'un foyer.
    Un foyer de 8 membres partage le quota tenant — empêche la monopolisation.
    Fallback sur l'IP si pas de contexte tenant (endpoint public).

    Returns:
        Chaîne unique identifiant le tenant ou l'IP.
    """
    household_id = getattr(request.state, "household_id", None)
    if household_id:
        return f"household:{household_id}"
    return f"ip:{get_remote_address(request)}"


def get_ip_key(request: Request) -> str:
    """
    Clé de rate limiting basée sur l'adresse IP.

    Niveau 1 : protection anti-bot sur les endpoints publics.
    En environnement Railway/Cloudflare, l'IP réelle est dans CF-Connecting-IP
    ou X-Forwarded-For. get_remote_address() de slowapi gère ce cas.

    Returns:
        Adresse IP de la requête.
    """
    return f"ip:{get_remote_address(request)}"


def _build_storage_uri(redis_url: str, redis_db: int) -> str:
    """
    Construit l'URI du storage Redis pour slowapi.

    Isole le rate limiting sur la DB Redis 1 (DB 0 = Celery broker).
    Garantit que les compteurs de rate limit ne sont pas évincés par
    la politique volatile-lru du broker Celery.

    Args:
        redis_url: URL Redis de base (sans numéro de base).
        redis_db: Numéro de la base Redis dédiée au rate limiting.

    Returns:
        URI complète pour slowapi (ex: redis://localhost:6379/1).
    """
    # Retire le numéro de DB existant si présent dans l'URL
    base_url = redis_url.rstrip("/")
    # Si l'URL se termine par /<chiffre>, le remplacer
    parts = base_url.rsplit("/", 1)
    if len(parts) == 2 and parts[1].isdigit():
        base_url = parts[0]
    return f"{base_url}/{redis_db}"


def create_limiter(redis_url: str = "redis://localhost:6379", redis_db: int = 1) -> Limiter:
    """
    Crée l'instance singleton du rate limiter slowapi.

    Configuré avec :
    - Strategy fixed-window-elastic-expiry (sliding window approximée)
    - Fail-open : si Redis est down, les requêtes passent (pas de 500)
    - Key func par défaut : user_id (niveau 2 lecture)

    Args:
        redis_url: URL Redis de base.
        redis_db: Numéro de la base Redis pour le rate limiting.

    Returns:
        Instance Limiter configurée.
    """
    storage_uri = _build_storage_uri(redis_url, redis_db)

    limiter = Limiter(
        key_func=get_user_key,
        storage_uri=storage_uri,
        strategy="fixed-window",
        # Limite par défaut : niveau 2 lecture (300/min par user)
        default_limits=["300/minute"],
        # Fail-open : si Redis est down, on laisse passer
        # Justification : panne Redis = coût légèrement plus élevé,
        # mais meilleur que bloquer tous les utilisateurs pendant la panne
        enabled=True,
    )

    return limiter


# FIX Phase 1 mature (review 2026-04-12)
# Singleton module-level requis pour les décorateurs @limiter.limit() sur les endpoints.
# SlowAPIMiddleware lit app.state.limiter — ce singleton est réassigné dans le lifespan
# (main.py) via app.state.limiter = create_limiter(...) après connexion Redis.
# En attendant le démarrage, cette instance utilise le storage mémoire (fallback).
limiter: Limiter = Limiter(
    key_func=get_user_key,
    default_limits=["300/minute"],
    strategy="fixed-window",
)


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Handler global pour les erreurs de rate limiting (HTTP 429).

    Retourne un JSON structuré en français avec le header Retry-After.
    Log l'événement pour monitoring (Sentry + PostHog via les logs structurés).

    Args:
        request: La requête qui a déclenché la limite.
        exc: L'exception RateLimitExceeded avec les métadonnées de la limite.

    Returns:
        JSONResponse 429 avec headers standards.
    """
    # Extraction du délai de retry depuis l'exception slowapi
    retry_after = getattr(exc, "retry_after", 60)
    if callable(retry_after):
        retry_after = 60  # Fallback si non calculable

    limit_str = "inconnu"
    if hasattr(exc, "limit") and exc.limit:
        limit_str = str(getattr(exc.limit, "limit", "inconnu"))

    # Log structuré pour monitoring — permet de détecter les abus
    logger.warning(
        "rate_limit_hit",
        correlation_id=getattr(request.state, "correlation_id", None),
        user_id=getattr(request.state, "user_id", None),
        household_id=getattr(request.state, "household_id", None),
        endpoint=str(request.url.path),
        method=request.method,
        ip=get_remote_address(request),
        limit=limit_str,
        retry_after=retry_after,
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": (
                f"Vous avez atteint votre limite de requêtes. "
                f"Réessayez dans {retry_after} secondes."
            ),
            "retry_after": retry_after,
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": limit_str,
            "X-RateLimit-Remaining": "0",
        },
    )


# -------------------------------------------------------------------------
# Limites prédéfinies pour utilisation dans les décorateurs @limiter.limit()
# -------------------------------------------------------------------------

# Niveau 1 — IP (endpoints publics : /auth/*, /health, /ready)
LIMIT_IP_PUBLIC = "60/minute"

# Niveau 2 — User authentifié
LIMIT_USER_READ = "300/minute"
LIMIT_USER_WRITE = "30/minute"

# Niveau 3 — Tenant (household)
LIMIT_TENANT = "1000/minute"

# Niveau 4 — LLM coûteux (par user)
LIMIT_LLM_PLAN_USER = "10/hour"
LIMIT_LLM_RECIPE_USER = "20/hour"
LIMIT_LLM_PDF_USER = "5/hour"

# Niveau 4 — LLM coûteux (par tenant)
LIMIT_LLM_PLAN_TENANT = "50/hour"
LIMIT_LLM_RECIPE_TENANT = "100/hour"

# Niveau 5 — Webhooks
LIMIT_WEBHOOK = "120/minute"
