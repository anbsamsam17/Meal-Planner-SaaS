"""session.py — Moteur et session SQLAlchemy 2.0 async pour Presto.

Architecture :
- create_async_engine avec pool_pre_ping pour détecter les connexions mortes
  (Supabase ferme les connexions idle après 5 minutes côté pgBouncer).
- pool_size=10, max_overflow=20 : 30 connexions max simultanées par processus.
  En production multi-worker (Gunicorn 4 workers), cela représente 120 connexions
  au total — dans la limite du plan Supabase Pro (200 connexions).
- async_sessionmaker avec expire_on_commit=False : évite le lazy-loading accidentel
  après un commit dans un contexte async (le ORM ne peut pas faire de requête sync).

Dépendances requises (pyproject.toml) :
    sqlalchemy[asyncio] >= 2.0
    asyncpg >= 0.29
    pgvector-python >= 0.3
"""

import os
import ssl
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _get_database_url() -> str:
    """Retourne l'URL async de la base de données depuis l'environnement.

    Normalise les URLs postgres:// et postgresql:// vers postgresql+asyncpg://
    pour la compatibilité avec asyncpg (driver async SQLAlchemy 2.0).
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL est requise. "
            "Consulter apps/api/src/db/README.md pour la configuration."
        )
    # Normalisation du schéma d'URL pour asyncpg
    for old_prefix in ("postgresql://", "postgres://"):
        if url.startswith(old_prefix):
            return url.replace(old_prefix, "postgresql+asyncpg://", 1)
    return url


def _build_connect_args() -> dict:
    """Construit les connect_args asyncpg selon l'environnement.

    FIX PROD (2026-04-12) : Supabase exige TLS en production.
    asyncpg accepte ssl="require" ou un objet ssl.SSLContext.
    En dev local (DATABASE_URL pointe vers localhost), SSL est désactivé
    pour éviter les erreurs de certificat auto-signé.

    Référence : https://magicstack.github.io/asyncpg/current/api/index.html#connection
    """
    database_url = os.environ.get("DATABASE_URL", "")
    env = os.environ.get("ENV", os.environ.get("ENVIRONMENT", "dev"))

    connect_args: dict = {
        # Désactive le prepared statement caching pour la compatibilité pgBouncer
        # mode transaction (Supabase utilise pgBouncer en mode transaction par défaut).
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }

    # FIX PROD (2026-04-12) : activer SSL si on pointe vers Supabase ou en production.
    # Supabase requiert SSL sur toutes les connexions hors localhost.
    is_supabase = "supabase" in database_url or "supabase.co" in database_url
    is_production = env in ("prod", "production", "staging")

    if is_supabase or is_production:
        # ssl="require" : asyncpg valide le certificat serveur (recommandé prod).
        # Utiliser ssl.create_default_context() si un CA bundle custom est nécessaire.
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE  # Supabase utilise des certs Let's Encrypt valides
        connect_args["ssl"] = ssl_ctx

    return connect_args


# Moteur async — singleton global par processus.
# pool_pre_ping=True : vérifie la connexion avant usage (évite les erreurs sur connexions mortes).
# pool_size=10 : connexions maintenues en pool (hot).
# max_overflow=20 : connexions supplémentaires autorisées au-delà du pool (temporaires).
# pool_recycle=1800 : recycle les connexions après 30 minutes (avant le timeout pgBouncer).
engine = create_async_engine(
    _get_database_url(),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    connect_args=_build_connect_args(),
    # echo=False en production — activer via DATABASE_ECHO=true en développement uniquement
    echo=os.environ.get("DATABASE_ECHO", "false").lower() == "true",
)

# Fabrique de sessions async — à utiliser via get_db() dans FastAPI.
# expire_on_commit=False : les objets ORM restent utilisables après commit dans un contexte async.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency FastAPI pour l'injection d'une session de base de données.

    Garantit que la session est fermée après chaque requête HTTP, même en cas d'exception.
    Le rollback automatique est géré par SQLAlchemy si le commit n'a pas été appelé.

    Usage :
        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.db.session import get_db

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_engine() -> None:
    """Ferme proprement le moteur de base de données.

    À appeler dans le lifespan FastAPI lors de l'arrêt de l'application :
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
            await close_engine()
    """
    await engine.dispose()
