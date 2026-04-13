-- =============================================================================
-- 00-setup-extensions.sql
-- Activation des extensions PostgreSQL 16 nécessaires au projet MealPlanner
-- À exécuter UNE SEULE FOIS par un superuser avant toute migration Alembic.
-- Dans Supabase : certaines extensions sont activables via le Dashboard SQL Editor.
-- =============================================================================

-- uuid-ossp : génération d'UUIDs v4 via gen_random_uuid() (natif PG16)
-- On active uuid-ossp pour compatibilité avec uuid_generate_v4() dans certains outils.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pgcrypto : fonctions de hachage (crypt, gen_salt) et gen_random_bytes
-- Utilisé pour tokens sécurisés côté application si besoin hors Supabase Auth.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- pgvector : stockage et recherche par similarité cosine sur vecteurs d'embeddings
-- CRITIQUE : doit être activé AVANT la création des tables recipe_embeddings et member_taste_vectors.
-- Dimension cible : 384 (sentence-transformers all-MiniLM-L6-v2, coût zéro d'inférence).
-- ATTENTION : changer la dimension après insertion impose un TRUNCATE + re-embed complet.
CREATE EXTENSION IF NOT EXISTS "vector";

-- pg_trgm : index trigrammes pour la recherche full-text approximative en français
-- Permet le LIKE '%terme%' performant et la recherche insensible aux accents sur recipes.title.
-- Couplé à un index GIN trgm, latence < 10ms sur 50 000 recettes.
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Vérification : affiche les extensions actives après installation
SELECT
    extname      AS extension,
    extversion   AS version,
    extnamespace AS schema_oid
FROM pg_extension
WHERE extname IN ('uuid-ossp', 'pgcrypto', 'vector', 'pg_trgm')
ORDER BY extname;
