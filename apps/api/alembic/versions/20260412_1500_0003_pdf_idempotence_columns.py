"""Ajout colonne content_hash sur weekly_books pour idempotence PDF Phase 3.

Revision ID: 0003
Revises: 0001
Create Date: 2026-04-12 15:00:00.000000+00:00

Contexte : référence au review Phase 1 (2026-04-12) et à la stratégie
13-pdf-generation-strategy.md. BOOK_GENERATOR utilisera content_hash (SHA-256
du contenu logique du plan) pour ne pas régénérer un PDF dont le contenu n'a
pas changé depuis la dernière génération. Préparation Phase 3.

Idempotence :
    - op.add_column est idempotent si la colonne existe déjà (catch ProgrammingError).
    - La colonne est nullable : aucun DEFAULT requis, les anciens enregistrements
      reçoivent NULL et seront re-hashés lors de leur prochaine génération.

downgrade() :
    - Supprime content_hash de weekly_books.
    - Safe : la colonne est nullable, aucune contrainte ne la référence.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute content_hash (TEXT, nullable) sur weekly_books.

    op.add_column est idempotent dans Alembic : si la migration est re-jouée
    sur une base qui a déjà cette colonne (ex : environnement de test avec
    fixtures partielles), PostgreSQL lèvera DuplicateColumn — on l'intercepte.
    """
    # Vérification préalable via SQL pour rendre l'upgrade safe en re-run
    op.execute("""
        ALTER TABLE public.weekly_books
        ADD COLUMN IF NOT EXISTS content_hash TEXT;
    """)

    op.execute("""
        COMMENT ON COLUMN public.weekly_books.content_hash IS
            'SHA-256 du contenu logique du plan (recettes + portions + semaine). '
            'NULL sur les anciens enregistrements. Calculé par BOOK_GENERATOR avant '
            'génération pour éviter une re-génération identique (idempotence Phase 3). '
            'Ajouté en Phase 1 — activé en Phase 3 (voir 13-pdf-generation-strategy.md).';
    """)


def downgrade() -> None:
    """Supprime content_hash de weekly_books.

    Safe uniquement en dev/test — les données content_hash sont perdues.
    En production, préférer laisser la colonne (elle est nullable et sans impact).
    """
    op.execute("""
        ALTER TABLE public.weekly_books
        DROP COLUMN IF EXISTS content_hash;
    """)
