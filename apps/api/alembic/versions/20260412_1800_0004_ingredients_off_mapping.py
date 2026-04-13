"""Enrichissement colonnes Open Food Facts sur ingredients — support RECIPE_SCOUT complet.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-12 18:00:00.000000+00:00

# Phase 1 mature (2026-04-12) : MISSION A — Open Food Facts mapping

Contexte :
    RECIPE_SCOUT va mapper chaque ingrédient canonique vers un produit Open Food Facts
    pour préparer la génération de panier drive (Phase 4). La colonne off_id existait
    déjà en Phase 0 (migration 0001) pour le principe. Cette migration l'enrichit avec
    les colonnes nécessaires au pipeline de mapping effectif.

Colonnes ajoutées :
    - off_last_checked_at TIMESTAMPTZ : dernière tentative de mapping (pour retry cron)
    - off_match_confidence FLOAT       : score de confiance du match OFF (0.0-1.0)
    - off_product_name TEXT            : nom du produit OFF retenu (snapshot pour affichage)
    - off_brand TEXT                   : marque produit OFF (optionnel, affichage drive)

Pourquoi ces colonnes et pas une table séparée :
    ~200 ingrédients canoniques max en Phase 1. Une table off_mapping_cache serait
    over-engineering : une ligne par ingrédient suffit. Les colonnes directes évitent
    un JOIN supplémentaire dans les queries CART_BUILDER (Phase 4).

Décision table off_mapping_cache :
    NON créée. Raison : avec ~200 ingrédients canoniques, l'API OFF est appelée une
    seule fois par ingrédient (puis retry automatique via off_last_checked_at). Une
    table cache de recherche par terme serait utile uniquement si plusieurs ingrédients
    partageaient le même terme de recherche — ce qui n'est pas le cas pour un référentiel
    canonique. Le cache Redis (si besoin) sera géré par le worker RECIPE_SCOUT directement.

Index ajoutés :
    - ix_ingredients_off_id_partial        : retrouver rapidement les ingrédients déjà mappés
    - ix_ingredients_off_pending           : retrouver rapidement les ingrédients à mapper
      (NULLS FIRST sur off_last_checked_at pour prioriser ceux jamais tentés)

Idempotence :
    Toutes les opérations utilisent ADD COLUMN IF NOT EXISTS et CREATE INDEX IF NOT EXISTS.
    Rejouer la migration sur une base déjà migrée est safe.

downgrade() :
    Supprime les colonnes enrichies et les index associés.
    off_id (colonne Phase 0, migration 0001) n'est PAS supprimée — elle appartient à 0001.
    Safe en dev/test uniquement. En production, préférer conserver les colonnes (nullable, sans impact).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enrichit la table ingredients avec les colonnes de mapping Open Food Facts.

    Phase 1 mature (2026-04-12) : nécessaire pour RECIPE_SCOUT complet et
    la préparation du panier drive Phase 4.
    """

    # -- A.2 : Colonnes de mapping Open Food Facts sur ingredients --

    # Dernière tentative de mapping — permet au cron de retry les ingrédients non mappés
    # NULLS FIRST dans l'index pending = les "jamais tentés" passent en priorité absolue
    op.execute("""
        ALTER TABLE public.ingredients
        ADD COLUMN IF NOT EXISTS off_last_checked_at TIMESTAMPTZ;
    """)
    op.execute("""
        COMMENT ON COLUMN public.ingredients.off_last_checked_at IS
            'Timestamp de la dernière tentative de mapping Open Food Facts. '
            'NULL = jamais tenté. Utilisé par le cron RECIPE_SCOUT pour retry. '
            'Phase 1 mature (2026-04-12) : support RECIPE_SCOUT complet.';
    """)

    # Score de confiance du match — RECIPE_SCOUT rejette les matches < 0.5 (seuil à configurer)
    op.execute("""
        ALTER TABLE public.ingredients
        ADD COLUMN IF NOT EXISTS off_match_confidence FLOAT;
    """)
    op.execute("""
        COMMENT ON COLUMN public.ingredients.off_match_confidence IS
            'Score de confiance du match Open Food Facts (0.0 = aucune confiance, 1.0 = certitude). '
            'Calculé par RECIPE_SCOUT lors du mapping. NULL si pas encore mappé ou mapping échoué. '
            'CHECK 0.0-1.0 n''est pas contraint en DB pour permettre NULL — validé en Python.';
    """)

    # Snapshot du nom produit OFF — évite une re-requête lors de l affichage drive
    op.execute("""
        ALTER TABLE public.ingredients
        ADD COLUMN IF NOT EXISTS off_product_name TEXT;
    """)
    op.execute("""
        COMMENT ON COLUMN public.ingredients.off_product_name IS
            'Nom du produit Open Food Facts sélectionné lors du mapping. '
            'Snapshot pour affichage drive sans re-requête OFF. '
            'NULL si pas encore mappé.';
    """)

    # Marque produit — optionnel, utile pour la liste de courses Phase 4
    op.execute("""
        ALTER TABLE public.ingredients
        ADD COLUMN IF NOT EXISTS off_brand TEXT;
    """)
    op.execute("""
        COMMENT ON COLUMN public.ingredients.off_brand IS
            'Marque du produit Open Food Facts sélectionné (optionnel). '
            'Affiché dans la liste de courses drive Phase 4 si disponible. '
            'NULL si marque non disponible ou ingrédient non mappé.';
    """)

    # -- Index partial sur off_id : retrouver les ingrédients déjà mappés --
    # Partial car on ne cherche JAMAIS les ingrédients non mappés via cet index.
    # Phase 1 mature (2026-04-12) : RECIPE_SCOUT query "déjà mappé ?"
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_ingredients_off_id_partial
        ON public.ingredients (off_id)
        WHERE off_id IS NOT NULL;
    """)
    op.execute("""
        COMMENT ON INDEX public.ix_ingredients_off_id_partial IS
            'Index UNIQUE partial sur off_id (WHERE off_id IS NOT NULL). '
            'Garantit l''unicité du product_code OFF dans le référentiel. '
            'Partial car les ingrédients non mappés (off_id IS NULL) sont nombreux '
            'et ne nécessitent pas d''unicité (plusieurs peuvent être en attente). '
            'Phase 1 mature (2026-04-12).';
    """)

    # -- Index sur off_last_checked_at pour la queue de mapping --
    # NULLS FIRST : les ingrédients jamais tentés passent avant les plus anciens retry
    # WHERE off_id IS NULL : ne concerne QUE les ingrédients non encore mappés
    # Phase 1 mature (2026-04-12) : RECIPE_SCOUT batch mapping nocturne
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ingredients_off_pending
        ON public.ingredients (off_last_checked_at NULLS FIRST)
        WHERE off_id IS NULL;
    """)
    op.execute("""
        COMMENT ON INDEX public.ix_ingredients_off_pending IS
            'Index BTREE partial pour la queue de mapping Open Food Facts. '
            'WHERE off_id IS NULL : restreint aux ingrédients non encore mappés. '
            'NULLS FIRST : les ingrédients jamais tentés (off_last_checked_at IS NULL) '
            'apparaissent en tête, avant les retry les plus anciens. '
            'Utilisé par RECIPE_SCOUT : SELECT * FROM ingredients WHERE off_id IS NULL '
            'ORDER BY off_last_checked_at NULLS FIRST LIMIT 50. '
            'Phase 1 mature (2026-04-12).';
    """)


def downgrade() -> None:
    """Supprime les colonnes et index de mapping Open Food Facts enrichis.

    IMPORTANT : off_id (colonne originale Phase 0, migration 0001) N'EST PAS supprimée.
    Elle appartient à la migration 0001 et doit être gérée par downgrade() de 0001.

    Safe en dev/test uniquement. En production, conserver les colonnes (nullable, sans impact).
    """
    # Suppression des index en premier (dépendances des colonnes)
    op.execute("DROP INDEX IF EXISTS public.ix_ingredients_off_pending;")
    op.execute("DROP INDEX IF EXISTS public.ix_ingredients_off_id_partial;")

    # Suppression des colonnes enrichies (dans l'ordre inverse d'ajout)
    op.execute("""
        ALTER TABLE public.ingredients
        DROP COLUMN IF EXISTS off_brand;
    """)
    op.execute("""
        ALTER TABLE public.ingredients
        DROP COLUMN IF EXISTS off_product_name;
    """)
    op.execute("""
        ALTER TABLE public.ingredients
        DROP COLUMN IF EXISTS off_match_confidence;
    """)
    op.execute("""
        ALTER TABLE public.ingredients
        DROP COLUMN IF EXISTS off_last_checked_at;
    """)
