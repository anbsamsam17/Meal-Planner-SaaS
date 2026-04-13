"""
session.py — Moteur et session SQLAlchemy async pour apps/worker.

FIX #1 (review Phase 1 2026-04-12) : expose AsyncSessionLocal et engine
pour que le worker puisse créer des sessions DB sans dépendre de apps/api.

Configuration spécifique worker :
- NullPool recommandé pour les tâches Celery batch (pas besoin de pool persistant)
- pool_size réduit par défaut (le worker est batch nocturne, pas du traffic HTTP)

Pour l'API FastAPI, utiliser apps/api/src/db/session.py directement (pool_size=10 + max_overflow=20).

NOTA database-administrator : si la configuration du pool change dans apps/api/src/db/session.py,
répercuter les changements pertinents ici (statement_cache_size=0 pgBouncer compat en particulier).
"""

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


def _get_database_url() -> str:
    """Retourne l'URL async de la base de données depuis l'environnement.

    Normalise les URLs postgres:// et postgresql:// vers postgresql+asyncpg://
    pour la compatibilité avec asyncpg.
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL est requise pour mealplanner_db.session. "
            "Définir la variable d'environnement DATABASE_URL."
        )
    for old_prefix in ("postgresql://", "postgres://"):
        if url.startswith(old_prefix):
            return url.replace(old_prefix, "postgresql+asyncpg://", 1)
    return url


# Moteur worker : NullPool pour les tâches Celery batch nocturnes.
# FIX BUG M3 (review Phase 1 2026-04-12) : évite de saturer les 60 connexions Supabase Free.
# Le pool persistant n'est pas nécessaire pour des tâches batch qui s'exécutent la nuit.
engine = create_async_engine(
    _get_database_url(),
    # NullPool : pas de pool persistant — une connexion par session, fermée après usage
    poolclass=NullPool,
    # connect_args : désactive le prepared statement caching pour pgBouncer (Supabase)
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
    echo=os.environ.get("DATABASE_ECHO", "false").lower() == "true",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency pour l'injection d'une session de base de données."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_engine() -> None:
    """Ferme proprement le moteur de base de données."""
    await engine.dispose()
