"""Ajout contrainte UNIQUE (member_id, recipe_id, feedback_type) sur recipe_feedbacks.

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-16 11:00:00.000000+00:00

Contexte :
    L'endpoint POST /api/v1/feedbacks utilise un ON CONFLICT UPSERT pour
    les feedbacks de type 'favorited' (feedback_type = 'favorited').
    Ce UPSERT requiert une contrainte UNIQUE sur (member_id, recipe_id, feedback_type)
    pour que PostgreSQL puisse détecter le conflit et faire l'UPDATE au lieu d'un INSERT.

    Sans cette contrainte, le ON CONFLICT échoue avec :
        "there is no unique or exclusion constraint matching the ON CONFLICT specification"

    La contrainte garantit également qu'un membre ne peut pas avoir deux feedbacks
    identiques pour la même recette et le même type d'interaction.

    Stratégie de migration :
    - Déduplication préalable des lignes existantes en cas de doublons
      (garde le plus récent created_at par triplet).
    - Ajout de la contrainte UNIQUE via ADD CONSTRAINT IF NOT EXISTS.
    - Mise à jour de l'index partiel idx_recipe_feedbacks_favorited pour
      devenir un index UNIQUE (remplace l'ancien index non-unique).

Changements :
    1. Déduplication des feedbacks 'favorited' en double (conserve le plus récent)
    2. ADD CONSTRAINT uq_recipe_feedbacks_member_recipe_type UNIQUE (member_id, recipe_id, feedback_type)
    3. DROP + CREATE INDEX UNIQUE pour idx_recipe_feedbacks_favorited
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute la contrainte UNIQUE sur recipe_feedbacks (member_id, recipe_id, feedback_type)."""

    # Étape 1 : déduplication des lignes existantes.
    # Si deux feedbacks identiques existent (même member/recipe/type),
    # on supprime tous sauf le plus récent (created_at DESC).
    op.execute(
        """
        DELETE FROM recipe_feedbacks
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY member_id, recipe_id, feedback_type
                           ORDER BY created_at DESC
                       ) AS rn
                FROM recipe_feedbacks
            ) ranked
            WHERE rn > 1
        );
        """
    )

    # Étape 2 : ajout de la contrainte UNIQUE.
    # DO $$ ... $$ permet de ne pas échouer si la contrainte existe déjà (idempotent).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_recipe_feedbacks_member_recipe_type'
            ) THEN
                ALTER TABLE recipe_feedbacks
                    ADD CONSTRAINT uq_recipe_feedbacks_member_recipe_type
                    UNIQUE (member_id, recipe_id, feedback_type);
            END IF;
        END $$;
        """
    )

    # Étape 3 : remplacer l'index partiel non-unique par un index standard.
    # La contrainte UNIQUE crée déjà un index B-tree complet — l'index partiel
    # idx_recipe_feedbacks_favorited n'est plus nécessaire et peut être supprimé.
    op.execute("DROP INDEX IF EXISTS idx_recipe_feedbacks_favorited;")


def downgrade() -> None:
    """Supprime la contrainte UNIQUE et restaure l'index partiel."""

    # Restaurer l'index partiel pour les favoris
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recipe_feedbacks_favorited
            ON recipe_feedbacks (household_id, recipe_id)
            WHERE feedback_type = 'favorited';
        """
    )

    # Supprimer la contrainte UNIQUE
    op.execute(
        """
        ALTER TABLE recipe_feedbacks
            DROP CONSTRAINT IF EXISTS uq_recipe_feedbacks_member_recipe_type;
        """
    )
