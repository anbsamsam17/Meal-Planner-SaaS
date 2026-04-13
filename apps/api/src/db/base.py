"""base.py — DeclarativeBase SQLAlchemy 2.0 avec convention de nommage standard.

Toutes les classes ORM héritent de Base définie ici.
La convention de nommage garantit la cohérence des noms de contraintes générés
automatiquement par SQLAlchemy (utile pour les migrations Alembic autogenerate).

Référence convention : https://docs.sqlalchemy.org/en/20/core/constraints.html#constraint-naming-conventions
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Convention de nommage des contraintes — essentielle pour les migrations Alembic.
# Sans convention explicite, SQLAlchemy génère des noms aléatoires qui rendent
# les migrations autogenerate non-déterministes (ex : ck_abc123 vs ck_def456).
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles ORM SQLAlchemy 2.0.

    Usage :
        class MyModel(Base):
            __tablename__ = "my_table"
            id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
