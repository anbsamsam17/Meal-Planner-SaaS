"""
Point d'entrée FastAPI — Presto API.

Ce fichier configure :
- L'application FastAPI avec ses métadonnées OpenAPI
- Le lifespan (startup/shutdown) : pool DB, Redis, modèle ML
- Les middlewares : CORS, correlation ID, SlowAPI rate limiting
- Les routers v1
- Sentry (si SENTRY_DSN défini)

Architecture lifespan :
  Au démarrage : connexion DB pool (asyncpg), connexion Redis, chargement
  sentence-transformers (singleton en mémoire). Le modèle prend ~3-5s à charger.
  C'est pourquoi /ready répond 503 jusqu'à la fin du chargement.

  À l'arrêt : fermeture propre des connexions (graceful shutdown SIGTERM).
"""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.ext.asyncio import (  # utilisé en fallback si src.db.session absent
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import src.core.rate_limit as _rate_limit_module
from src.api.v1.router import api_v1_router
from src.core.config import get_settings
from src.core.logging import set_correlation_id, setup_logging
from src.core.rate_limit import create_limiter, rate_limit_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gestionnaire de cycle de vie FastAPI.

    Startup :
    1. Configure loguru selon l'environnement
    2. Initialise Sentry si SENTRY_DSN défini
    3. Connecte le pool de connexions PostgreSQL (asyncpg)
    4. Connecte Redis (rate limiting + cache futur)
    5. Charge le modèle sentence-transformers (singleton)
    6. Marque app.state.model_loaded = True → /ready répond 200

    Shutdown :
    - Ferme le pool DB (libère les connexions)
    - Ferme la connexion Redis
    - Décharge le modèle ML de la mémoire
    """
    settings = get_settings()

    # ---- Configuration du logging ----
    setup_logging(log_level=settings.LOG_LEVEL, env=settings.ENV)
    logger.info(
        "api_startup",
        env=settings.ENV,
        log_level=settings.LOG_LEVEL,
        port=settings.PORT,
    )

    # ---- Sentry (monitoring erreurs) ----
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.ENV,
                integrations=[FastApiIntegration(), SqlalchemyIntegration()],
                # Ne pas envoyer les événements de debug en dev
                traces_sample_rate=0.1 if settings.ENV == "prod" else 0.0,
            )
            logger.info("sentry_initialized", env=settings.ENV)
        except ImportError:
            logger.warning("sentry_sdk_not_installed", hint="pip install sentry-sdk")

    # ---- Pool de connexions PostgreSQL ----
    # Utilise le moteur et la session factory créés par database-administrator (src/db/session.py).
    # Évite de créer un second pool de connexions redondant.
    try:
        from src.db.session import AsyncSessionLocal
        from src.db.session import engine as db_engine
        app.state.db_engine = db_engine
        app.state.db_session_factory = AsyncSessionLocal
        logger.info("database_pool_connected_from_db_module")
    except ImportError:
        # Fallback : créer le pool directement si src.db.session n'est pas disponible
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
            echo=settings.ENV == "dev",
        )
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        app.state.db_engine = engine
        app.state.db_session_factory = session_factory
        logger.info("database_pool_connected_fallback", database_url=settings.DATABASE_URL[:50])

    # ---- Redis ----
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    app.state.redis = redis_client
    logger.info("redis_connected", redis_url=settings.REDIS_URL)

    # ---- Rate limiter (slowapi) ----
    # FIX Phase 1 mature (review 2026-04-12) : le singleton module-level est réassigné
    # avec l'URI Redis réelle après connexion, pour que les décorateurs @limiter.limit()
    # utilisent le bon storage Redis (et non le fallback mémoire du module-level).
    limiter = create_limiter(
        redis_url=settings.REDIS_URL,
        redis_db=settings.RATE_LIMIT_REDIS_DB,
    )
    _rate_limit_module.limiter = limiter
    app.state.limiter = limiter

    # ---- Modèle sentence-transformers (singleton) ----
    # Le modèle all-MiniLM-L6-v2 pèse ~90MB sur disque, ~350MB en RAM.
    # Il est chargé une seule fois au démarrage et partagé entre toutes les requêtes.
    # Tant qu'il n'est pas chargé, /ready retourne 503 (pattern Railway readiness).
    app.state.model_loaded = False
    try:
        from sentence_transformers import SentenceTransformer

        logger.info("model_loading", model="all-MiniLM-L6-v2")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        app.state.embedding_model = model
        app.state.model_loaded = True
        logger.info("model_loaded", model="all-MiniLM-L6-v2", dim=384)
    except ImportError:
        # sentence-transformers non installé (tests unitaires légers)
        # L'API démarre quand même, mais /ready signalera model=False
        logger.warning(
            "sentence_transformers_not_installed",
            hint="Installer sentence-transformers pour activer les embeddings",
        )
        app.state.model_loaded = True  # En mode dégradé, on laisse passer
    except Exception as exc:
        logger.error("model_loading_failed", error=str(exc))
        # Ne pas bloquer le démarrage — /ready retournera 503
        app.state.model_loaded = False

    logger.info("api_ready", env=settings.ENV)

    yield  # L'application est prête à recevoir du trafic

    # ---- Shutdown ----
    logger.info("api_shutdown_start")

    try:
        from src.db.session import close_engine
        await close_engine()
    except ImportError:
        if hasattr(app.state, "db_engine"):
            await app.state.db_engine.dispose()
    logger.info("database_pool_closed")

    await redis_client.aclose()
    logger.info("redis_closed")

    if hasattr(app.state, "embedding_model"):
        del app.state.embedding_model
    app.state.model_loaded = False

    logger.info("api_shutdown_complete")


def create_app() -> FastAPI:
    """
    Factory de l'application FastAPI.

    Séparer la création de l'app de son démarrage facilite les tests
    (on peut créer une app de test sans démarrer le lifespan).
    """
    settings = get_settings()

    app = FastAPI(
        title="Presto API",
        version="0.1.0",
        description=(
            "API REST de Presto — le livre de recettes de votre famille, réinventé par Presto. "
            "Gère les foyers, les recettes, les plans semaine et les listes de courses. "
            "Documentation complète : https://docs.presto.fr"
        ),
        lifespan=lifespan,
        # Désactiver les docs en production pour réduire la surface d'attaque
        docs_url="/docs" if settings.ENV != "prod" else None,
        redoc_url="/redoc" if settings.ENV != "prod" else None,
        openapi_url="/openapi.json" if settings.ENV != "prod" else None,
    )

    # ---- Middleware CORS ----
    # FIX #8 (review Phase 1 2026-04-12) : allow_headers=["*"] + allow_credentials=True
    # est rejeté par la spec CORS des navigateurs modernes (Chrome, Firefox, Safari).
    # La spec CORS interdit l'wildcard headers quand credentials=True.
    # Liste explicite des headers autorisés.
    #
    # FIX PROD (2026-04-12) : log des origines configurées au démarrage pour diagnostic Railway.
    # Permet de vérifier que CORS_ORIGINS est bien parsé (pas d'espace, pas de / final).
    #
    # FIX CORS PROD (2026-04-12) : hardcoder les domaines critiques EN PLUS de la variable d'env.
    # Protège contre un CORS_ORIGINS mal parsé sur Railway (espace, guillemet, / final).
    # Ces domaines sont toujours autorisés même si CORS_ORIGINS est vide ou mal configuré.
    _ALWAYS_ALLOWED_ORIGINS = [
        "https://hop-presto-saas-sa.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    cors_origins = list(settings.cors_origins_list)
    for _origin in _ALWAYS_ALLOWED_ORIGINS:
        if _origin not in cors_origins:
            cors_origins.append(_origin)

    logger.info(
        "cors_origins_configured",
        origins=cors_origins,
        raw_value=settings.CORS_ORIGINS,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Correlation-ID",
            "X-Request-ID",
        ],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After", "X-Correlation-ID"],
        max_age=600,
    )

    # ---- Middleware Correlation ID ----
    # Injecte un ID unique dans chaque requête pour le tracing distribué.
    # Le même ID est propagé dans les logs de la requête ET dans les tâches Celery.
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next: Any) -> Any:
        """
        Middleware qui assigne un correlation ID unique à chaque requête.

        Priorité : utilise le header X-Correlation-ID si fourni par le client
        (utile pour le tracing entre services), sinon génère un nouveau UUID court.
        """
        correlation_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex[:8]
        set_correlation_id(correlation_id)
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    # ---- Middleware SlowAPI (rate limiting) ----
    app.add_middleware(SlowAPIMiddleware)

    # ---- Handler global 429 ----
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)  # type: ignore[arg-type]

    # ---- Handler global erreurs non gérées ----
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all pour les erreurs non anticipées.

        Log l'erreur complète (avec traceback) et retourne un 500 générique
        sans exposer les détails internes à l'utilisateur.
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.exception(
            "unhandled_exception",
            correlation_id=correlation_id,
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "Une erreur inattendue s'est produite. "
                "Notre équipe a été notifiée automatiquement.",
                "correlation_id": correlation_id,
            },
        )

    # ---- Routers ----
    app.include_router(api_v1_router)

    return app


# Instance de l'application — importée par uvicorn
app = create_app()
