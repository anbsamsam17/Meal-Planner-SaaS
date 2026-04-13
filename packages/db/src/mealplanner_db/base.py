"""
base.py — Ré-export de la DeclarativeBase SQLAlchemy depuis apps/api.

FIX #1 (review Phase 1 2026-04-12) : expose Base via mealplanner_db.base
pour que le worker puisse créer des engines sans dépendre de apps/api directement.

Ce fichier re-déclare la Base avec la même convention de nommage que apps/api/src/db/base.py.
Les deux doivent rester synchronisés — si la convention change, modifier les deux fichiers
et alerter le database-administrator.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Même convention que apps/api/src/db/base.py — doit rester synchronisée
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles ORM SQLAlchemy 2.0."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
