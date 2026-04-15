"""Ajout colonne course sur recipes pour classifier le type de plat.

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-15 14:00:00.000000+00:00

Contexte :
    Le planner hebdomadaire peut actuellement proposer un accompagnement seul
    comme diner car il n'y a aucune distinction entre plat principal,
    accompagnement, dessert, boisson, etc. Cette migration ajoute la colonne
    `course` pour permettre au planner de filtrer correctement.

    La classification des 338 recettes existantes sera faite via un script
    de migration SQL separe (scripts/classify_recipes.py -> classify_recipes.sql).

Valeurs attendues pour `course` :
    - plat_principal
    - accompagnement
    - dessert
    - boisson
    - entree
    - petit_dejeuner
    - pain_viennoiserie
    - sauce_condiment

Changements :
    1. ALTER TABLE recipes ADD COLUMN course text (nullable, pas de CHECK)
    2. CREATE INDEX idx_recipes_course pour filtrage rapide par le planner
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute la colonne course et son index sur recipes."""

    # 1. Colonne course — nullable, sans contrainte CHECK pour l'instant.
    #    La classification se fera via script SQL (classify_recipes.sql).
    #    Valeurs attendues : plat_principal, accompagnement, dessert, boisson,
    #    entree, petit_dejeuner, pain_viennoiserie, sauce_condiment
    op.execute(
        """
        ALTER TABLE recipes ADD COLUMN IF NOT EXISTS course text;
        """
    )

    # 2. Index pour filtrage par course (utilise par le planner hebdomadaire)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recipes_course ON recipes(course);
        """
    )


def downgrade() -> None:
    """Supprime l'index et la colonne course."""
    op.execute("DROP INDEX IF EXISTS idx_recipes_course;")
    op.execute("ALTER TABLE recipes DROP COLUMN IF EXISTS course;")
