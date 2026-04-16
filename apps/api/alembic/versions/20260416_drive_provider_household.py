"""Ajout colonne drive_provider sur households.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-16 10:00:00.000000+00:00

Contexte :
    La page Settings du frontend permet a l'utilisateur de configurer son
    fournisseur de drive preferé (Leclerc, Auchan, Carrefour, etc.) pour
    que la shopping list genere un lien de commande pre-rempli.

    Les valeurs acceptées sont :
    - 'leclerc'     : E.Leclerc Drive
    - 'auchan'      : Auchan Drive
    - 'carrefour'   : Carrefour Drive
    - 'intermarche' : Intermarché Drive
    - 'other'       : Autre (export générique)
    - NULL          : non configuré (defaut)

    Aucune contrainte CHECK pour l'instant — on tolere les nouvelles
    enseignes sans migration. La validation est portée cote API (Pydantic).

Changements :
    1. ALTER TABLE households ADD COLUMN drive_provider VARCHAR NULL
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute la colonne drive_provider sur la table households."""

    op.execute(
        """
        ALTER TABLE households ADD COLUMN IF NOT EXISTS drive_provider VARCHAR NULL;
        """
    )

    # Index léger pour les requêtes analytics (volume faible — pas critique)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_households_drive_provider
            ON households (drive_provider)
            WHERE drive_provider IS NOT NULL;
        """
    )


def downgrade() -> None:
    """Supprime l'index et la colonne drive_provider."""
    op.execute("DROP INDEX IF EXISTS idx_households_drive_provider;")
    op.execute("ALTER TABLE households DROP COLUMN IF EXISTS drive_provider;")
