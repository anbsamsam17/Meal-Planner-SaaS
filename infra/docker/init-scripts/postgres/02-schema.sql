-- =============================================================================
-- 02-schema.sql
-- Schéma complet Phase 0 — MealPlanner SaaS
--
-- Ce fichier est un assemblage ordonné des sources Phase 0 :
--   00-setup-extensions.sql  → extensions PostgreSQL 16
--   01-schema-core.sql       → tables (13 tables)
--   02-indexes.sql           → index HNSW, GIN trgm, BTREE
--   04-triggers-functions.sql → fonctions et triggers (avant RLS : dépendance)
--   03-rls-policies.sql      → Row Level Security + GRANTs
--
-- Ce fichier remplace Alembic en développement local Docker sur Windows,
-- où asyncpg pose des problèmes de compatibilité avec les migrations.
-- En production Supabase, les migrations Alembic s'appliquent normalement.
--
-- Tous les DDL sont idempotents (IF NOT EXISTS, CREATE OR REPLACE).
-- Exécuté automatiquement au premier démarrage du container postgres
-- (répertoire /docker-entrypoint-initdb.d, après 01-supabase-stubs.sql).
-- =============================================================================


-- =============================================================================
-- === Source: 00-setup-extensions.sql ===
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


-- =============================================================================
-- === Source: 01-schema-core.sql ===
-- Schéma relationnel complet — MealPlanner SaaS
-- PostgreSQL 16 + pgvector + Supabase Auth
-- Ordre de création respecte les dépendances FK (pas de forward references).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- DOMAINE : Auth / Tenancy
-- Un "household" est l'unité de multi-tenancy. Toutes les données utilisateur
-- sont isolées par household_id. C'est le pilier de la Row Level Security.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS households (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Nom du foyer affiché dans l'UI ("Famille Dupont")
    name                TEXT NOT NULL,
    -- Plan tarifaire : starter (gratuit), famille (9,99€), coach (14,99€)
    plan                TEXT NOT NULL DEFAULT 'starter'
                            CHECK (plan IN ('starter', 'famille', 'coach')),
    -- Référence Stripe créée lors de la première souscription (Phase 3)
    stripe_customer_id  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE households IS
    'Unité de tenancy. Chaque foyer est isolé par RLS. Un foyer = un abonnement Stripe.';

CREATE TABLE IF NOT EXISTS household_members (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id     UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    -- Lié à l'utilisateur Supabase Auth. NULL possible pour membres "fantôme" (enfant sans compte).
    supabase_user_id UUID,
    -- Rôle : owner peut gérer l'abonnement, member peut consulter et donner du feedback
    role             TEXT NOT NULL DEFAULT 'member'
                         CHECK (role IN ('owner', 'member')),
    display_name     TEXT NOT NULL,
    birth_date       DATE,
    -- Simplifie l'affichage adaptatif (portions enfant, restrictions spécifiques)
    is_child         BOOLEAN NOT NULL DEFAULT false,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Un utilisateur Supabase ne peut appartenir qu'à un seul foyer à la fois
    UNIQUE (supabase_user_id)
);

COMMENT ON TABLE household_members IS
    'Membres du foyer. supabase_user_id fait le pont entre Supabase Auth et le schéma métier.';

-- -----------------------------------------------------------------------------
-- DOMAINE : Préférences alimentaires
-- Stocké par membre pour permettre la réconciliation des contraintes (WEEKLY_PLANNER).
-- JSONB pour flexibilité : les tags évoluent sans migration de schéma.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS member_preferences (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id         UUID NOT NULL REFERENCES household_members(id) ON DELETE CASCADE,
    -- Ex : ["vegan", "sans-gluten", "halal"]. Validé côté application.
    diet_tags         JSONB NOT NULL DEFAULT '[]',
    -- Ex : ["arachides", "lait", "gluten"]. Critique pour la sécurité alimentaire.
    allergies         JSONB NOT NULL DEFAULT '[]',
    -- Ex : ["épinards", "brocolis"]. Pris en compte mais non bloquant.
    dislikes          JSONB NOT NULL DEFAULT '[]',
    -- Durée maximale acceptable pour la préparation + cuisson (minutes)
    cooking_time_max  INT CHECK (cooking_time_max > 0),
    -- Préférence budget : 'économique', 'moyen', 'premium'
    budget_pref       TEXT CHECK (budget_pref IN ('économique', 'moyen', 'premium')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (member_id)
);

COMMENT ON TABLE member_preferences IS
    'Préférences alimentaires par membre. diet_tags et allergies sont lus par WEEKLY_PLANNER '
    'pour filtrer les recettes incompatibles avant toute recommandation.';

-- -----------------------------------------------------------------------------
-- DOMAINE : Catalogue de recettes (global, non-tenant)
-- Les recettes sont publiques en lecture. Les writes sont réservés au service role
-- (pipeline RECIPE_SCOUT en batch Celery). Pas de household_id ici.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS recipes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Origine de la recette pour traçabilité et droits : 'marmiton', 'allrecipes', 'llm', etc.
    source          TEXT NOT NULL,
    source_url      TEXT,
    title           TEXT NOT NULL,
    -- Slug URL-friendly généré depuis le titre, utilisé dans les routes Next.js
    slug            TEXT NOT NULL UNIQUE,
    description     TEXT,
    -- Instructions structurées : [{"step": 1, "text": "...", "duration_min": 5}, ...]
    instructions    JSONB NOT NULL DEFAULT '[]',
    servings        INT NOT NULL CHECK (servings > 0),
    prep_time_min   INT CHECK (prep_time_min >= 0),
    cook_time_min   INT CHECK (cook_time_min >= 0),
    total_time_min  INT GENERATED ALWAYS AS (COALESCE(prep_time_min, 0) + COALESCE(cook_time_min, 0)) STORED,
    -- 1 = très facile, 2 = facile, 3 = moyen, 4 = difficile, 5 = très difficile
    -- Convention alignée avec RECIPE_SCOUT (mapping very_hard → 5) et API (Field ge=1, le=5).
    difficulty      INT CHECK (difficulty BETWEEN 1 AND 5),
    cuisine_type    TEXT,
    photo_url       TEXT,
    -- Infos nutritionnelles par portion : {"calories": 450, "proteins_g": 30, ...}
    nutrition       JSONB NOT NULL DEFAULT '{}',
    -- Tags libres pour filtrage : ["sans-gluten", "rapide", "hiver", "végétarien"]
    tags            TEXT[] NOT NULL DEFAULT '{}',
    -- Score qualité calculé par le pipeline LLM (0.0 à 1.0).
    -- Règle ROADMAP : toute recette avec quality_score < 0.6 est rejetée avant insertion.
    quality_score   NUMERIC(3,2) NOT NULL DEFAULT 0.0
                        CHECK (quality_score BETWEEN 0.0 AND 1.0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE recipes IS
    'Catalogue global de recettes. Non isolé par tenant (données publiques). '
    'Peuplé exclusivement par RECIPE_SCOUT via service role. '
    'quality_score < 0.6 interdit par trigger (voir 04-triggers-functions.sql).';

-- Vecteurs d'embedding séparés pour ne pas alourdir les requêtes sur recipes.
-- Dimension 384 = sentence-transformers/all-MiniLM-L6-v2 (local, coût zéro).
-- OPT #1 (review 2026-04-12) : Dénormalisation des colonnes hot-path depuis recipes.
-- Raison : la query "5 recettes similaires filtrées par régime + temps" (WEEKLY_PLANNER)
-- nécessitait un JOIN recipes + filtre post-HNSW, causant une latence estimée 150-400ms.
-- En dénormalisant tags, total_time_min, difficulty et cuisine_type ici, le filtre WHERE
-- peut s'appliquer AVANT le scan HNSW sur la table déjà en cache → cible <100ms.
-- Ces colonnes sont maintenues en sync par le trigger recipe_embeddings_sync_metadata.
CREATE TABLE IF NOT EXISTS recipe_embeddings (
    recipe_id       UUID PRIMARY KEY REFERENCES recipes(id) ON DELETE CASCADE,
    -- vector(384) correspond à all-MiniLM-L6-v2. Ne JAMAIS mélanger des vecteurs
    -- générés par des modèles différents dans la même colonne.
    embedding       vector(384) NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- OPT #1 (review 2026-04-12) : colonnes dénormalisées depuis recipes pour pré-filtrage HNSW.
    -- Maintenues en sync automatiquement par le trigger recipe_embeddings_sync_metadata.
    -- Ne pas modifier directement : utiliser UPDATE sur recipes, le trigger propage.
    tags            TEXT[]  NOT NULL DEFAULT '{}',
    total_time_min  INT,
    difficulty      INT,
    cuisine_type    TEXT
);

COMMENT ON TABLE recipe_embeddings IS
    'Embeddings pgvector 384 dims (all-MiniLM-L6-v2). '
    'Relation 1:1 avec recipes. Séparée pour ne pas pénaliser les requêtes sans similarité. '
    'Colonnes dénormalisées (tags, total_time_min, difficulty, cuisine_type) maintenues '
    'par trigger pour permettre le pré-filtrage avant scan HNSW (latence cible <100ms).';

-- Ingrédients normalisés (canonical form pour déduplication et mapping Open Food Facts)
-- MISSION 2.3 + MISSION 3 : colonnes Open Food Facts (migrations 0004/0005 non jouées sur Windows)
-- Ces colonnes sont incluses directement dans le schéma d'init Docker pour qu'elles
-- soient présentes dès le premier démarrage, sans avoir à jouer les migrations Alembic.
CREATE TABLE IF NOT EXISTS ingredients (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Nom canonique normalisé : "carotte" (pas "carottes", "Carotte", "carotte râpée")
    canonical_name TEXT NOT NULL UNIQUE,
    -- Catégorie rayon : 'légume', 'viande', 'produit-laitier', 'épicerie', 'poisson', etc.
    category       TEXT NOT NULL,
    -- Unité par défaut pour normalisation : 'g', 'ml', 'pièce', 'c.à.s.'
    unit_default   TEXT NOT NULL DEFAULT 'g',
    -- === Colonnes Open Food Facts (Phase 1 mature — migration 0004) ===
    -- ID produit Open Food Facts (null = pas encore mappé)
    off_id         TEXT,
    -- Timestamp de la dernière tentative de mapping OFF (NULL = jamais tenté = priorité maximale)
    off_last_checked_at TIMESTAMPTZ,
    -- Score de confiance du match OFF (0.0-1.0). NULL si pas encore mappé. Seuil rejet : < 0.5
    off_match_confidence FLOAT,
    -- Snapshot du nom du produit OFF pour affichage drive sans re-requête API OFF
    off_product_name TEXT,
    -- Marque du produit OFF (optionnel, affiché dans la liste de courses)
    off_brand      TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE ingredients IS
    'Référentiel canonique des ingrédients. Normalisé pour le mapping Open Food Facts (Phase 4). '
    'off_id null = ingrédient non encore mappé à un produit drive. '
    'Colonnes off_* : mapping Open Food Facts (Phase 1 mature — migration 0004).';

-- Index UNIQUE partiel sur off_id (NULL exclus) pour garantir l'unicité des produits OFF mappés
-- sans bloquer les ingrédients non encore mappés (off_id = NULL autorisé en multiple).
CREATE UNIQUE INDEX IF NOT EXISTS ix_ingredients_off_id_partial
    ON ingredients (off_id)
    WHERE off_id IS NOT NULL;

COMMENT ON INDEX ix_ingredients_off_id_partial IS
    'Index UNIQUE partiel : un seul ingrédient peut être lié à un product_code OFF donné. '
    'Les ingrédients non mappés (off_id NULL) sont exclus de la contrainte (multi-NULL autorisé).';

-- Table de liaison recette ↔ ingrédient avec quantité et position pour l'affichage
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id     UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
    quantity      NUMERIC(10,3) NOT NULL CHECK (quantity > 0),
    unit          TEXT NOT NULL,
    -- Notes optionnelles : "coupé en dés", "râpé", "à température ambiante"
    notes         TEXT,
    -- Ordre d'affichage dans la liste des ingrédients
    position      INT NOT NULL DEFAULT 0,
    PRIMARY KEY (recipe_id, ingredient_id)
);

COMMENT ON TABLE recipe_ingredients IS
    'Association recette ↔ ingrédient avec quantité. '
    'position permet d''afficher les ingrédients dans l''ordre éditorial de la source.';

-- -----------------------------------------------------------------------------
-- DOMAINE : Taste profile — moteur de personnalisation (TASTE_PROFILE agent)
-- -----------------------------------------------------------------------------

-- Vecteur de goût par membre, mis à jour après chaque feedback.
-- Représente les préférences latentes du membre dans l'espace d'embedding des recettes.
CREATE TABLE IF NOT EXISTS member_taste_vectors (
    member_id  UUID PRIMARY KEY REFERENCES household_members(id) ON DELETE CASCADE,
    -- Même dimension que recipe_embeddings pour permettre la recherche cosine directe
    vector     vector(384) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE member_taste_vectors IS
    'Vecteur de goût synthétique mis à jour par TASTE_PROFILE après chaque feedback. '
    'La recherche cosine member_taste_vectors.vector ↔ recipe_embeddings.embedding '
    'est le cœur du moteur de recommandation.';

-- Feedback utilisateur sur les recettes — source de vérité pour l'apprentissage du goût
CREATE TABLE IF NOT EXISTS recipe_feedbacks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- household_id dénormalisé ici pour simplifier les politiques RLS sur cette table
    household_id  UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    member_id     UUID NOT NULL REFERENCES household_members(id) ON DELETE CASCADE,
    recipe_id     UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    -- NULL si l'utilisateur a seulement skippé ou favoritisé sans noter
    rating        INT CHECK (rating BETWEEN 1 AND 5),
    -- Type d'interaction : 'cooked' (cuisiné), 'skipped' (ignoré), 'favorited' (coup de cœur)
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('cooked', 'skipped', 'favorited')),
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE recipe_feedbacks IS
    'Journal de tous les feedbacks utilisateur. Chaque entrée déclenche une mise à jour '
    'asynchrone de member_taste_vectors via TASTE_PROFILE (tâche Celery). '
    'household_id dénormalisé pour simplifier la politique RLS.';

-- -----------------------------------------------------------------------------
-- DOMAINE : Planification hebdomadaire (WEEKLY_PLANNER agent)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS weekly_plans (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    -- Toujours un lundi (validé côté application ET par contrainte DB — M6 fix 2026-04-12)
    week_start   DATE NOT NULL,
    -- draft = en cours de génération/édition, validated = validé par l'utilisateur,
    -- archived = semaine passée
    status       TEXT NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft', 'validated', 'archived')),
    -- N1 fix (review 2026-04-12) : timestamp de validation → déclenche génération PDF.
    -- NULL tant que le plan est en draft.
    validated_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Un seul plan par foyer par semaine
    UNIQUE (household_id, week_start),
    -- M6 fix (review 2026-04-12) : ISODOW 1=lundi (ISO 8601).
    CONSTRAINT weekly_plans_week_start_monday_check
        CHECK (EXTRACT(ISODOW FROM week_start) = 1)
);

COMMENT ON TABLE weekly_plans IS
    'Plan de dîners hebdomadaire généré par WEEKLY_PLANNER. '
    'week_start doit toujours être un lundi (contrainte DB ISODOW + contrainte applicative). '
    'validated_at : timestamp de validation, déclenche la génération PDF eager via Celery. '
    'Seuls les plans status=validated déclenchent la génération PDF.';

CREATE TABLE IF NOT EXISTS planned_meals (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id          UUID NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
    -- 1=lundi, 2=mardi, ... 7=dimanche
    day_of_week      INT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    -- Slot repas : uniquement 'dinner' pour la v0/v1, extensible en v2 (déjeuner)
    slot             TEXT NOT NULL DEFAULT 'dinner' CHECK (slot IN ('dinner', 'lunch')),
    recipe_id        UUID NOT NULL REFERENCES recipes(id) ON DELETE RESTRICT,
    -- Permet d'ajuster les portions au nombre de membres du foyer
    servings_adjusted INT NOT NULL CHECK (servings_adjusted > 0),
    UNIQUE (plan_id, day_of_week, slot)
);

COMMENT ON TABLE planned_meals IS
    'Repas individuels composant un plan hebdomadaire. '
    'servings_adjusted permet de scaler les quantités sans modifier la recette source.';

-- Liste de courses générée depuis un plan validé
CREATE TABLE IF NOT EXISTS shopping_lists (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id      UUID NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
    -- Structure : [{"ingredient_id": "...", "name": "carotte", "quantity": 500, "unit": "g", "aisle": "légumes"}, ...]
    items        JSONB NOT NULL DEFAULT '[]',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (plan_id)
);

COMMENT ON TABLE shopping_lists IS
    'Liste de courses consolidée générée par CART_BUILDER à partir d''un plan validé. '
    'items est un JSONB pour flexibilité (structure évoluera en Phase 4 avec SKU drive). '
    'Partagée en temps réel via Supabase Realtime.';

-- -----------------------------------------------------------------------------
-- DOMAINE : Gestion du frigo (mode anti-gaspi — v2)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fridge_items (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id  UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
    quantity      NUMERIC(10,3) NOT NULL CHECK (quantity > 0),
    unit          TEXT NOT NULL,
    -- NULL si la date d'expiration n'est pas renseignée (produit non périssable)
    expiry_date   DATE,
    added_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE fridge_items IS
    'Stock frigo actuel du foyer. WEEKLY_PLANNER lit cette table pour prioriser '
    'les recettes utilisant les ingrédients proches de leur date de péremption (anti-gaspi).';

-- -----------------------------------------------------------------------------
-- DOMAINE : Livres PDF hebdomadaires (BOOK_GENERATOR agent)
-- -----------------------------------------------------------------------------

-- MISSION 3 : content_hash présent dès l'init (migration 0003 non jouée sur Windows)
-- Idempotence Phase 3 : si content_hash identique, BOOK_GENERATOR retourne le PDF existant.
CREATE TABLE IF NOT EXISTS weekly_books (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id         UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    plan_id              UUID NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
    -- Clé Cloudflare R2 : "books/{household_id}/{year-week}.pdf"
    pdf_r2_key           TEXT NOT NULL,
    -- SHA-256 du contenu logique du plan (recettes + portions) — idempotence génération PDF
    content_hash         TEXT,
    generated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- NULL = notification non encore envoyée (Celery beat vérifie ce champ)
    notification_sent_at TIMESTAMPTZ,
    UNIQUE (plan_id)
);

COMMENT ON TABLE weekly_books IS
    'Référence au PDF généré par BOOK_GENERATOR chaque dimanche. '
    'pdf_r2_key pointe vers Cloudflare R2. notification_sent_at = NULL déclenche '
    'l''envoi push/email par RETENTION_LOOP. '
    'content_hash : SHA-256 pour idempotence de génération (migration 0003).';

-- -----------------------------------------------------------------------------
-- DOMAINE : Stripe subscriptions (stub Phase 3)
-- Tables créées maintenant pour éviter une migration destructive plus tard.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id        UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    stripe_sub_id       TEXT NOT NULL UNIQUE,
    plan                TEXT NOT NULL CHECK (plan IN ('starter', 'famille', 'coach')),
    -- Statut Stripe : active, past_due, canceled, trialing
    status              TEXT NOT NULL,
    current_period_end  TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (household_id)
);

COMMENT ON TABLE subscriptions IS
    'Stub Stripe — Phase 3. Créée maintenant pour éviter une migration breaking en v2. '
    'Non peuplée en Phase 0/1. Le plan households.plan est la source de vérité '
    'jusqu''à l''activation de Stripe.';


-- =============================================================================
-- === Source: 02-indexes.sql ===
-- Stratégie d'indexation — MealPlanner SaaS
-- À exécuter APRÈS 01-schema-core.sql.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- INDEX HNSW — Recherche vectorielle pgvector
-- HNSW offre le meilleur compromis latence/rappel pour 50 000–500 000 vecteurs.
-- m=16 : connexions par nœud (↑m → ↑rappel mais ↑mémoire)
-- ef_construction=64 : qualité de construction (↑ef → ↑précision mais ↑temps de build)
-- ef_search : paramètre de SESSION (SET LOCAL hnsw.ef_search = 80) — pas dans le DDL.
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_hnsw
    ON recipe_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

COMMENT ON INDEX idx_recipe_embeddings_hnsw IS
    'Index HNSW pour recherche par similarité cosine (TASTE_PROFILE + WEEKLY_PLANNER). '
    'Cible : latence < 50ms sur 50 000 vecteurs avec ef_search=40 (paramètre runtime). '
    'ef_search se règle en runtime : SET LOCAL hnsw.ef_search = 80 (plans) ou 40 (feed).';

-- OPT #1 (review 2026-04-12) : Index GIN sur les tags dénormalisés dans recipe_embeddings.
-- Pré-filtrage "tags && ARRAY[régimes_exclus]" AVANT le scan HNSW.
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_tags_gin
    ON recipe_embeddings USING gin (tags);

COMMENT ON INDEX idx_recipe_embeddings_tags_gin IS
    'OPT #1 (review 2026-04-12) : Index GIN sur les tags dénormalisés. '
    'Permet le pré-filtrage WHERE tags @> ARRAY[...] AVANT le scan HNSW. '
    'Essentiel pour que la query WEEKLY_PLANNER respecte le SLA <5s génération plan.';

-- OPT #1 (review 2026-04-12) : Index BTREE partiel sur total_time_min dénormalisé.
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_total_time
    ON recipe_embeddings (total_time_min)
    WHERE total_time_min IS NOT NULL;

COMMENT ON INDEX idx_recipe_embeddings_total_time IS
    'OPT #1 (review 2026-04-12) : Index partiel sur total_time_min dénormalisé. '
    'Permet WHERE total_time_min <= $1 en index scan avant passage au HNSW.';

-- OPT #1 (review 2026-04-12) : Index composite couvrant pour la stratégie deux étapes.
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_filter_composite
    ON recipe_embeddings (total_time_min, cuisine_type)
    INCLUDE (recipe_id)
    WHERE total_time_min IS NOT NULL;

COMMENT ON INDEX idx_recipe_embeddings_filter_composite IS
    'OPT #1 (review 2026-04-12) : Index composite hot-path pour la stratégie deux étapes. '
    'Étape 1 : SELECT recipe_id WHERE total_time_min <= $1 AND cuisine_type = $2 (index-only). '
    'Étape 2 : SELECT ... ORDER BY embedding <=> $vec (HNSW sur sous-ensemble filtré).';

-- Index HNSW sur les vecteurs de goût membres (corpus plus petit)
CREATE INDEX IF NOT EXISTS idx_member_taste_vectors_hnsw
    ON member_taste_vectors
    USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 32);

COMMENT ON INDEX idx_member_taste_vectors_hnsw IS
    'Index HNSW sur les vecteurs de goût membres. Corpus petit (< 10 000 membres max). '
    'Utilisé pour trouver des membres similaires en mode "famille découverte".';

-- -----------------------------------------------------------------------------
-- INDEX BTREE — household_id (clé de tenancy)
-- Présent sur TOUTES les tables avec données utilisateur.
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_household_members_household_id
    ON household_members (household_id);

CREATE INDEX IF NOT EXISTS idx_member_preferences_member_id
    ON member_preferences (member_id);

CREATE INDEX IF NOT EXISTS idx_recipe_feedbacks_household_id
    ON recipe_feedbacks (household_id);

CREATE INDEX IF NOT EXISTS idx_recipe_feedbacks_member_id
    ON recipe_feedbacks (member_id);

CREATE INDEX IF NOT EXISTS idx_recipe_feedbacks_recipe_id
    ON recipe_feedbacks (recipe_id);

CREATE INDEX IF NOT EXISTS idx_weekly_plans_household_id
    ON weekly_plans (household_id);

-- Index composite pour la requête la plus fréquente : "plan de la semaine courante du foyer"
CREATE INDEX IF NOT EXISTS idx_weekly_plans_household_week
    ON weekly_plans (household_id, week_start DESC);

CREATE INDEX IF NOT EXISTS idx_planned_meals_plan_id
    ON planned_meals (plan_id);

CREATE INDEX IF NOT EXISTS idx_fridge_items_household_id
    ON fridge_items (household_id);

-- Index sur expiry_date pour la requête anti-gaspi : "ingrédients qui périment bientôt"
CREATE INDEX IF NOT EXISTS idx_fridge_items_expiry
    ON fridge_items (household_id, expiry_date ASC NULLS LAST)
    WHERE expiry_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_weekly_books_household_id
    ON weekly_books (household_id);

-- -----------------------------------------------------------------------------
-- INDEX GIN — Recherche dans les tableaux et colonnes JSONB
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_recipes_tags_gin
    ON recipes USING gin (tags);

CREATE INDEX IF NOT EXISTS idx_recipes_nutrition_gin
    ON recipes USING gin (nutrition jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_member_preferences_diet_tags_gin
    ON member_preferences USING gin (diet_tags jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_member_preferences_allergies_gin
    ON member_preferences USING gin (allergies jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_shopping_lists_items_gin
    ON shopping_lists USING gin (items jsonb_path_ops);

-- -----------------------------------------------------------------------------
-- INDEX GIN trgm — Recherche full-text FR sur le titre des recettes
-- MISSION 2.1 : index pg_trgm sur recipes.title (confirmé présent et nommé)
-- pg_trgm + GIN permet : ILIKE '%coq au vin%', similarité avec fautes de frappe.
-- Latence cible : < 10ms sur 50 000 recettes avec cet index.
-- -----------------------------------------------------------------------------

-- Index nommé ix_recipes_title_trgm (nom utilisé dans le commentaire MISSION 2.1)
CREATE INDEX IF NOT EXISTS ix_recipes_title_trgm
    ON recipes USING gin (title gin_trgm_ops);

-- Alias idx_ pour compatibilité avec les commentaires phase-0 originaux
-- (Les deux noms coexistent : ix_ est le nom canonique, idx_ est le nom legacy)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'recipes' AND indexname = 'idx_recipes_title_trgm'
    ) THEN
        CREATE INDEX idx_recipes_title_trgm ON recipes USING gin (title gin_trgm_ops);
    END IF;
END$$;

-- Index trgm sur canonical_name des ingrédients pour la saisie frigo (autocomplétion)
CREATE INDEX IF NOT EXISTS idx_ingredients_canonical_name_trgm
    ON ingredients USING gin (canonical_name gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- INDEX BTREE standard — Colonnes de filtrage fréquentes sur recipes
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_recipes_cuisine_difficulty
    ON recipes (cuisine_type, difficulty);

CREATE INDEX IF NOT EXISTS idx_recipes_total_time
    ON recipes (total_time_min ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_recipes_quality_score
    ON recipes (quality_score DESC);

-- -----------------------------------------------------------------------------
-- INDEX PARTIELS — Optimisation pour les sous-ensembles fréquents
-- -----------------------------------------------------------------------------

-- Plans en cours d'édition : status='draft' uniquement
CREATE INDEX IF NOT EXISTS idx_weekly_plans_draft
    ON weekly_plans (household_id, week_start)
    WHERE status = 'draft';

COMMENT ON INDEX idx_weekly_plans_draft IS
    'Index partiel : seuls les plans en cours d''édition sont ciblés. '
    'Les plans archived (majorité) sont exclus, réduisant la taille de l''index de ~80%.';

-- Livres sans notification envoyée (RETENTION_LOOP poll toutes les 4h)
CREATE INDEX IF NOT EXISTS idx_weekly_books_unsent_notification
    ON weekly_books (generated_at)
    WHERE notification_sent_at IS NULL;

-- Feedbacks de type 'favorited' (collection coups de cœur)
CREATE INDEX IF NOT EXISTS idx_recipe_feedbacks_favorited
    ON recipe_feedbacks (household_id, recipe_id)
    WHERE feedback_type = 'favorited';

-- Membres avec compte Supabase Auth (exclus les membres "fantôme")
CREATE INDEX IF NOT EXISTS idx_household_members_with_auth
    ON household_members (supabase_user_id, household_id)
    WHERE supabase_user_id IS NOT NULL;

-- Index pour le workflow de mapping OFF : priorité aux ingrédients jamais tentés
CREATE INDEX IF NOT EXISTS idx_ingredients_off_unmapped
    ON ingredients (off_last_checked_at NULLS FIRST)
    WHERE off_id IS NULL;

COMMENT ON INDEX idx_ingredients_off_unmapped IS
    'MISSION 2.3 : accélère la queue de mapping Open Food Facts. '
    'SELECT ... WHERE off_id IS NULL ORDER BY off_last_checked_at NULLS FIRST LIMIT 50 '
    'utilise cet index partiel (corpus réduit aux non-mappés uniquement).';


-- =============================================================================
-- === Source: 04-triggers-functions.sql ===
-- Fonctions PostgreSQL et triggers — MealPlanner SaaS
-- Exécuté AVANT 03-rls-policies.sql (get_current_household_id est une dépendance).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- FONCTION : get_current_household_id()
-- Retourne le household_id de l'utilisateur Supabase Auth connecté.
-- Utilisée dans TOUTES les policies RLS pour centraliser la logique d'appartenance.
-- SECURITY DEFINER + search_path vide : prévient l'injection via search_path.
-- STABLE : PostgreSQL peut mettre en cache le résultat pour la transaction.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION get_current_household_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path TO ''
AS $$
    SELECT household_id
    FROM public.household_members
    WHERE supabase_user_id = auth.uid()
    LIMIT 1;
$$;

COMMENT ON FUNCTION get_current_household_id() IS
    'Retourne le household_id de l''utilisateur JWT connecté. '
    'SECURITY DEFINER + search_path vide pour prévenir l''injection via search_path. '
    'Appelée dans toutes les policies RLS pour éviter la duplication de sous-requêtes. '
    'Retourne NULL si l''utilisateur n''appartient à aucun foyer (nouveau compte).';

-- -----------------------------------------------------------------------------
-- FONCTION + TRIGGER : updated_at automatique
-- Mise à jour automatique du champ updated_at à chaque UPDATE.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO ''
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION trigger_set_updated_at() IS
    'Trigger générique : force updated_at = now() sur tout UPDATE. '
    'Protège contre les mises à jour silencieuses qui oublieraient ce champ.';

-- Triggers updated_at sur toutes les tables concernées
-- CREATE OR REPLACE TRIGGER n'existe pas en PG < 14 pour les triggers normaux.
-- On utilise DROP IF EXISTS + CREATE pour idempotence.
DROP TRIGGER IF EXISTS set_updated_at_households ON households;
CREATE TRIGGER set_updated_at_households
    BEFORE UPDATE ON households
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_household_members ON household_members;
CREATE TRIGGER set_updated_at_household_members
    BEFORE UPDATE ON household_members
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_member_preferences ON member_preferences;
CREATE TRIGGER set_updated_at_member_preferences
    BEFORE UPDATE ON member_preferences
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_recipes ON recipes;
CREATE TRIGGER set_updated_at_recipes
    BEFORE UPDATE ON recipes
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_recipe_embeddings ON recipe_embeddings;
CREATE TRIGGER set_updated_at_recipe_embeddings
    BEFORE UPDATE ON recipe_embeddings
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_weekly_plans ON weekly_plans;
CREATE TRIGGER set_updated_at_weekly_plans
    BEFORE UPDATE ON weekly_plans
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

DROP TRIGGER IF EXISTS set_updated_at_subscriptions ON subscriptions;
CREATE TRIGGER set_updated_at_subscriptions
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- -----------------------------------------------------------------------------
-- TRIGGER : validation qualité des recettes avant insertion
-- quality_score < 0.6 → rejet. Règle ROADMAP.
-- Le trigger donne un message d'erreur lisible pour les logs Celery (RECIPE_SCOUT).
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_recipe_quality()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO ''
AS $$
BEGIN
    IF NEW.quality_score < 0.6 THEN
        RAISE EXCEPTION
            'Recette rejetée : quality_score=% insuffisant (seuil=0.6). '
            'Recette : %. Source : %.',
            NEW.quality_score,
            NEW.title,
            NEW.source
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.instructions = '[]'::jsonb OR NEW.instructions IS NULL THEN
        RAISE EXCEPTION
            'Recette rejetée : instructions vides. Recette : %. Source : %.',
            NEW.title,
            NEW.source
            USING ERRCODE = 'check_violation';
    END IF;

    IF COALESCE(NEW.prep_time_min, 0) + COALESCE(NEW.cook_time_min, 0) = 0 THEN
        RAISE WARNING
            'Recette % (source: %) : temps total = 0 minute. Vérifier les données source.',
            NEW.title,
            NEW.source;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION validate_recipe_quality() IS
    'Trigger BEFORE INSERT/UPDATE sur recipes. '
    'Rejette les recettes avec quality_score < 0.6 (règle ROADMAP section 10). '
    'Émet un WARNING (sans rejet) pour les recettes à temps zéro. '
    'Le message d''erreur est loggé par RECIPE_SCOUT via Celery loguru.';

DROP TRIGGER IF EXISTS validate_recipe_quality_before_insert ON recipes;
CREATE TRIGGER validate_recipe_quality_before_insert
    BEFORE INSERT OR UPDATE ON recipes
    FOR EACH ROW EXECUTE FUNCTION validate_recipe_quality();

-- -----------------------------------------------------------------------------
-- FONCTION : get_household_constraints(p_household_id UUID)
-- Vue agrégée des contraintes de tous les membres d'un foyer.
-- FIX #4 (review 2026-04-12) : CTEs séparées pour éviter le produit cartésien JSONB.
-- Budget_pref : CASE WHEN avec ordre sémantique (économique < moyen < premium).
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION get_household_constraints(p_household_id UUID)
RETURNS TABLE (
    allergies_union  JSONB,
    diet_tags_union  JSONB,
    max_cooking_time INT,
    budget_pref      TEXT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path TO ''
AS $$
    WITH allergies_cte AS (
        SELECT DISTINCT a.allergy_item
        FROM public.household_members hm
        JOIN public.member_preferences mp ON mp.member_id = hm.id
        CROSS JOIN LATERAL jsonb_array_elements_text(mp.allergies) AS a(allergy_item)
        WHERE hm.household_id = p_household_id
          AND a.allergy_item IS NOT NULL
    ),
    diets_cte AS (
        SELECT DISTINCT d.diet_item
        FROM public.household_members hm
        JOIN public.member_preferences mp ON mp.member_id = hm.id
        CROSS JOIN LATERAL jsonb_array_elements_text(mp.diet_tags) AS d(diet_item)
        WHERE hm.household_id = p_household_id
          AND d.diet_item IS NOT NULL
    ),
    scalars_cte AS (
        SELECT
            MIN(mp.cooking_time_max) AS max_cooking_time,
            MIN(
                CASE mp.budget_pref
                    WHEN 'économique' THEN 1
                    WHEN 'moyen'      THEN 2
                    WHEN 'premium'    THEN 3
                    ELSE NULL
                END
            ) AS budget_pref_rank
        FROM public.household_members hm
        JOIN public.member_preferences mp ON mp.member_id = hm.id
        WHERE hm.household_id = p_household_id
    )
    SELECT
        (SELECT jsonb_agg(allergy_item) FROM allergies_cte) AS allergies_union,
        (SELECT jsonb_agg(diet_item)    FROM diets_cte)     AS diet_tags_union,
        (SELECT max_cooking_time        FROM scalars_cte)   AS max_cooking_time,
        (SELECT CASE budget_pref_rank
                    WHEN 1 THEN 'économique'
                    WHEN 2 THEN 'moyen'
                    WHEN 3 THEN 'premium'
                    ELSE NULL
                END
         FROM scalars_cte) AS budget_pref;
$$;

COMMENT ON FUNCTION get_household_constraints(UUID) IS
    'Agrège les contraintes alimentaires de tous les membres d''un foyer. '
    'Utilisée par WEEKLY_PLANNER avant chaque génération de plan. '
    'FIX #4 (2026-04-12) : CTEs séparées pour éviter le produit cartésien JSONB. '
    'Budget_pref résolu par CASE WHEN (ordre sémantique) et non MIN(TEXT) (ordre lexicographique).';

-- -----------------------------------------------------------------------------
-- FONCTION : cleanup_old_embeddings()
-- Supprime les embeddings orphelins (recettes supprimées).
-- HIGH-3 (review 2026-04-12) : NOT IN remplacé par NOT EXISTS (NULL-safe).
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION cleanup_old_embeddings()
RETURNS INT
LANGUAGE plpgsql
SET search_path TO ''
AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM public.recipe_embeddings re
    WHERE NOT EXISTS (
        SELECT 1 FROM public.recipes r WHERE r.id = re.recipe_id
    );

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    IF deleted_count > 0 THEN
        RAISE NOTICE 'Nettoyage embeddings : % entrées orphelines supprimées.', deleted_count;
    END IF;

    RETURN deleted_count;
END;
$$;

COMMENT ON FUNCTION cleanup_old_embeddings() IS
    'Maintenance : supprime les vecteurs d''embeddings dont la recette parente a été supprimée. '
    'Appelée par la tâche Celery beat hebdomadaire (cleanup_embeddings_task). '
    'HIGH-3 (2026-04-12) : NOT IN remplacé par NOT EXISTS (NULL-safe + planner-friendly).';

-- -----------------------------------------------------------------------------
-- FONCTION : create_household_with_owner()
-- BUG #2 (review 2026-04-12) : création atomique foyer + owner via SECURITY DEFINER.
-- Résout le deadlock d'onboarding causé par la récursion RLS sur household_members.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION create_household_with_owner(
    p_household_name  TEXT,
    p_supabase_user_id UUID,
    p_display_name    TEXT
)
RETURNS TABLE (
    household_id UUID,
    member_id    UUID
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO ''
AS $$
DECLARE
    v_household_id UUID;
    v_member_id    UUID;
BEGIN
    IF EXISTS (
        SELECT 1 FROM public.household_members
        WHERE supabase_user_id = p_supabase_user_id
    ) THEN
        RAISE EXCEPTION
            'L''utilisateur % appartient déjà à un foyer. '
            'Un utilisateur Supabase ne peut appartenir qu''à un seul foyer.',
            p_supabase_user_id
            USING ERRCODE = 'unique_violation';
    END IF;

    INSERT INTO public.households (name)
    VALUES (p_household_name)
    RETURNING id INTO v_household_id;

    INSERT INTO public.household_members (household_id, supabase_user_id, role, display_name)
    VALUES (v_household_id, p_supabase_user_id, 'owner', p_display_name)
    RETURNING id INTO v_member_id;

    RETURN QUERY SELECT v_household_id, v_member_id;
END;
$$;

COMMENT ON FUNCTION create_household_with_owner(TEXT, UUID, TEXT) IS
    'BUG #2 (2026-04-12) : Création atomique d''un foyer avec son premier owner. '
    'Bypasse la RLS via SECURITY DEFINER pour résoudre le deadlock d''onboarding. '
    'Appelée côté API FastAPI avec supabase_client configuré avec SUPABASE_SERVICE_ROLE_KEY.';

-- -----------------------------------------------------------------------------
-- OPT #1 (review 2026-04-12) : Trigger de synchronisation des colonnes dénormalisées
-- dans recipe_embeddings depuis recipes.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION recipe_embeddings_sync_metadata()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path TO ''
AS $$
BEGIN
    IF (NEW.tags          IS DISTINCT FROM OLD.tags)
    OR (NEW.total_time_min IS DISTINCT FROM OLD.total_time_min)
    OR (NEW.difficulty     IS DISTINCT FROM OLD.difficulty)
    OR (NEW.cuisine_type   IS DISTINCT FROM OLD.cuisine_type)
    THEN
        UPDATE public.recipe_embeddings
        SET
            tags           = NEW.tags,
            total_time_min = NEW.total_time_min,
            difficulty     = NEW.difficulty,
            cuisine_type   = NEW.cuisine_type,
            updated_at     = now()
        WHERE recipe_id = NEW.id;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION recipe_embeddings_sync_metadata() IS
    'OPT #1 (2026-04-12) : Synchronise les colonnes dénormalisées dans recipe_embeddings '
    'quand recipes est modifié. Déclenché AFTER UPDATE uniquement si les colonnes hot-path '
    '(tags, total_time_min, difficulty, cuisine_type) ont réellement changé.';

DROP TRIGGER IF EXISTS sync_recipe_embeddings_metadata ON recipes;
CREATE TRIGGER sync_recipe_embeddings_metadata
    AFTER UPDATE ON recipes
    FOR EACH ROW EXECUTE FUNCTION recipe_embeddings_sync_metadata();


-- =============================================================================
-- === Source: 03-rls-policies.sql ===
-- Row Level Security — MealPlanner SaaS
-- CRITIQUE : protège l'isolation stricte entre foyers (tenants).
-- Exécuté APRÈS 04-triggers-functions.sql (get_current_household_id est disponible).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- ACTIVATION RLS sur toutes les tables tenant-scoped
-- Les tables non listées (recipes, ingredients, recipe_ingredients) sont
-- publiques en lecture → accès géré par les GRANTS ci-dessous.
-- -----------------------------------------------------------------------------

ALTER TABLE households               ENABLE ROW LEVEL SECURITY;
ALTER TABLE household_members        ENABLE ROW LEVEL SECURITY;
ALTER TABLE member_preferences       ENABLE ROW LEVEL SECURITY;
ALTER TABLE member_taste_vectors     ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipe_feedbacks         ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_plans             ENABLE ROW LEVEL SECURITY;
ALTER TABLE planned_meals            ENABLE ROW LEVEL SECURITY;
ALTER TABLE shopping_lists           ENABLE ROW LEVEL SECURITY;
ALTER TABLE fridge_items             ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_books             ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions            ENABLE ROW LEVEL SECURITY;

-- FORCE RLS même pour le propriétaire de la table (sécurité défensive)
ALTER TABLE households               FORCE ROW LEVEL SECURITY;
ALTER TABLE household_members        FORCE ROW LEVEL SECURITY;
ALTER TABLE member_preferences       FORCE ROW LEVEL SECURITY;
ALTER TABLE member_taste_vectors     FORCE ROW LEVEL SECURITY;
ALTER TABLE recipe_feedbacks         FORCE ROW LEVEL SECURITY;
ALTER TABLE weekly_plans             FORCE ROW LEVEL SECURITY;
ALTER TABLE planned_meals            FORCE ROW LEVEL SECURITY;
ALTER TABLE shopping_lists           FORCE ROW LEVEL SECURITY;
ALTER TABLE fridge_items             FORCE ROW LEVEL SECURITY;
ALTER TABLE weekly_books             FORCE ROW LEVEL SECURITY;
ALTER TABLE subscriptions            FORCE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- POLICIES : households
-- Un utilisateur ne voit que SON foyer.
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS households_select ON households;
CREATE POLICY households_select
    ON households FOR SELECT TO authenticated
    USING (
        id IN (
            SELECT household_id FROM household_members
            WHERE supabase_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS households_update ON households;
CREATE POLICY households_update
    ON households FOR UPDATE TO authenticated
    USING (
        id IN (
            SELECT household_id FROM household_members
            WHERE supabase_user_id = auth.uid() AND role = 'owner'
        )
    )
    WITH CHECK (
        id IN (
            SELECT household_id FROM household_members
            WHERE supabase_user_id = auth.uid() AND role = 'owner'
        )
    );

DROP POLICY IF EXISTS households_insert ON households;
CREATE POLICY households_insert
    ON households FOR INSERT TO authenticated
    WITH CHECK (true);

-- -----------------------------------------------------------------------------
-- POLICIES : household_members
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS household_members_select ON household_members;
CREATE POLICY household_members_select
    ON household_members FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());

DROP POLICY IF EXISTS household_members_update ON household_members;
CREATE POLICY household_members_update
    ON household_members FOR UPDATE TO authenticated
    USING (
        household_id = get_current_household_id()
        AND (
            supabase_user_id = (SELECT auth.uid())
            OR EXISTS (
                SELECT 1 FROM household_members hm
                WHERE hm.supabase_user_id = (SELECT auth.uid())
                  AND hm.household_id = household_members.household_id
                  AND hm.role = 'owner'
            )
        )
    )
    WITH CHECK (household_id = get_current_household_id());

-- -----------------------------------------------------------------------------
-- POLICIES : member_preferences
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS member_preferences_select ON member_preferences;
CREATE POLICY member_preferences_select
    ON member_preferences FOR SELECT TO authenticated
    USING (
        member_id IN (
            SELECT id FROM household_members
            WHERE household_id = get_current_household_id()
        )
    );

DROP POLICY IF EXISTS member_preferences_insert ON member_preferences;
CREATE POLICY member_preferences_insert
    ON member_preferences FOR INSERT TO authenticated
    WITH CHECK (
        member_id IN (
            SELECT id FROM household_members
            WHERE household_id = get_current_household_id()
        )
    );

DROP POLICY IF EXISTS member_preferences_update ON member_preferences;
CREATE POLICY member_preferences_update
    ON member_preferences FOR UPDATE TO authenticated
    USING (
        member_id IN (
            SELECT id FROM household_members
            WHERE household_id = get_current_household_id()
        )
    )
    WITH CHECK (
        member_id IN (
            SELECT id FROM household_members
            WHERE household_id = get_current_household_id()
        )
    );

-- -----------------------------------------------------------------------------
-- POLICIES : member_taste_vectors
-- Lecture pour les membres du foyer. Écriture réservée au service_role.
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS member_taste_vectors_select ON member_taste_vectors;
CREATE POLICY member_taste_vectors_select
    ON member_taste_vectors FOR SELECT TO authenticated
    USING (
        member_id IN (
            SELECT id FROM household_members
            WHERE household_id = get_current_household_id()
        )
    );

-- -----------------------------------------------------------------------------
-- POLICIES : recipe_feedbacks
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS recipe_feedbacks_select ON recipe_feedbacks;
CREATE POLICY recipe_feedbacks_select
    ON recipe_feedbacks FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());

DROP POLICY IF EXISTS recipe_feedbacks_insert ON recipe_feedbacks;
CREATE POLICY recipe_feedbacks_insert
    ON recipe_feedbacks FOR INSERT TO authenticated
    WITH CHECK (
        household_id = get_current_household_id()
        AND member_id IN (
            SELECT id FROM household_members
            WHERE supabase_user_id = auth.uid()
        )
    );

-- -----------------------------------------------------------------------------
-- POLICIES : weekly_plans
-- Isolation stricte par household. Supabase Realtime écoute cette table.
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS weekly_plans_select ON weekly_plans;
CREATE POLICY weekly_plans_select
    ON weekly_plans FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());

DROP POLICY IF EXISTS weekly_plans_insert ON weekly_plans;
CREATE POLICY weekly_plans_insert
    ON weekly_plans FOR INSERT TO authenticated
    WITH CHECK (household_id = get_current_household_id());

DROP POLICY IF EXISTS weekly_plans_update ON weekly_plans;
CREATE POLICY weekly_plans_update
    ON weekly_plans FOR UPDATE TO authenticated
    USING (household_id = get_current_household_id())
    WITH CHECK (household_id = get_current_household_id());

DROP POLICY IF EXISTS weekly_plans_delete ON weekly_plans;
CREATE POLICY weekly_plans_delete
    ON weekly_plans FOR DELETE TO authenticated
    USING (
        household_id = get_current_household_id()
        AND status = 'draft'
    );

-- -----------------------------------------------------------------------------
-- POLICIES : planned_meals
-- Accès via le plan parent.
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS planned_meals_select ON planned_meals;
CREATE POLICY planned_meals_select
    ON planned_meals FOR SELECT TO authenticated
    USING (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
        )
    );

DROP POLICY IF EXISTS planned_meals_insert ON planned_meals;
CREATE POLICY planned_meals_insert
    ON planned_meals FOR INSERT TO authenticated
    WITH CHECK (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
        )
    );

DROP POLICY IF EXISTS planned_meals_update ON planned_meals;
CREATE POLICY planned_meals_update
    ON planned_meals FOR UPDATE TO authenticated
    USING (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
              AND status = 'draft'
        )
    )
    WITH CHECK (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
              AND status = 'draft'
        )
    );

DROP POLICY IF EXISTS planned_meals_delete ON planned_meals;
CREATE POLICY planned_meals_delete
    ON planned_meals FOR DELETE TO authenticated
    USING (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
              AND status = 'draft'
        )
    );

-- -----------------------------------------------------------------------------
-- POLICIES : shopping_lists
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS shopping_lists_select ON shopping_lists;
CREATE POLICY shopping_lists_select
    ON shopping_lists FOR SELECT TO authenticated
    USING (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
        )
    );

DROP POLICY IF EXISTS shopping_lists_update ON shopping_lists;
CREATE POLICY shopping_lists_update
    ON shopping_lists FOR UPDATE TO authenticated
    USING (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
        )
    )
    WITH CHECK (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
        )
    );

-- -----------------------------------------------------------------------------
-- POLICIES : fridge_items
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS fridge_items_select ON fridge_items;
CREATE POLICY fridge_items_select
    ON fridge_items FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());

DROP POLICY IF EXISTS fridge_items_insert ON fridge_items;
CREATE POLICY fridge_items_insert
    ON fridge_items FOR INSERT TO authenticated
    WITH CHECK (household_id = get_current_household_id());

DROP POLICY IF EXISTS fridge_items_update ON fridge_items;
CREATE POLICY fridge_items_update
    ON fridge_items FOR UPDATE TO authenticated
    USING (household_id = get_current_household_id())
    WITH CHECK (household_id = get_current_household_id());

DROP POLICY IF EXISTS fridge_items_delete ON fridge_items;
CREATE POLICY fridge_items_delete
    ON fridge_items FOR DELETE TO authenticated
    USING (household_id = get_current_household_id());

-- -----------------------------------------------------------------------------
-- POLICIES : weekly_books
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS weekly_books_select ON weekly_books;
CREATE POLICY weekly_books_select
    ON weekly_books FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());

-- -----------------------------------------------------------------------------
-- POLICIES : subscriptions
-- Lecture pour l'owner uniquement. Écriture par service_role (webhook Stripe).
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS subscriptions_select ON subscriptions;
CREATE POLICY subscriptions_select
    ON subscriptions FOR SELECT TO authenticated
    USING (
        household_id IN (
            SELECT household_id FROM household_members
            WHERE supabase_user_id = auth.uid() AND role = 'owner'
        )
    );

-- -----------------------------------------------------------------------------
-- GRANTS — Tables publiques (recettes, ingrédients)
-- Pas de RLS nécessaire : données non-tenant. SELECT accordé à anon et authenticated.
-- Les writes sont réservés au service_role.
-- -----------------------------------------------------------------------------

GRANT SELECT ON recipes              TO anon, authenticated;
GRANT SELECT ON recipe_embeddings    TO anon, authenticated;
GRANT SELECT ON ingredients          TO anon, authenticated;
GRANT SELECT ON recipe_ingredients   TO anon, authenticated;

DO $$ BEGIN RAISE NOTICE '02-schema.sql : schéma complet Phase 0 appliqué (13 tables, index, triggers, RLS).'; END $$;
