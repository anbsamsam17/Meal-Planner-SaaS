-- =============================================================================
-- 00-extensions.sql — Extensions PostgreSQL activées au démarrage du container
-- FIX Phase 1 (review 2026-04-12) : préparer les extensions avant qu'Alembic tourne
-- =============================================================================
--
-- Ce script est exécuté automatiquement par le container pgvector/pgvector:pg16
-- au premier démarrage (répertoire /docker-entrypoint-initdb.d).
--
-- IMPORTANT : Ce script ne s'exécute QUE si le répertoire postgres_data est vide
-- (i.e., premier démarrage). Il ne rejoue pas à chaque redémarrage.
--
-- En production Supabase, les extensions sont activées via le Dashboard Supabase
-- (Extensions → activer) ou via la migration Alembic initiale.

-- Extension vectorielle pgvector (recherche de similarité cosine, HNSW, IVFFlat)
-- Requise pour : recipe_embeddings, member_taste_vectors
CREATE EXTENSION IF NOT EXISTS vector;

-- Extension de recherche full-text trigram (recherche fuzzy sur les noms de recettes)
-- Requise pour : index GIN sur recipes.name, tag_recipes.name
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Extension UUID v4 (génération d'identifiants uniques côté PostgreSQL)
-- Utilisée par les colonnes id DEFAULT gen_random_uuid() dans Alembic
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Extension pour les statistiques de requêtes (optionnel — utile en dev pour EXPLAIN ANALYZE)
-- Commentée par défaut : activer uniquement si on profil les requêtes localement
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
