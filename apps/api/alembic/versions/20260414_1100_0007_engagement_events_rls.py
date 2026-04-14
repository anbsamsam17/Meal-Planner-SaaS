"""SEC-03 — Activation RLS et policies sur engagement_events.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-14 11:00:00.000000+00:00

Contexte :
    La table engagement_events a ete creee dans le schema SQL Docker
    (04-phase2-schema.sql) avec RLS active et policies configurees.
    Cependant, en production Supabase, les init scripts Docker ne sont
    pas executes : seules les migrations Alembic font foi.
    Cette migration applique les memes protections RLS que le script
    Docker, garantissant la parite dev/prod.

Probleme de securite (SEC-03 P1) :
    Sans RLS, tout utilisateur authentifie avec la anon key Supabase
    peut lire/ecrire dans engagement_events sans restriction tenant.
    Les evenements d'engagement (at_risk, win_back_sent, churn signals)
    sont des donnees metier sensibles qui doivent etre isolees par foyer.

Changements :
    1. ENABLE ROW LEVEL SECURITY sur engagement_events
    2. FORCE ROW LEVEL SECURITY (meme les table owners sont soumis)
    3. Policy SELECT : un membre authentifie ne peut lire que les events
       de son propre foyer (via household_members.supabase_user_id)
    4. Policy INSERT : l'ecriture est reservee au service_role (Celery).
       Les utilisateurs authentifies ne peuvent PAS inserer d'events
       directement (le RETENTION_LOOP agent ecrit via service_role_key).

Idempotence :
    Toutes les operations utilisent DROP POLICY IF EXISTS avant CREATE.
    ENABLE/FORCE ROW LEVEL SECURITY sont des no-ops si deja actives.
    La migration peut etre rejouee en toute securite.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Active RLS et cree les policies sur engagement_events.

    Pattern Supabase standard :
    - Policy SELECT : USING clause verifie que le household_id de la ligne
      correspond a un foyer dont l'utilisateur JWT est membre.
    - Policy INSERT : reservee au service_role (agent RETENTION_LOOP).
      Les utilisateurs authentifies ne peuvent pas inserer d'events.
    - Le claim JWT sub est extrait via auth.uid() (fonction Supabase built-in).
    """

    # -----------------------------------------------------------------------
    # ETAPE 1 : Activer RLS sur engagement_events
    # -----------------------------------------------------------------------

    # ENABLE ROW LEVEL SECURITY : active le mecanisme RLS sur la table.
    # Sans cette commande, les policies n'ont aucun effet.
    op.execute("""
        ALTER TABLE public.engagement_events ENABLE ROW LEVEL SECURITY;
    """)

    # FORCE ROW LEVEL SECURITY : soumet meme les table owners (superuser,
    # postgres role) aux policies. Defense en profondeur : meme si un service
    # se connecte avec le role owner de la table, il est quand meme filtre.
    op.execute("""
        ALTER TABLE public.engagement_events FORCE ROW LEVEL SECURITY;
    """)

    # -----------------------------------------------------------------------
    # ETAPE 2 : Policy SELECT — lecture restreinte aux membres du foyer
    # -----------------------------------------------------------------------

    # Suppression idempotente de la policy si elle existe deja
    # (permet de rejouer la migration sans erreur)
    op.execute("""
        DROP POLICY IF EXISTS engagement_events_select_own
        ON public.engagement_events;
    """)

    # Policy SELECT : un utilisateur authentifie ne peut lire que les events
    # de son propre foyer. Le sous-select sur household_members garantit
    # l'isolation tenant : seuls les events dont le household_id correspond
    # a un foyer dont l'utilisateur est membre sont retournes.
    #
    # auth.uid() : fonction Supabase built-in qui extrait le claim 'sub'
    # du JWT de la requete courante (equivalent a current_setting('request.jwt.claims')::json->>'sub').
    op.execute("""
        CREATE POLICY engagement_events_select_own
        ON public.engagement_events
        FOR SELECT
        TO authenticated
        USING (
            household_id IN (
                SELECT hm.household_id
                FROM public.household_members hm
                WHERE hm.supabase_user_id = auth.uid()
            )
        );
    """)

    # -----------------------------------------------------------------------
    # ETAPE 3 : Policy INSERT — ecriture reservee au service_role
    # -----------------------------------------------------------------------

    # Suppression idempotente
    op.execute("""
        DROP POLICY IF EXISTS engagement_events_insert_service
        ON public.engagement_events;
    """)

    # Policy INSERT : seul le service_role peut inserer des events.
    # Le RETENTION_LOOP agent (Celery) se connecte avec la service_role_key
    # qui bypass RLS. Cette policy est une defense supplementaire : si un
    # utilisateur authentifie tente un INSERT direct (ex : via Supabase client JS),
    # le WITH CHECK false empechera l'insertion.
    #
    # Note : service_role bypass RLS par defaut dans Supabase, donc cette policy
    # ne le bloque pas. Elle bloque uniquement les INSERT des roles 'authenticated'
    # et 'anon'.
    op.execute("""
        CREATE POLICY engagement_events_insert_service
        ON public.engagement_events
        FOR INSERT
        TO authenticated
        WITH CHECK (false);
    """)

    # -----------------------------------------------------------------------
    # Comments pour la documentation schema
    # -----------------------------------------------------------------------
    op.execute("""
        COMMENT ON TABLE public.engagement_events IS
            'Journal d''evenements d''engagement par foyer. Ecrit par l''agent '
            'RETENTION_LOOP (service_role via Celery). RLS active (SEC-03, 2026-04-14) : '
            'SELECT restreint aux membres du foyer, INSERT reserve au service_role.';
    """)


def downgrade() -> None:
    """Desactive RLS et supprime les policies sur engagement_events.

    AVERTISSEMENT :
        Desactiver RLS en production expose les donnees d'engagement de
        TOUS les foyers a TOUS les utilisateurs authentifies. N'executer
        ce downgrade qu'en environnement de developpement/test.
    """

    # Suppression des policies dans l'ordre inverse de creation
    op.execute("""
        DROP POLICY IF EXISTS engagement_events_insert_service
        ON public.engagement_events;
    """)
    op.execute("""
        DROP POLICY IF EXISTS engagement_events_select_own
        ON public.engagement_events;
    """)

    # Desactivation de FORCE et ENABLE RLS
    # Note : NO FORCE puis DISABLE
    op.execute("""
        ALTER TABLE public.engagement_events NO FORCE ROW LEVEL SECURITY;
    """)
    op.execute("""
        ALTER TABLE public.engagement_events DISABLE ROW LEVEL SECURITY;
    """)
