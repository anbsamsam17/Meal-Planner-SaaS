"""Module db — couche d'accès à la base de données Presto.

Exports publics :
- Base           : DeclarativeBase SQLAlchemy 2.0 (base de tous les modèles ORM)
- AsyncSessionLocal : fabrique de sessions async pour FastAPI
- get_db         : dependency FastAPI pour l'injection de session
- engine         : moteur async (utile pour les scripts de maintenance)

Usage dans un endpoint FastAPI :
    from src.db import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    async def my_endpoint(db: AsyncSession = Depends(get_db)):
        ...
"""

from src.db.base import Base
from src.db.session import AsyncSessionLocal, engine, get_db

__all__ = ["AsyncSessionLocal", "Base", "engine", "get_db"]
