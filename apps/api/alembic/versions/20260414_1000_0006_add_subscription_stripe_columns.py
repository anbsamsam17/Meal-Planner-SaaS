"""Correction drift ORM — colonnes Stripe manquantes sur subscriptions (Phase 2).

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-14 10:00:00.000000+00:00

Contexte :
    Le modèle ORM Subscription (apps/api/src/db/models/subscription.py) a été enrichi
    en Phase 2 avec 5 colonnes Stripe et 2 assouplissements de contraintes NOT NULL.
    Ces changements n'ont pas été traduits en migration Alembic, créant un drift entre
    l'ORM et la DB réelle. Les webhooks Stripe crashent en production avec "column does
    not exist" lors des INSERT/UPDATE sur subscriptions.

Colonnes ajoutées (5) :
    - stripe_customer_id  TEXT NULLABLE  : lien vers le Customer Stripe (créé avant
      la souscription, ex : lors du checkout). NULL si la souscription est créée
      directement sans pré-création customer (cas rare).
    - stripe_price_id     TEXT NULLABLE  : Price ID du plan actif (ex: price_xxx).
      NULL si l'abonnement est en Phase 0/1 (stub) ou si la price est déterminée
      dynamiquement. Source de vérité pour les upgrades/downgrades.
    - cancel_at_period_end BOOLEAN NOT NULL DEFAULT false : flag Stripe — l'utilisateur
      a demandé l'annulation mais garde l'accès jusqu'à current_period_end. Requis par
      le webhook customer.subscription.updated pour éviter une annulation immédiate.
    - canceled_at         TIMESTAMPTZ NULLABLE : timestamp de l'annulation effective
      (quand status passe à 'canceled'). NULL si toujours actif ou en trial.
    - trial_end           TIMESTAMPTZ NULLABLE : fin du trial gratuit. NULL si pas de
      période d'essai. Utilisé par RETENTION_LOOP pour les alertes de fin de trial.

Contraintes assouplies (2) :
    - stripe_sub_id NOT NULL → NULLABLE : la pré-création d'un Customer Stripe précède
      la création d'une Subscription. Pendant l'intervalle checkout → webhook
      checkout.session.completed, la ligne subscriptions existe sans stripe_sub_id.
    - current_period_end NOT NULL → NULLABLE : même raison — la période de facturation
      n'est connue qu'après confirmation Stripe (webhook). Les lignes stub Phase 0/1
      ont cette colonne NULL.

Index ajouté (1) :
    - ix_subscriptions_stripe_customer_id : BTREE sur stripe_customer_id (WHERE NOT NULL).
      Les webhooks Stripe (customer.subscription.updated, invoice.payment_failed, etc.)
      arrivent avec le customer_id comme clé de lookup — sans index, chaque webhook
      fait un Seq Scan sur subscriptions (inacceptable en production multi-tenant).

Idempotence :
    Toutes les opérations utilisent ADD COLUMN IF NOT EXISTS et CREATE INDEX IF NOT EXISTS.
    ALTER COLUMN DROP NOT NULL est safe en re-run sur PostgreSQL : si la colonne est déjà
    nullable, l'opération est un no-op silencieux. Rejouer la migration est safe.

downgrade() :
    Reverse dans l'ordre strict inverse :
      1. Restore NOT NULL sur stripe_sub_id et current_period_end
      2. Drop l'index stripe_customer_id
      3. Drop les 5 colonnes
    IMPORTANT : en production, les lignes avec stripe_sub_id IS NULL ou
    current_period_end IS NULL causeront un échec de la contrainte NOT NULL lors du
    downgrade. Effectuer le downgrade uniquement en dev/test après nettoyage des NULLs.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Corrige le drift ORM/DB sur la table subscriptions.

    Phase 2 (2026-04-14) : colonnes Stripe complètes + assouplissement des NOT NULL
    qui bloquaient la pré-création de Customer avant la finalisation du checkout.
    """

    # -----------------------------------------------------------------------
    # ÉTAPE 1 : Assouplissement des contraintes NOT NULL existantes
    # -----------------------------------------------------------------------

    # stripe_sub_id : NOT NULL → NULLABLE
    # Raison : la création d'un enregistrement subscriptions précède la réception
    # du webhook checkout.session.completed. Pendant ce délai (quelques secondes),
    # stripe_sub_id est inconnu. Forcer NOT NULL causait un IntegrityError au INSERT.
    op.execute("""
        ALTER TABLE public.subscriptions
        ALTER COLUMN stripe_sub_id DROP NOT NULL;
    """)
    op.execute("""
        COMMENT ON COLUMN public.subscriptions.stripe_sub_id IS
            'Identifiant de la Subscription Stripe (sub_xxx). '
            'NULLABLE depuis Phase 2 : la pré-création Customer précède la finalisation '
            'de la souscription (délai checkout → webhook checkout.session.completed). '
            'Rempli par le handler webhook checkout.session.completed. '
            'UNIQUE garanti par la contrainte uq_subscriptions_stripe_sub_id (0001).';
    """)

    # current_period_end : NOT NULL → NULLABLE
    # Raison : même délai — la période de facturation n'est connue qu'après confirmation
    # Stripe. Les lignes stub Phase 0/1 ont également cette valeur inconnue.
    op.execute("""
        ALTER TABLE public.subscriptions
        ALTER COLUMN current_period_end DROP NOT NULL;
    """)
    op.execute("""
        COMMENT ON COLUMN public.subscriptions.current_period_end IS
            'Fin de la période de facturation courante (UTC). '
            'NULLABLE depuis Phase 2 : inconnu pendant l''intervalle checkout → webhook. '
            'Mis à jour par les webhooks invoice.payment_succeeded et '
            'customer.subscription.updated. Source de vérité pour la gestion des accès.';
    """)

    # -----------------------------------------------------------------------
    # ÉTAPE 2 : Ajout des 5 colonnes Stripe manquantes
    # -----------------------------------------------------------------------

    # stripe_customer_id — clé de lookup pour TOUS les webhooks Stripe entrants.
    # La majorité des webhooks Stripe fournissent le customer_id, pas le sub_id.
    # Cette colonne est la clé de jointure critique du flow webhook.
    op.execute("""
        ALTER TABLE public.subscriptions
        ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
    """)
    op.execute("""
        COMMENT ON COLUMN public.subscriptions.stripe_customer_id IS
            'Identifiant du Customer Stripe (cus_xxx). '
            'Créé lors du checkout avant la Subscription. Clé de lookup principale '
            'pour les webhooks Stripe (customer.subscription.updated, '
            'invoice.payment_failed, customer.subscription.deleted). '
            'NULL uniquement sur les stubs Phase 0/1 sans Customer Stripe associé.';
    """)

    # stripe_price_id — source de vérité du plan tarifaire actif.
    # Permet de détecter les upgrades/downgrades sans re-interroger l'API Stripe.
    # Exemple : price_starter_monthly, price_famille_annual.
    op.execute("""
        ALTER TABLE public.subscriptions
        ADD COLUMN IF NOT EXISTS stripe_price_id TEXT;
    """)
    op.execute("""
        COMMENT ON COLUMN public.subscriptions.stripe_price_id IS
            'Price ID du plan Stripe actif (price_xxx). '
            'Source de vérité pour les upgrades/downgrades de plan. '
            'Mis à jour par le webhook customer.subscription.updated quand '
            'l''utilisateur change de plan. NULL sur les stubs Phase 0/1.';
    """)

    # cancel_at_period_end — flag d'annulation programmée Stripe.
    # NOT NULL DEFAULT false : sémantique claire sur les lignes existantes (stub Phase 0/1
    # = pas d'annulation programmée). server_default requis pour les lignes déjà présentes.
    op.execute("""
        ALTER TABLE public.subscriptions
        ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN NOT NULL DEFAULT false;
    """)
    op.execute("""
        COMMENT ON COLUMN public.subscriptions.cancel_at_period_end IS
            'Annulation programmée demandée par l''utilisateur (flag Stripe). '
            'true = l''accès est maintenu jusqu''à current_period_end, puis annulation. '
            'false = abonnement actif sans annulation programmée (défaut). '
            'Positionné par le webhook customer.subscription.updated. '
            'Utilisé par RETENTION_LOOP pour les campagnes win-back.';
    """)

    # canceled_at — timestamp de l'annulation effective.
    # NULL si l'abonnement est actif. Rempli par le webhook customer.subscription.deleted.
    op.execute("""
        ALTER TABLE public.subscriptions
        ADD COLUMN IF NOT EXISTS canceled_at TIMESTAMP WITH TIME ZONE;
    """)
    op.execute("""
        COMMENT ON COLUMN public.subscriptions.canceled_at IS
            'Timestamp de l''annulation effective (quand status = ''canceled''). '
            'NULL si l''abonnement est toujours actif ou en période d''essai. '
            'Rempli par le webhook customer.subscription.deleted. '
            'Conservé après annulation pour l''historique et les analytics de churn.';
    """)

    # trial_end — fin du trial gratuit.
    # NULL si pas de période d'essai. RETENTION_LOOP envoie une alerte J-3 avant expiration.
    op.execute("""
        ALTER TABLE public.subscriptions
        ADD COLUMN IF NOT EXISTS trial_end TIMESTAMP WITH TIME ZONE;
    """)
    op.execute("""
        COMMENT ON COLUMN public.subscriptions.trial_end IS
            'Fin de la période d''essai gratuit (UTC). '
            'NULL si l''utilisateur n''a pas de trial (achat direct). '
            'Mis à jour par le webhook customer.subscription.updated. '
            'Utilisé par RETENTION_LOOP pour les alertes de conversion trial → payant '
            '(email J-3, J-1 avant expiration).';
    """)

    # -----------------------------------------------------------------------
    # ÉTAPE 3 : Index sur stripe_customer_id (critique pour les webhooks)
    # -----------------------------------------------------------------------

    # Les webhooks Stripe arrivent avec customer_id comme identifiant principal.
    # Sans cet index, chaque webhook (invoice.payment_failed, subscription.updated, etc.)
    # génère un Seq Scan sur toute la table subscriptions — inacceptable en production.
    # Partial WHERE NOT NULL : les stubs Phase 0/1 sans customer ne sont pas indexés
    # (ils ne reçoivent pas de webhooks Stripe, l'index partiel est plus compact).
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_subscriptions_stripe_customer_id
        ON public.subscriptions (stripe_customer_id)
        WHERE stripe_customer_id IS NOT NULL;
    """)
    op.execute("""
        COMMENT ON INDEX public.ix_subscriptions_stripe_customer_id IS
            'Index BTREE partial sur subscriptions.stripe_customer_id (WHERE NOT NULL). '
            'Critique pour les handlers webhook Stripe : lookup par customer_id pour '
            'customer.subscription.updated, invoice.payment_failed, '
            'customer.subscription.deleted. Sans cet index : Seq Scan par webhook. '
            'Partial WHERE NOT NULL : les stubs Phase 0/1 sans Customer Stripe '
            'n''apparaissent pas dans l''index (compacité). Phase 2 (2026-04-14).';
    """)


def downgrade() -> None:
    """Reverse le drift fix — supprime les colonnes Stripe et restore les NOT NULL.

    AVERTISSEMENT PRODUCTION :
        Avant d'exécuter ce downgrade en production, s'assurer qu'aucune ligne
        subscriptions n'a stripe_sub_id IS NULL ou current_period_end IS NULL.
        La restore des contraintes NOT NULL échouera sinon avec :
            ERROR: column "stripe_sub_id" of relation "subscriptions" contains null values

    Safe en dev/test uniquement (table vide ou données de test nettoyées).
    """

    # Étape 1 : supprimer l'index (dépendance de la colonne)
    op.execute("""
        DROP INDEX IF EXISTS public.ix_subscriptions_stripe_customer_id;
    """)

    # Étape 2 : supprimer les 5 colonnes dans l'ordre inverse d'ajout
    # trial_end
    op.execute("""
        ALTER TABLE public.subscriptions
        DROP COLUMN IF EXISTS trial_end;
    """)
    # canceled_at
    op.execute("""
        ALTER TABLE public.subscriptions
        DROP COLUMN IF EXISTS canceled_at;
    """)
    # cancel_at_period_end
    op.execute("""
        ALTER TABLE public.subscriptions
        DROP COLUMN IF EXISTS cancel_at_period_end;
    """)
    # stripe_price_id
    op.execute("""
        ALTER TABLE public.subscriptions
        DROP COLUMN IF EXISTS stripe_price_id;
    """)
    # stripe_customer_id
    op.execute("""
        ALTER TABLE public.subscriptions
        DROP COLUMN IF EXISTS stripe_customer_id;
    """)

    # Étape 3 : remettre les contraintes NOT NULL
    # Prérequis : toutes les lignes doivent avoir une valeur non-NULL dans ces colonnes.
    op.execute("""
        ALTER TABLE public.subscriptions
        ALTER COLUMN current_period_end SET NOT NULL;
    """)
    op.execute("""
        ALTER TABLE public.subscriptions
        ALTER COLUMN stripe_sub_id SET NOT NULL;
    """)
