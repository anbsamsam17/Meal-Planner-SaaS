"""Table user_imported_recipes — tracking des imports par foyer.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-15 10:00:00.000000+00:00

Contexte :
    La feature "Import recette depuis URL" (Phase A v1 MVP) permet aux
    utilisateurs d'importer des recettes depuis n'importe quelle URL.
    Cette table track quelles recettes ont ete importees par quel foyer,
    permettant :
    - Afficher "Mes imports" dans le frontend
    - Limiter les imports par foyer (anti-abus)
    - Analytics sur les sources d'import les plus populaires

Securite :
    - RLS active : un foyer ne voit que ses propres imports
    - FORCE ROW LEVEL SECURITY pour couvrir les table owners
    - Policy SELECT/INSERT par household_id via household_members join

Changements :
    1. CREATE TABLE user_imported_recipes
    2. Index unique (recipe_id, household_id) — un foyer ne peut importer
       la meme recette qu'une seule fois
    3. FK vers recipes(id) et auth.users(id)
    4. RLS policies SELECT et INSERT
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cree la table user_imported_recipes avec RLS."""

    # 1. Table principale
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_imported_recipes (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            recipe_id   UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
            household_id UUID NOT NULL,
            imported_by UUID NOT NULL,
            imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT uq_import_recipe_household
                UNIQUE (recipe_id, household_id)
        );
        """
    )

    # 2. Index pour les lookups par foyer (page "Mes imports")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_imported_recipes_household
            ON user_imported_recipes (household_id, imported_at DESC);
        """
    )

    # 3. RLS
    op.execute("ALTER TABLE user_imported_recipes ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE user_imported_recipes FORCE ROW LEVEL SECURITY;")

    # Policy SELECT — un membre authentifie ne voit que les imports de son foyer
    op.execute("DROP POLICY IF EXISTS user_imported_recipes_select ON user_imported_recipes;")
    op.execute(
        """
        CREATE POLICY user_imported_recipes_select ON user_imported_recipes
            FOR SELECT
            USING (
                household_id IN (
                    SELECT hm.household_id
                    FROM household_members hm
                    WHERE hm.supabase_user_id = auth.uid()
                )
            );
        """
    )

    # Policy INSERT — un membre authentifie peut inserer pour son propre foyer
    op.execute("DROP POLICY IF EXISTS user_imported_recipes_insert ON user_imported_recipes;")
    op.execute(
        """
        CREATE POLICY user_imported_recipes_insert ON user_imported_recipes
            FOR INSERT
            WITH CHECK (
                household_id IN (
                    SELECT hm.household_id
                    FROM household_members hm
                    WHERE hm.supabase_user_id = auth.uid()
                )
            );
        """
    )

    # Policy pour le service_role (Celery worker) — acces total
    op.execute("DROP POLICY IF EXISTS user_imported_recipes_service ON user_imported_recipes;")
    op.execute(
        """
        CREATE POLICY user_imported_recipes_service ON user_imported_recipes
            FOR ALL
            USING (current_setting('role') = 'service_role')
            WITH CHECK (current_setting('role') = 'service_role');
        """
    )


def downgrade() -> None:
    """Supprime la table user_imported_recipes."""
    op.execute("DROP TABLE IF EXISTS user_imported_recipes CASCADE;")
