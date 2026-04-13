"""Schéma initial MealPlanner SaaS — Phase 0/1 complet (13 tables, RLS, triggers, indexes).

Revision ID: 0001
Revises:
Create Date: 2026-04-12 12:00:00.000000+00:00

Contexte : schéma de référence Phase 0/1 (review Phase 1 — 2026-04-12).
Corrections appliquées dans cette version :
    - BUG #1 (code-review C3 / debug-audit BUG #3) : difficulty BETWEEN 1 AND 3 → 1 AND 5.
      Convention : 1=très facile, 2=facile, 3=moyen, 4=difficile, 5=très difficile.
      Aligne la contrainte DB avec RECIPE_SCOUT agent.py (mapping very_hard→5)
      et l'API Pydantic (Field ge=1, le=5). Sans ce fix : IntegrityError silencieux
      sur toutes les recettes "difficile" et "très difficile" en pipeline nocturne.
    - BUG #2 (idempotence RLS) : ajout de DROP POLICY IF EXISTS avant chaque CREATE POLICY.
      PostgreSQL ne supporte pas CREATE POLICY IF NOT EXISTS — sans ce pattern,
      un re-run partiel de la migration lève DuplicateObject et laisse le schéma incohérent.

Décision d'architecture :
    Le SQL Phase 0 est inliné dans cette migration plutôt que lu depuis les fichiers
    phase-0/database/. Raison : portabilité — les fichiers phase-0 peuvent être déplacés,
    archivés ou supprimés sans casser le replay de migrations. Une migration Alembic doit
    être auto-suffisante et rejouer correctement même des années après sa création.

    Les fichiers SQL source sont conservés dans phase-0/database/ comme référence canonique
    et documentation, mais le contenu de cette migration en est une copie statique.

Ordre d'exécution :
    1. 00-setup-extensions.sql  — uuid-ossp, pgcrypto, vector, pg_trgm
    2. 01-schema-core.sql       — 13 tables
    3. 02-indexes.sql           — HNSW + btree + GIN + trgm
    4. 04-triggers-functions.sql — fonctions d'abord (RLS en dépend)
    5. 03-rls-policies.sql      — RLS policies (avec DROP POLICY IF EXISTS pour idempotence)

    07-seed-data.sql est exclu : géré par src/scripts/seed.py séparément.

Idempotence :
    - Extensions : CREATE EXTENSION IF NOT EXISTS (natif)
    - Tables : CREATE TABLE IF NOT EXISTS
    - Indexes : CREATE INDEX IF NOT EXISTS
    - Fonctions : CREATE OR REPLACE FUNCTION (idempotent nativement)
    - RLS policies : DROP POLICY IF EXISTS + CREATE POLICY (PG n'a pas IF NOT EXISTS pour POLICY)
    - Triggers : pas IF NOT EXISTS en PG — safe car CREATE OR REPLACE FUNCTION couvre les fonctions

downgrade() :
    DROP en ordre inverse strict pour respecter les dépendances FK :
    RLS → triggers/fonctions → tables → extensions
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# =============================================================================
# STEP 1 — Extensions PostgreSQL
# Contenu de 00-setup-extensions.sql
# =============================================================================
SQL_EXTENSIONS = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
"""

# =============================================================================
# STEP 2 — Schéma core (13 tables)
# Contenu de 01-schema-core.sql (avec les 3 fixes résiduels phase 0.x)
# =============================================================================
SQL_SCHEMA_CORE = """
CREATE TABLE IF NOT EXISTS households (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    plan                TEXT NOT NULL DEFAULT 'starter'
                            CHECK (plan IN ('starter', 'famille', 'coach')),
    stripe_customer_id  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE households IS
    'Unité de tenancy. Chaque foyer est isolé par RLS. Un foyer = un abonnement Stripe.';

CREATE TABLE IF NOT EXISTS household_members (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id     UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    supabase_user_id UUID,
    role             TEXT NOT NULL DEFAULT 'member'
                         CHECK (role IN ('owner', 'member')),
    display_name     TEXT NOT NULL,
    birth_date       DATE,
    is_child         BOOLEAN NOT NULL DEFAULT false,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (supabase_user_id)
);

COMMENT ON TABLE household_members IS
    'Membres du foyer. supabase_user_id fait le pont entre Supabase Auth et le schéma métier.';

CREATE TABLE IF NOT EXISTS member_preferences (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id         UUID NOT NULL REFERENCES household_members(id) ON DELETE CASCADE,
    diet_tags         JSONB NOT NULL DEFAULT '[]',
    allergies         JSONB NOT NULL DEFAULT '[]',
    dislikes          JSONB NOT NULL DEFAULT '[]',
    cooking_time_max  INT CHECK (cooking_time_max > 0),
    budget_pref       TEXT CHECK (budget_pref IN ('économique', 'moyen', 'premium')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (member_id)
);

COMMENT ON TABLE member_preferences IS
    'Préférences alimentaires par membre. diet_tags et allergies sont lus par WEEKLY_PLANNER '
    'pour filtrer les recettes incompatibles avant toute recommandation.';

CREATE TABLE IF NOT EXISTS recipes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source          TEXT NOT NULL,
    source_url      TEXT,
    title           TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    description     TEXT,
    instructions    JSONB NOT NULL DEFAULT '[]',
    servings        INT NOT NULL CHECK (servings > 0),
    prep_time_min   INT CHECK (prep_time_min >= 0),
    cook_time_min   INT CHECK (cook_time_min >= 0),
    total_time_min  INT GENERATED ALWAYS AS (COALESCE(prep_time_min, 0) + COALESCE(cook_time_min, 0)) STORED,
    -- Échelle de difficulté : 1=très facile, 2=facile, 3=moyen, 4=difficile, 5=très difficile.
    -- Convention alignée avec le mapping RECIPE_SCOUT (agent.py) et l'API Pydantic (Field ge=1, le=5).
    difficulty      INT CHECK (difficulty BETWEEN 1 AND 5),
    cuisine_type    TEXT,
    photo_url       TEXT,
    nutrition       JSONB NOT NULL DEFAULT '{}',
    tags            TEXT[] NOT NULL DEFAULT '{}',
    quality_score   NUMERIC(3,2) NOT NULL DEFAULT 0.0
                        CHECK (quality_score BETWEEN 0.0 AND 1.0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE recipes IS
    'Catalogue global de recettes. Non isolé par tenant (données publiques). '
    'Peuplé exclusivement par RECIPE_SCOUT via service role. '
    'quality_score < 0.6 interdit par trigger (voir 04-triggers-functions.sql).';

CREATE TABLE IF NOT EXISTS recipe_embeddings (
    recipe_id       UUID PRIMARY KEY REFERENCES recipes(id) ON DELETE CASCADE,
    embedding       vector(384) NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
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

CREATE TABLE IF NOT EXISTS ingredients (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name TEXT NOT NULL UNIQUE,
    category       TEXT NOT NULL,
    unit_default   TEXT NOT NULL DEFAULT 'g',
    off_id         TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE ingredients IS
    'Référentiel canonique des ingrédients. Normalisé pour le mapping Open Food Facts (Phase 4). '
    'off_id null = ingrédient non encore mappé à un produit drive.';

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id     UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
    quantity      NUMERIC(10,3) NOT NULL CHECK (quantity > 0),
    unit          TEXT NOT NULL,
    notes         TEXT,
    position      INT NOT NULL DEFAULT 0,
    PRIMARY KEY (recipe_id, ingredient_id)
);

COMMENT ON TABLE recipe_ingredients IS
    'Association recette <=> ingrédient avec quantité. '
    'position permet d afficher les ingrédients dans l ordre éditorial de la source.';

CREATE TABLE IF NOT EXISTS member_taste_vectors (
    member_id  UUID PRIMARY KEY REFERENCES household_members(id) ON DELETE CASCADE,
    vector     vector(384) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE member_taste_vectors IS
    'Vecteur de goût synthétique mis à jour par TASTE_PROFILE après chaque feedback. '
    'La recherche cosine member_taste_vectors.vector <=> recipe_embeddings.embedding '
    'est le coeur du moteur de recommandation.';

CREATE TABLE IF NOT EXISTS recipe_feedbacks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id  UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    member_id     UUID NOT NULL REFERENCES household_members(id) ON DELETE CASCADE,
    recipe_id     UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    rating        INT CHECK (rating BETWEEN 1 AND 5),
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('cooked', 'skipped', 'favorited')),
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE recipe_feedbacks IS
    'Journal de tous les feedbacks utilisateur. Chaque entrée déclenche une mise à jour '
    'asynchrone de member_taste_vectors via TASTE_PROFILE (tâche Celery). '
    'household_id dénormalisé pour simplifier la politique RLS.';

CREATE TABLE IF NOT EXISTS weekly_plans (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    week_start   DATE NOT NULL,
    status       TEXT NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft', 'validated', 'archived')),
    validated_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (household_id, week_start),
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
    day_of_week      INT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    slot             TEXT NOT NULL DEFAULT 'dinner' CHECK (slot IN ('dinner', 'lunch')),
    recipe_id        UUID NOT NULL REFERENCES recipes(id) ON DELETE RESTRICT,
    servings_adjusted INT NOT NULL CHECK (servings_adjusted > 0),
    UNIQUE (plan_id, day_of_week, slot)
);

COMMENT ON TABLE planned_meals IS
    'Repas individuels composant un plan hebdomadaire. '
    'servings_adjusted permet de scaler les quantités sans modifier la recette source.';

CREATE TABLE IF NOT EXISTS shopping_lists (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id      UUID NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
    items        JSONB NOT NULL DEFAULT '[]',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (plan_id)
);

COMMENT ON TABLE shopping_lists IS
    'Liste de courses consolidée générée par CART_BUILDER à partir d un plan validé. '
    'items est un JSONB pour flexibilité (structure évoluera en Phase 4 avec SKU drive). '
    'Partagée en temps réel via Supabase Realtime.';

CREATE TABLE IF NOT EXISTS fridge_items (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id  UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
    quantity      NUMERIC(10,3) NOT NULL CHECK (quantity > 0),
    unit          TEXT NOT NULL,
    expiry_date   DATE,
    added_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE fridge_items IS
    'Stock frigo actuel du foyer. WEEKLY_PLANNER lit cette table pour prioriser '
    'les recettes utilisant les ingrédients proches de leur date de péremption (anti-gaspi).';

CREATE TABLE IF NOT EXISTS weekly_books (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id         UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    plan_id              UUID NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
    pdf_r2_key           TEXT NOT NULL,
    generated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    notification_sent_at TIMESTAMPTZ,
    UNIQUE (plan_id)
);

COMMENT ON TABLE weekly_books IS
    'Référence au PDF généré par BOOK_GENERATOR chaque dimanche. '
    'pdf_r2_key pointe vers Cloudflare R2. notification_sent_at = NULL déclenche '
    'l envoi push/email par RETENTION_LOOP.';

CREATE TABLE IF NOT EXISTS subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id        UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    stripe_sub_id       TEXT NOT NULL UNIQUE,
    plan                TEXT NOT NULL CHECK (plan IN ('starter', 'famille', 'coach')),
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
"""

# =============================================================================
# STEP 3 — Indexes
# Contenu de 02-indexes.sql
# =============================================================================
SQL_INDEXES = """
-- HNSW embeddings recettes
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_hnsw
    ON recipe_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- GIN tags dénormalisés
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_tags_gin
    ON recipe_embeddings USING gin (tags);

-- BTREE partiel total_time_min
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_total_time
    ON recipe_embeddings (total_time_min)
    WHERE total_time_min IS NOT NULL;

-- Composite couvrant (total_time_min, cuisine_type) INCLUDE recipe_id
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_filter_composite
    ON recipe_embeddings (total_time_min, cuisine_type)
    INCLUDE (recipe_id)
    WHERE total_time_min IS NOT NULL;

-- HNSW taste vectors membres
CREATE INDEX IF NOT EXISTS idx_member_taste_vectors_hnsw
    ON member_taste_vectors
    USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 32);

-- BTREE clés de tenancy
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

CREATE INDEX IF NOT EXISTS idx_weekly_plans_household_week
    ON weekly_plans (household_id, week_start DESC);

CREATE INDEX IF NOT EXISTS idx_planned_meals_plan_id
    ON planned_meals (plan_id);

CREATE INDEX IF NOT EXISTS idx_fridge_items_household_id
    ON fridge_items (household_id);

CREATE INDEX IF NOT EXISTS idx_fridge_items_expiry
    ON fridge_items (household_id, expiry_date ASC NULLS LAST)
    WHERE expiry_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_weekly_books_household_id
    ON weekly_books (household_id);

-- GIN JSONB et tableaux
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

-- GIN trigrammes full-text FR
CREATE INDEX IF NOT EXISTS idx_recipes_title_trgm
    ON recipes USING gin (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_ingredients_canonical_name_trgm
    ON ingredients USING gin (canonical_name gin_trgm_ops);

-- BTREE filtres fréquents recipes
CREATE INDEX IF NOT EXISTS idx_recipes_cuisine_difficulty
    ON recipes (cuisine_type, difficulty);

CREATE INDEX IF NOT EXISTS idx_recipes_total_time
    ON recipes (total_time_min ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_recipes_quality_score
    ON recipes (quality_score DESC);

-- Index partiels
CREATE INDEX IF NOT EXISTS idx_weekly_plans_draft
    ON weekly_plans (household_id, week_start)
    WHERE status = 'draft';

CREATE INDEX IF NOT EXISTS idx_weekly_books_unsent_notification
    ON weekly_books (generated_at)
    WHERE notification_sent_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_recipe_feedbacks_favorited
    ON recipe_feedbacks (household_id, recipe_id)
    WHERE feedback_type = 'favorited';

CREATE INDEX IF NOT EXISTS idx_household_members_with_auth
    ON household_members (supabase_user_id, household_id)
    WHERE supabase_user_id IS NOT NULL;
"""

# =============================================================================
# STEP 4 — Triggers et fonctions
# Contenu de 04-triggers-functions.sql (version corrigée avec SECURITY DEFINER)
# Ordre : fonctions d'abord, car les RLS policies en dépendent.
# =============================================================================
SQL_TRIGGERS_FUNCTIONS = r"""
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
    'SECURITY DEFINER + search_path vide (règle défensive uniforme, fix résiduel 2026-04-12).';

CREATE TRIGGER set_updated_at_households
    BEFORE UPDATE ON public.households
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_household_members
    BEFORE UPDATE ON public.household_members
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_member_preferences
    BEFORE UPDATE ON public.member_preferences
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_recipes
    BEFORE UPDATE ON public.recipes
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_recipe_embeddings
    BEFORE UPDATE ON public.recipe_embeddings
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_weekly_plans
    BEFORE UPDATE ON public.weekly_plans
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_subscriptions
    BEFORE UPDATE ON public.subscriptions
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

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
            'Recette % (source: %) : temps total = 0 minute. '
            'Vérifier les données source.',
            NEW.title,
            NEW.source;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION validate_recipe_quality() IS
    'Trigger BEFORE INSERT/UPDATE sur recipes. '
    'Rejette les recettes avec quality_score < 0.6 (règle ROADMAP section 10). '
    'SECURITY DEFINER + search_path vide (fix résiduel 2026-04-12). '
    'Émet un WARNING (sans rejet) pour les recettes à temps zéro.';

CREATE TRIGGER validate_recipe_quality_before_insert
    BEFORE INSERT OR UPDATE ON public.recipes
    FOR EACH ROW EXECUTE FUNCTION validate_recipe_quality();

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

CREATE TRIGGER sync_recipe_embeddings_metadata
    AFTER UPDATE ON public.recipes
    FOR EACH ROW EXECUTE FUNCTION recipe_embeddings_sync_metadata();
"""

# =============================================================================
# STEP 5 — RLS Policies
# Contenu de 03-rls-policies.sql
# =============================================================================
SQL_RLS_POLICIES = """
-- Activation RLS
ALTER TABLE public.households               ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.household_members        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.member_preferences       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.member_taste_vectors     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recipe_feedbacks         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_plans             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.planned_meals            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shopping_lists           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fridge_items             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_books             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions            ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.households               FORCE ROW LEVEL SECURITY;
ALTER TABLE public.household_members        FORCE ROW LEVEL SECURITY;
ALTER TABLE public.member_preferences       FORCE ROW LEVEL SECURITY;
ALTER TABLE public.member_taste_vectors     FORCE ROW LEVEL SECURITY;
ALTER TABLE public.recipe_feedbacks         FORCE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_plans             FORCE ROW LEVEL SECURITY;
ALTER TABLE public.planned_meals            FORCE ROW LEVEL SECURITY;
ALTER TABLE public.shopping_lists           FORCE ROW LEVEL SECURITY;
ALTER TABLE public.fridge_items             FORCE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_books             FORCE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions            FORCE ROW LEVEL SECURITY;

-- Idempotence RLS : PostgreSQL ne supporte pas CREATE POLICY IF NOT EXISTS.
-- Stratégie : DROP POLICY IF EXISTS avant chaque CREATE POLICY.
-- Cela rend la section RLS safe en cas de re-run partiel de la migration.

-- Policies households
DROP POLICY IF EXISTS households_select ON public.households;
CREATE POLICY households_select
    ON public.households FOR SELECT TO authenticated
    USING (id IN (SELECT household_id FROM public.household_members WHERE supabase_user_id = auth.uid()));

DROP POLICY IF EXISTS households_update ON public.households;
CREATE POLICY households_update
    ON public.households FOR UPDATE TO authenticated
    USING (id IN (SELECT household_id FROM public.household_members WHERE supabase_user_id = auth.uid() AND role = 'owner'))
    WITH CHECK (id IN (SELECT household_id FROM public.household_members WHERE supabase_user_id = auth.uid() AND role = 'owner'));

DROP POLICY IF EXISTS households_insert ON public.households;
CREATE POLICY households_insert
    ON public.households FOR INSERT TO authenticated
    WITH CHECK (true);

-- Policies household_members
DROP POLICY IF EXISTS household_members_select ON public.household_members;
CREATE POLICY household_members_select
    ON public.household_members FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());

DROP POLICY IF EXISTS household_members_update ON public.household_members;
CREATE POLICY household_members_update
    ON public.household_members FOR UPDATE TO authenticated
    USING (
        household_id = get_current_household_id()
        AND (
            supabase_user_id = (SELECT auth.uid())
            OR EXISTS (
                SELECT 1 FROM public.household_members hm
                WHERE hm.supabase_user_id = (SELECT auth.uid())
                  AND hm.household_id = household_members.household_id
                  AND hm.role = 'owner'
            )
        )
    )
    WITH CHECK (household_id = get_current_household_id());

-- Policies member_preferences
DROP POLICY IF EXISTS member_preferences_select ON public.member_preferences;
CREATE POLICY member_preferences_select
    ON public.member_preferences FOR SELECT TO authenticated
    USING (member_id IN (SELECT id FROM public.household_members WHERE household_id = get_current_household_id()));

DROP POLICY IF EXISTS member_preferences_insert ON public.member_preferences;
CREATE POLICY member_preferences_insert
    ON public.member_preferences FOR INSERT TO authenticated
    WITH CHECK (member_id IN (SELECT id FROM public.household_members WHERE household_id = get_current_household_id()));

DROP POLICY IF EXISTS member_preferences_update ON public.member_preferences;
CREATE POLICY member_preferences_update
    ON public.member_preferences FOR UPDATE TO authenticated
    USING (member_id IN (SELECT id FROM public.household_members WHERE household_id = get_current_household_id()))
    WITH CHECK (member_id IN (SELECT id FROM public.household_members WHERE household_id = get_current_household_id()));

-- Policies member_taste_vectors
DROP POLICY IF EXISTS member_taste_vectors_select ON public.member_taste_vectors;
CREATE POLICY member_taste_vectors_select
    ON public.member_taste_vectors FOR SELECT TO authenticated
    USING (member_id IN (SELECT id FROM public.household_members WHERE household_id = get_current_household_id()));

-- Policies recipe_feedbacks
DROP POLICY IF EXISTS recipe_feedbacks_select ON public.recipe_feedbacks;
CREATE POLICY recipe_feedbacks_select
    ON public.recipe_feedbacks FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());

DROP POLICY IF EXISTS recipe_feedbacks_insert ON public.recipe_feedbacks;
CREATE POLICY recipe_feedbacks_insert
    ON public.recipe_feedbacks FOR INSERT TO authenticated
    WITH CHECK (
        household_id = get_current_household_id()
        AND member_id IN (SELECT id FROM public.household_members WHERE supabase_user_id = auth.uid())
    );

-- Policies weekly_plans
DROP POLICY IF EXISTS weekly_plans_select ON public.weekly_plans;
CREATE POLICY weekly_plans_select
    ON public.weekly_plans FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());

DROP POLICY IF EXISTS weekly_plans_insert ON public.weekly_plans;
CREATE POLICY weekly_plans_insert
    ON public.weekly_plans FOR INSERT TO authenticated
    WITH CHECK (household_id = get_current_household_id());

DROP POLICY IF EXISTS weekly_plans_update ON public.weekly_plans;
CREATE POLICY weekly_plans_update
    ON public.weekly_plans FOR UPDATE TO authenticated
    USING (household_id = get_current_household_id())
    WITH CHECK (household_id = get_current_household_id());

DROP POLICY IF EXISTS weekly_plans_delete ON public.weekly_plans;
CREATE POLICY weekly_plans_delete
    ON public.weekly_plans FOR DELETE TO authenticated
    USING (household_id = get_current_household_id() AND status = 'draft');

-- Policies planned_meals
DROP POLICY IF EXISTS planned_meals_select ON public.planned_meals;
CREATE POLICY planned_meals_select
    ON public.planned_meals FOR SELECT TO authenticated
    USING (plan_id IN (SELECT id FROM public.weekly_plans WHERE household_id = get_current_household_id()));

DROP POLICY IF EXISTS planned_meals_insert ON public.planned_meals;
CREATE POLICY planned_meals_insert
    ON public.planned_meals FOR INSERT TO authenticated
    WITH CHECK (plan_id IN (SELECT id FROM public.weekly_plans WHERE household_id = get_current_household_id()));

DROP POLICY IF EXISTS planned_meals_update ON public.planned_meals;
CREATE POLICY planned_meals_update
    ON public.planned_meals FOR UPDATE TO authenticated
    USING (plan_id IN (SELECT id FROM public.weekly_plans WHERE household_id = get_current_household_id() AND status = 'draft'))
    WITH CHECK (plan_id IN (SELECT id FROM public.weekly_plans WHERE household_id = get_current_household_id() AND status = 'draft'));

DROP POLICY IF EXISTS planned_meals_delete ON public.planned_meals;
CREATE POLICY planned_meals_delete
    ON public.planned_meals FOR DELETE TO authenticated
    USING (plan_id IN (SELECT id FROM public.weekly_plans WHERE household_id = get_current_household_id() AND status = 'draft'));

-- Policies shopping_lists
DROP POLICY IF EXISTS shopping_lists_select ON public.shopping_lists;
CREATE POLICY shopping_lists_select
    ON public.shopping_lists FOR SELECT TO authenticated
    USING (plan_id IN (SELECT id FROM public.weekly_plans WHERE household_id = get_current_household_id()));

DROP POLICY IF EXISTS shopping_lists_update ON public.shopping_lists;
CREATE POLICY shopping_lists_update
    ON public.shopping_lists FOR UPDATE TO authenticated
    USING (plan_id IN (SELECT id FROM public.weekly_plans WHERE household_id = get_current_household_id()))
    WITH CHECK (plan_id IN (SELECT id FROM public.weekly_plans WHERE household_id = get_current_household_id()));

-- Policies fridge_items
DROP POLICY IF EXISTS fridge_items_select ON public.fridge_items;
CREATE POLICY fridge_items_select
    ON public.fridge_items FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());

DROP POLICY IF EXISTS fridge_items_insert ON public.fridge_items;
CREATE POLICY fridge_items_insert
    ON public.fridge_items FOR INSERT TO authenticated
    WITH CHECK (household_id = get_current_household_id());

DROP POLICY IF EXISTS fridge_items_update ON public.fridge_items;
CREATE POLICY fridge_items_update
    ON public.fridge_items FOR UPDATE TO authenticated
    USING (household_id = get_current_household_id())
    WITH CHECK (household_id = get_current_household_id());

DROP POLICY IF EXISTS fridge_items_delete ON public.fridge_items;
CREATE POLICY fridge_items_delete
    ON public.fridge_items FOR DELETE TO authenticated
    USING (household_id = get_current_household_id());

-- Policies weekly_books
DROP POLICY IF EXISTS weekly_books_select ON public.weekly_books;
CREATE POLICY weekly_books_select
    ON public.weekly_books FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());

-- Policies subscriptions
DROP POLICY IF EXISTS subscriptions_select ON public.subscriptions;
CREATE POLICY subscriptions_select
    ON public.subscriptions FOR SELECT TO authenticated
    USING (household_id IN (SELECT household_id FROM public.household_members WHERE supabase_user_id = auth.uid() AND role = 'owner'));

-- GRANTs tables publiques
GRANT SELECT ON public.recipes              TO anon, authenticated;
GRANT SELECT ON public.recipe_embeddings    TO anon, authenticated;
GRANT SELECT ON public.ingredients          TO anon, authenticated;
GRANT SELECT ON public.recipe_ingredients   TO anon, authenticated;
"""

# =============================================================================
# DOWNGRADE SQL — DROP en ordre inverse strict
# =============================================================================
SQL_DOWNGRADE_RLS = """
-- Suppression des policies RLS (ordre : policies avant DISABLE)
DROP POLICY IF EXISTS subscriptions_select          ON public.subscriptions;
DROP POLICY IF EXISTS weekly_books_select           ON public.weekly_books;
DROP POLICY IF EXISTS fridge_items_delete           ON public.fridge_items;
DROP POLICY IF EXISTS fridge_items_update           ON public.fridge_items;
DROP POLICY IF EXISTS fridge_items_insert           ON public.fridge_items;
DROP POLICY IF EXISTS fridge_items_select           ON public.fridge_items;
DROP POLICY IF EXISTS shopping_lists_update         ON public.shopping_lists;
DROP POLICY IF EXISTS shopping_lists_select         ON public.shopping_lists;
DROP POLICY IF EXISTS planned_meals_delete          ON public.planned_meals;
DROP POLICY IF EXISTS planned_meals_update          ON public.planned_meals;
DROP POLICY IF EXISTS planned_meals_insert          ON public.planned_meals;
DROP POLICY IF EXISTS planned_meals_select          ON public.planned_meals;
DROP POLICY IF EXISTS weekly_plans_delete           ON public.weekly_plans;
DROP POLICY IF EXISTS weekly_plans_update           ON public.weekly_plans;
DROP POLICY IF EXISTS weekly_plans_insert           ON public.weekly_plans;
DROP POLICY IF EXISTS weekly_plans_select           ON public.weekly_plans;
DROP POLICY IF EXISTS recipe_feedbacks_insert       ON public.recipe_feedbacks;
DROP POLICY IF EXISTS recipe_feedbacks_select       ON public.recipe_feedbacks;
DROP POLICY IF EXISTS member_taste_vectors_select   ON public.member_taste_vectors;
DROP POLICY IF EXISTS member_preferences_update     ON public.member_preferences;
DROP POLICY IF EXISTS member_preferences_insert     ON public.member_preferences;
DROP POLICY IF EXISTS member_preferences_select     ON public.member_preferences;
DROP POLICY IF EXISTS household_members_update      ON public.household_members;
DROP POLICY IF EXISTS household_members_select      ON public.household_members;
DROP POLICY IF EXISTS households_insert             ON public.households;
DROP POLICY IF EXISTS households_update             ON public.households;
DROP POLICY IF EXISTS households_select             ON public.households;

-- Révocation GRANTS
REVOKE SELECT ON public.recipe_ingredients  FROM anon, authenticated;
REVOKE SELECT ON public.ingredients         FROM anon, authenticated;
REVOKE SELECT ON public.recipe_embeddings   FROM anon, authenticated;
REVOKE SELECT ON public.recipes             FROM anon, authenticated;

-- Désactivation RLS
ALTER TABLE public.subscriptions            DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_books             DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.fridge_items             DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.shopping_lists           DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.planned_meals            DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_plans             DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.recipe_feedbacks         DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.member_taste_vectors     DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.member_preferences       DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.household_members        DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.households               DISABLE ROW LEVEL SECURITY;
"""

SQL_DOWNGRADE_TRIGGERS = """
DROP TRIGGER IF EXISTS sync_recipe_embeddings_metadata     ON public.recipes;
DROP TRIGGER IF EXISTS validate_recipe_quality_before_insert ON public.recipes;
DROP TRIGGER IF EXISTS set_updated_at_subscriptions        ON public.subscriptions;
DROP TRIGGER IF EXISTS set_updated_at_weekly_plans         ON public.weekly_plans;
DROP TRIGGER IF EXISTS set_updated_at_recipe_embeddings    ON public.recipe_embeddings;
DROP TRIGGER IF EXISTS set_updated_at_recipes              ON public.recipes;
DROP TRIGGER IF EXISTS set_updated_at_member_preferences   ON public.member_preferences;
DROP TRIGGER IF EXISTS set_updated_at_household_members    ON public.household_members;
DROP TRIGGER IF EXISTS set_updated_at_households           ON public.households;

DROP FUNCTION IF EXISTS recipe_embeddings_sync_metadata();
DROP FUNCTION IF EXISTS create_household_with_owner(TEXT, UUID, TEXT);
DROP FUNCTION IF EXISTS cleanup_old_embeddings();
DROP FUNCTION IF EXISTS get_household_constraints(UUID);
DROP FUNCTION IF EXISTS validate_recipe_quality();
DROP FUNCTION IF EXISTS trigger_set_updated_at();
DROP FUNCTION IF EXISTS get_current_household_id();
"""

SQL_DOWNGRADE_TABLES = """
-- DROP dans l'ordre inverse des dépendances FK
DROP TABLE IF EXISTS public.subscriptions         CASCADE;
DROP TABLE IF EXISTS public.weekly_books          CASCADE;
DROP TABLE IF EXISTS public.fridge_items          CASCADE;
DROP TABLE IF EXISTS public.shopping_lists        CASCADE;
DROP TABLE IF EXISTS public.planned_meals         CASCADE;
DROP TABLE IF EXISTS public.weekly_plans          CASCADE;
DROP TABLE IF EXISTS public.recipe_feedbacks      CASCADE;
DROP TABLE IF EXISTS public.member_taste_vectors  CASCADE;
DROP TABLE IF EXISTS public.member_preferences    CASCADE;
DROP TABLE IF EXISTS public.recipe_ingredients    CASCADE;
DROP TABLE IF EXISTS public.recipe_embeddings     CASCADE;
DROP TABLE IF EXISTS public.recipes               CASCADE;
DROP TABLE IF EXISTS public.ingredients           CASCADE;
DROP TABLE IF EXISTS public.household_members     CASCADE;
DROP TABLE IF EXISTS public.households            CASCADE;
"""

SQL_DOWNGRADE_EXTENSIONS = """
-- Extensions : DROP uniquement si aucune autre base ne les utilise.
-- En production Supabase, NE PAS supprimer vector et uuid-ossp (utilisées par d'autres services).
-- Ce downgrade est prévu pour les environnements de dev/test uniquement.
DROP EXTENSION IF EXISTS "pg_trgm"   CASCADE;
DROP EXTENSION IF EXISTS "vector"    CASCADE;
DROP EXTENSION IF EXISTS "pgcrypto"  CASCADE;
DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;
"""


def upgrade() -> None:
    """Crée le schéma complet Phase 0 MealPlanner SaaS.

    Exécution dans l'ordre :
    1. Extensions
    2. Tables (avec contraintes inline)
    3. Indexes
    4. Fonctions et triggers
    5. RLS policies et grants
    """
    op.execute(SQL_EXTENSIONS)
    op.execute(SQL_SCHEMA_CORE)
    op.execute(SQL_INDEXES)
    op.execute(SQL_TRIGGERS_FUNCTIONS)
    op.execute(SQL_RLS_POLICIES)


def downgrade() -> None:
    """Supprime le schéma complet Phase 0 en ordre inverse strict.

    ATTENTION : destructif et irréversible. À utiliser uniquement en dev/test.
    En production, préférer une migration de renommage/archivage.

    Ordre : RLS → triggers/fonctions → tables → extensions
    """
    op.execute(SQL_DOWNGRADE_RLS)
    op.execute(SQL_DOWNGRADE_TRIGGERS)
    op.execute(SQL_DOWNGRADE_TABLES)
    op.execute(SQL_DOWNGRADE_EXTENSIONS)
