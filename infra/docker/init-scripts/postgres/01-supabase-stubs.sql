-- =============================================================================
-- 01-supabase-stubs.sql
-- Stubs Supabase pour le développement local Docker
--
-- Ce script s'exécute automatiquement au PREMIER démarrage du container
-- (répertoire /docker-entrypoint-initdb.d, ordre alphabétique numéroté).
--
-- En production, ces rôles et fonctions sont fournis nativement par Supabase.
-- En dev local, ils sont simulés ici pour que le schéma et les policies RLS
-- fonctionnent de façon identique à l'environnement Supabase cible.
--
-- IMPORTANT : ce script ne s'exécute QUE si postgres_data est vide.
-- Un `docker compose down -v && docker compose up -d` le rejoue intégralement.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Schéma auth (simulé — en production c'est Supabase qui le fournit)
-- Ce schéma héberge auth.uid() et, chez Supabase, auth.users, auth.sessions, etc.
-- En dev local on n'a besoin que du schéma et de la fonction uid().
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS auth;

-- -----------------------------------------------------------------------------
-- Fonction auth.uid() — retourne l'UUID du user JWT connecté
--
-- En production Supabase : la fonction lit le JWT décodé par PostgREST.
-- En dev local : lit le GUC (Grand Unified Configuration) 'request.jwt.claim.sub'
-- que le middleware FastAPI définit via SET LOCAL avant chaque requête SQL.
--
-- Comportement :
--   - Si le GUC est défini et valide → retourne l'UUID du user
--   - Si le GUC est absent ou vide   → retourne l'UUID "zéro" (sentinel dev)
--     (jamais NULL, pour éviter les faux positifs RLS en dev)
--
-- STABLE : PostgreSQL peut mettre le résultat en cache pour la transaction.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION auth.uid() RETURNS UUID AS $$
  SELECT COALESCE(
    nullif(current_setting('request.jwt.claim.sub', true), '')::UUID,
    '00000000-0000-0000-0000-000000000000'::UUID
  );
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION auth.uid() IS
    'Stub dev local de auth.uid() Supabase. '
    'Lit le GUC request.jwt.claim.sub défini par le middleware FastAPI (SET LOCAL). '
    'Retourne un UUID zéro si absent (sentinel dev — jamais NULL). '
    'En production Supabase, cette fonction est fournie nativement par PostgREST.';

-- -----------------------------------------------------------------------------
-- Rôles Supabase simulés
--
-- anon         : utilisateur non authentifié (lecture publique)
-- authenticated: utilisateur avec JWT valide (accès RLS complet)
-- service_role : backend interne (bypass RLS complet — agents Celery, webhooks Stripe)
--
-- Ces rôles sont créés conditionnellement (IF NOT EXISTS) pour idempotence.
-- NOLOGIN : ces rôles ne peuvent pas se connecter directement à la DB.
-- Ils sont utilisés comme rôles cibles dans les GRANT et les RLS TO <role>.
-- -----------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
    CREATE ROLE anon NOLOGIN;
    RAISE NOTICE 'Rôle anon créé.';
  ELSE
    RAISE NOTICE 'Rôle anon déjà présent — ignoré.';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOLOGIN;
    RAISE NOTICE 'Rôle authenticated créé.';
  ELSE
    RAISE NOTICE 'Rôle authenticated déjà présent — ignoré.';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
    CREATE ROLE service_role NOLOGIN;
    RAISE NOTICE 'Rôle service_role créé.';
  ELSE
    RAISE NOTICE 'Rôle service_role déjà présent — ignoré.';
  END IF;
END
$$;

-- -----------------------------------------------------------------------------
-- Accès aux schémas pour les rôles Supabase simulés
--
-- USAGE sur public : permet aux rôles de "voir" le schéma et ses objets.
--   Sans ce GRANT, les SELECT/INSERT/UPDATE retournent "relation does not exist".
-- USAGE sur auth   : permet aux rôles d'appeler auth.uid().
--   Nécessaire pour que les policies RLS puissent évaluer la fonction.
-- -----------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT USAGE ON SCHEMA auth   TO anon, authenticated, service_role;

-- Permettre aux rôles d'exécuter la fonction auth.uid()
GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated, service_role;

DO $$ BEGIN RAISE NOTICE '01-supabase-stubs.sql : stubs Supabase installés avec succès.'; END $$;
