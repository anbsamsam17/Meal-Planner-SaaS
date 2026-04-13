-- =============================================================================
-- 01-schema-core.sql
-- Schéma relationnel complet — MealPlanner SaaS
-- PostgreSQL 16 + pgvector + Supabase Auth
-- Ordre de création respecte les dépendances FK (pas de forward references).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- DOMAINE : Auth / Tenancy
-- Un "household" est l'unité de multi-tenancy. Toutes les données utilisateur
-- sont isolées par household_id. C'est le pilier de la Row Level Security.
-- -----------------------------------------------------------------------------

CREATE TABLE households (
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

CREATE TABLE household_members (
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

CREATE TABLE member_preferences (
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

CREATE TABLE recipes (
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
-- ATTENTION : Si on migre vers OpenAI text-embedding-3-small (1536 dims),
-- il faudra recréer cette colonne ET re-embedder les 50 000 recettes.
--
-- OPT #1 (review 2026-04-12) : Dénormalisation des colonnes hot-path depuis recipes.
-- Raison : la query "5 recettes similaires filtrées par régime + temps" (WEEKLY_PLANNER)
-- nécessitait un JOIN recipes + filtre post-HNSW, causant une latence estimée 150-400ms.
-- En dénormalisant tags, total_time_min, difficulty et cuisine_type ici, le filtre WHERE
-- peut s'appliquer AVANT le scan HNSW sur la table déjà en cache → cible <100ms.
-- Ces colonnes sont maintenues en sync par le trigger recipe_embeddings_sync_metadata
-- défini dans 04-triggers-functions.sql.
CREATE TABLE recipe_embeddings (
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
CREATE TABLE ingredients (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Nom canonique normalisé : "carotte" (pas "carottes", "Carotte", "carotte râpée")
    canonical_name TEXT NOT NULL UNIQUE,
    -- Catégorie rayon : 'légume', 'viande', 'produit-laitier', 'épicerie', 'poisson', etc.
    category       TEXT NOT NULL,
    -- Unité par défaut pour normalisation : 'g', 'ml', 'pièce', 'c.à.s.'
    unit_default   TEXT NOT NULL DEFAULT 'g',
    -- ID produit Open Food Facts (null = pas encore mappé, mapping en Phase 4)
    off_id         TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE ingredients IS
    'Référentiel canonique des ingrédients. Normalisé pour le mapping Open Food Facts (Phase 4). '
    'off_id null = ingrédient non encore mappé à un produit drive.';

-- Table de liaison recette ↔ ingrédient avec quantité et position pour l'affichage
CREATE TABLE recipe_ingredients (
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
CREATE TABLE member_taste_vectors (
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
CREATE TABLE recipe_feedbacks (
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

CREATE TABLE weekly_plans (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    -- Toujours un lundi (validé côté application ET par contrainte DB — M6 fix 2026-04-12)
    week_start   DATE NOT NULL,
    -- draft = en cours de génération/édition, validated = validé par l'utilisateur,
    -- archived = semaine passée
    status       TEXT NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft', 'validated', 'archived')),
    -- N1 fix (review 2026-04-12) : colonne ajoutée pour 13-pdf-generation-strategy.md.
    -- Timestamptz du moment où le plan passe en status='validated'.
    -- Sert de déclencheur à la tâche Celery BOOK_GENERATOR (génération PDF eager).
    -- NULL tant que le plan est en draft. Mis à jour par l'endpoint FastAPI POST /plans/{id}/validate.
    validated_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Un seul plan par foyer par semaine
    UNIQUE (household_id, week_start),
    -- M6 fix (review 2026-04-12) : contrainte DB garantissant que week_start est toujours un lundi.
    -- ISODOW : 1=lundi, 7=dimanche (ISO 8601). EXTRACT(DOW ...) retourne 0=dimanche (non-ISO).
    -- On utilise ISODOW pour la cohérence avec l'ISO 8601 (semaines démarrent lundi).
    CONSTRAINT weekly_plans_week_start_monday_check
        CHECK (EXTRACT(ISODOW FROM week_start) = 1)
);

COMMENT ON TABLE weekly_plans IS
    'Plan de dîners hebdomadaire généré par WEEKLY_PLANNER. '
    'week_start doit toujours être un lundi (contrainte DB ISODOW + contrainte applicative). '
    'validated_at : timestamp de validation, déclenche la génération PDF eager via Celery. '
    'Seuls les plans status=validated déclenchent la génération PDF.';

CREATE TABLE planned_meals (
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
CREATE TABLE shopping_lists (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id      UUID NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
    -- Structure : [{"ingredient_id": "...", "name": "carotte", "quantity": 500, "unit": "g", "aisle": "légumes"}, ...]
    -- Groupé par rayon (aisle) pour faciliter le parcours en magasin.
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

CREATE TABLE fridge_items (
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

CREATE TABLE weekly_books (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id         UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    plan_id              UUID NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
    -- Clé Cloudflare R2 : "books/{household_id}/{year-week}.pdf"
    pdf_r2_key           TEXT NOT NULL,
    generated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- NULL = notification non encore envoyée (Celery beat vérifie ce champ)
    notification_sent_at TIMESTAMPTZ,
    UNIQUE (plan_id)
);

COMMENT ON TABLE weekly_books IS
    'Référence au PDF généré par BOOK_GENERATOR chaque dimanche. '
    'pdf_r2_key pointe vers Cloudflare R2. notification_sent_at = NULL déclenche '
    'l''envoi push/email par RETENTION_LOOP.';

-- -----------------------------------------------------------------------------
-- DOMAINE : Stripe subscriptions (stub Phase 3 — tables créées maintenant
-- pour éviter une migration destructive plus tard, mais non peuplées en v0/v1)
-- -----------------------------------------------------------------------------

CREATE TABLE subscriptions (
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
