-- =============================================================================
-- 04-phase2-schema.sql
-- Enrichissements Phase 2 — MealPlanner SaaS
--
-- Ce fichier applique les DDL Phase 2 sur le schéma Phase 0 déjà en place (02-schema.sql).
-- Toutes les opérations sont idempotentes (ADD COLUMN IF NOT EXISTS, CREATE IF NOT EXISTS).
--
-- Périmètre :
--   MISSION 1 : colonnes Stripe sur subscriptions
--   MISSION 2 : colonnes enrichies sur fridge_items (notes, is_staple)
--   MISSION 3 : table engagement_events (RETENTION_LOOP)
--   MISSION 4 : fonction suggest_recipes_from_fridge (mode frigo)
--
-- Ordre d'exécution : après 02-schema.sql et 03-seed.sql.
-- En production Supabase, ces DDL doivent être copiés dans une migration Alembic dédiée.
-- =============================================================================


-- =============================================================================
-- MISSION 1 — Enrichissement de la table subscriptions pour Stripe complet
-- La table existait en stub Phase 0 avec : household_id, stripe_sub_id, plan, status, current_period_end.
-- On ajoute les colonnes nécessaires au webhook Stripe Phase 2.
-- =============================================================================

-- Identifiant client Stripe (créé lors du checkout, avant toute subscription)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;

-- Identifiant du prix Stripe actif (price_famille_monthly, price_coach_annual, etc.)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_price_id TEXT;

-- true = annulation programmée en fin de période (l'utilisateur a demandé l'annulation)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN NOT NULL DEFAULT false;

-- Timestamp exact de l'annulation effective (NULL si pas encore annulé)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS canceled_at TIMESTAMPTZ;

-- Fin de la période d'essai gratuit (NULL si pas de trial)
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS trial_end TIMESTAMPTZ;

COMMENT ON COLUMN subscriptions.stripe_customer_id IS
    'ID customer Stripe (cus_xxx). Copie locale pour éviter un lookup API sur chaque webhook.';
COMMENT ON COLUMN subscriptions.stripe_price_id IS
    'ID prix Stripe actif (price_xxx). Permet de tracker les changements de plan sans appel API.';
COMMENT ON COLUMN subscriptions.cancel_at_period_end IS
    'true = annulation programmée. Le foyer garde l''accès jusqu''à current_period_end.';
COMMENT ON COLUMN subscriptions.canceled_at IS
    'Timestamp Stripe de l''annulation effective. NULL tant que la subscription est active.';
COMMENT ON COLUMN subscriptions.trial_end IS
    'Fin du trial gratuit. NULL si pas de trial. Affiché dans le dashboard abonnement.';

-- households.stripe_customer_id est déjà présent dans 02-schema.sql (ligne 69).
-- Aucune modification nécessaire sur households.
-- La colonne existe : TEXT, nullable, non-indexée côté households.

-- Index pour les lookups webhook Stripe (très fréquents — un webhook par événement)
CREATE INDEX IF NOT EXISTS ix_subscriptions_stripe_customer
    ON subscriptions (stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

COMMENT ON INDEX ix_subscriptions_stripe_customer IS
    'Lookup webhook Stripe : retrouver la subscription depuis customer_id. Partiel : exclut les lignes NULL.';

CREATE INDEX IF NOT EXISTS ix_subscriptions_stripe_sub
    ON subscriptions (stripe_sub_id);

COMMENT ON INDEX ix_subscriptions_stripe_sub IS
    'Lookup webhook Stripe : retrouver la subscription depuis subscription_id.';

-- Index partiel unique : un seul abonnement actif ou en trial par foyer
-- Remplace la contrainte UNIQUE(household_id) trop large (empêchait d'archiver les anciens)
-- Note : si UNIQUE(household_id) est déjà en place, cet index coexiste (couverture différente).
CREATE UNIQUE INDEX IF NOT EXISTS ix_subscriptions_household_active
    ON subscriptions (household_id)
    WHERE status IN ('active', 'trialing');

COMMENT ON INDEX ix_subscriptions_household_active IS
    'Garantit qu''un foyer ne peut avoir qu''une seule subscription active ou en trial. '
    'Partiel : les subscriptions canceled/past_due ne sont pas concernées.';

-- Policy RLS complémentaire : lecture par supabase_user_id (tous les membres, pas uniquement owner)
-- La policy Phase 0 (subscriptions_select) limitait aux owners.
-- Phase 2 : tous les membres peuvent voir le statut de l''abonnement (lecture seule, données non-sensibles).
DROP POLICY IF EXISTS subscriptions_select_own ON subscriptions;
CREATE POLICY subscriptions_select_own ON subscriptions FOR SELECT TO authenticated
    USING (
        household_id IN (
            SELECT household_id FROM household_members
            WHERE supabase_user_id = auth.uid()
        )
    );

-- Remplacement de la policy Phase 0 pour aligner les droits de lecture
-- (subscriptions_select Phase 0 = owner uniquement → subscriptions_select_own Phase 2 = tous membres)
-- On retire la policy Phase 0 pour éviter le conflit de noms (PostgreSQL interdit deux policies SELECT de même nom)
DROP POLICY IF EXISTS subscriptions_select ON subscriptions;


-- =============================================================================
-- MISSION 2 — Enrichissement de fridge_items pour le mode frigo Phase 2
-- Colonnes existantes vérifiées : id, household_id, ingredient_id, quantity, unit, expiry_date, added_at.
-- =============================================================================

-- Note textuelle libre (ex : "à finir avant vendredi", "ouvert")
ALTER TABLE fridge_items ADD COLUMN IF NOT EXISTS notes TEXT;

-- true = produit permanent qui ne disparaît pas après usage (sel, huile, sucre...)
-- WEEKLY_PLANNER ignore ces ingrédients dans le calcul de la liste de courses
ALTER TABLE fridge_items ADD COLUMN IF NOT EXISTS is_staple BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN fridge_items.notes IS
    'Note libre saisie par l''utilisateur. Ex : "à finir avant vendredi", "flacon ouvert".';
COMMENT ON COLUMN fridge_items.is_staple IS
    'Produit permanent (sel, huile, farine...). WEEKLY_PLANNER exclut les staples '
    'de la liste de courses car toujours disponibles.';

-- Index pour les suggestions de recettes depuis le frigo (requête critique du mode frigo)
-- Composite household_id + ingredient_id : retrouver tous les ingrédients d''un foyer
CREATE INDEX IF NOT EXISTS ix_fridge_items_household_ingredient
    ON fridge_items (household_id, ingredient_id);

COMMENT ON INDEX ix_fridge_items_household_ingredient IS
    'Utilisé par suggest_recipes_from_fridge : JOIN entre fridge_items et recipe_ingredients. '
    'Remplace le scan complet de fridge_items par un accès ciblé par foyer.';

-- Index pour les alertes de péremption (RETENTION_LOOP : "ingrédients qui périment bientôt")
-- idx_fridge_items_expiry (Phase 0) indexe (household_id, expiry_date ASC) — même stratégie, nom différent
-- On crée ix_fridge_items_expiry comme alias idempotent (ne conflicte pas si l'ancien existe)
CREATE INDEX IF NOT EXISTS ix_fridge_items_expiry
    ON fridge_items (household_id, expiry_date)
    WHERE expiry_date IS NOT NULL;

COMMENT ON INDEX ix_fridge_items_expiry IS
    'Alertes péremption RETENTION_LOOP : foyers avec ingrédients expirant dans les 2 jours. '
    'Partiel : exclut les produits sans date de péremption (staples, conserves).';


-- =============================================================================
-- MISSION 3 — Table engagement_events pour le RETENTION_LOOP
-- Cette table centralise tous les signaux d'engagement :
--   - Actions produit (plan_generated, recipe_rated, list_shared, app_opened)
--   - Signaux de risque (at_risk, inactive, win_back_sent)
-- Écriture réservée au service_role (agent RETENTION_LOOP Celery).
-- Lecture autorisée aux membres pour la transparence (RGPD).
-- =============================================================================

CREATE TABLE IF NOT EXISTS engagement_events (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID        NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    -- Type d'événement — liste non-exhaustive, extensible sans migration (JSONB event_data)
    -- Valeurs attendues : 'plan_generated', 'recipe_rated', 'list_shared', 'app_opened',
    --                     'at_risk', 'inactive', 'win_back_sent', 'reactivated'
    event_type   TEXT        NOT NULL,
    -- Données contextuelles libres (recipe_id, plan_id, channel, score de risque...)
    event_data   JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE engagement_events IS
    'Journal d''événements d''engagement par foyer. Écrit par l''agent RETENTION_LOOP (Celery). '
    'Permet la détection des foyers à risque de churn et le suivi des campagnes de rétention. '
    'event_data JSONB extensible sans migration (ajout de champs sans ALTER TABLE).';

COMMENT ON COLUMN engagement_events.event_type IS
    'Catégorie de l''événement. Valeurs utilisées par RETENTION_LOOP : '
    'plan_generated | recipe_rated | list_shared | app_opened | at_risk | inactive | win_back_sent | reactivated.';

COMMENT ON COLUMN engagement_events.event_data IS
    'Contexte libre de l''événement. Ex : {"recipe_id": "...", "rating": 4} pour recipe_rated, '
    '{"channel": "email", "template": "win_back_v2"} pour win_back_sent.';

-- RLS : activation + FORCE (sécurité défensive conforme à la politique Phase 0)
ALTER TABLE engagement_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE engagement_events FORCE ROW LEVEL SECURITY;

-- Policy lecture : les membres peuvent lire leurs propres événements (transparence RGPD)
DROP POLICY IF EXISTS engagement_events_select_own ON engagement_events;
CREATE POLICY engagement_events_select_own ON engagement_events FOR SELECT TO authenticated
    USING (
        household_id IN (
            SELECT household_id FROM household_members
            WHERE supabase_user_id = auth.uid()
        )
    );

-- Index principal : lookup par foyer + type d'événement + date (requêtes RETENTION_LOOP)
-- Ex : "tous les foyers at_risk des 7 derniers jours"
CREATE INDEX IF NOT EXISTS ix_engagement_events_household_type
    ON engagement_events (household_id, event_type, created_at DESC);

COMMENT ON INDEX ix_engagement_events_household_type IS
    'Requêtes RETENTION_LOOP : "foyer X a-t-il un événement at_risk récent ?". '
    'DESC sur created_at : les derniers événements sont lus en premier (ORDER BY created_at DESC LIMIT 1).';

-- Index partiel pour le scan des événements récents (30 jours glissants)
-- RETENTION_LOOP tourne en Celery beat toutes les 4h et ne lit que les events récents
-- Note : la condition "now() - INTERVAL '30 days'" est évaluée à la création de l'index.
-- Pour un index réellement glissant, utiliser un index GiST ou un partition par mois (Phase 3).
-- En Phase 2, cet index sert de hint pour le planificateur sur les données récentes.
CREATE INDEX IF NOT EXISTS ix_engagement_events_recent
    ON engagement_events (created_at DESC);

COMMENT ON INDEX ix_engagement_events_recent IS
    'Scan des événements récents par le planificateur Celery. '
    'En Phase 3 : partitionner engagement_events par mois (partition pruning).';


-- =============================================================================
-- MISSION 4 — Fonction suggest_recipes_from_fridge
-- Retourne les recettes matchant le mieux le contenu du frigo d''un foyer.
-- Tri : recettes avec ingrédients proches péremption en premier, puis par nombre de matches.
-- Seuil de qualité : quality_score >= 0.6 (recettes validées par RECIPE_SCOUT).
-- Minimum 2 ingrédients matchés pour éviter les suggestions non pertinentes.
-- =============================================================================

CREATE OR REPLACE FUNCTION suggest_recipes_from_fridge(
    p_household_id UUID,
    p_limit        INT DEFAULT 5
)
RETURNS TABLE (
    recipe_id              UUID,
    title                  TEXT,
    matching_ingredients   INT,
    total_ingredients      INT,
    match_ratio            FLOAT,
    has_expiring_ingredient BOOLEAN
)
LANGUAGE sql
STABLE
-- SECURITY DEFINER : s''exécute avec les droits du propriétaire de la fonction (postgres/service_role).
-- Permet à un utilisateur authenticated d''appeler la fonction sans accès direct à recipe_ingredients
-- (table publique en lecture, mais on reste explicite pour la traçabilité).
SECURITY DEFINER
-- SET search_path TO '' : sécurité défensive contre le search_path hijacking.
-- Toutes les tables doivent être qualifiées par leur schéma.
SET search_path TO ''
AS $$
    WITH fridge AS (
        -- Contenu du frigo du foyer : ingrédients disponibles + dates de péremption
        SELECT
            fi.ingredient_id,
            fi.expiry_date
        FROM public.fridge_items fi
        WHERE fi.household_id = p_household_id
          AND fi.is_staple = false  -- Les produits permanents ne comptent pas comme "disponibles"
    ),
    recipe_matches AS (
        -- Pour chaque recette : compter les ingrédients présents dans le frigo
        SELECT
            ri.recipe_id,
            COUNT(CASE WHEN f.ingredient_id IS NOT NULL THEN 1 END)  AS matching,
            COUNT(*)                                                   AS total,
            -- true si au moins un ingrédient matché expire dans les 2 prochains jours
            BOOL_OR(
                f.expiry_date IS NOT NULL
                AND f.expiry_date <= CURRENT_DATE + INTERVAL '2 days'
            )                                                          AS has_expiring
        FROM public.recipe_ingredients ri
        LEFT JOIN fridge f ON f.ingredient_id = ri.ingredient_id
        GROUP BY ri.recipe_id
        -- Minimum 2 ingrédients matchés : seuil de pertinence anti-bruit
        HAVING COUNT(CASE WHEN f.ingredient_id IS NOT NULL THEN 1 END) >= 2
    )
    SELECT
        rm.recipe_id,
        r.title,
        rm.matching::INT                            AS matching_ingredients,
        rm.total::INT                               AS total_ingredients,
        (rm.matching::FLOAT / rm.total::FLOAT)      AS match_ratio,
        rm.has_expiring                             AS has_expiring_ingredient
    FROM recipe_matches rm
    JOIN public.recipes r ON r.id = rm.recipe_id
    -- Filtre qualité : seules les recettes validées par RECIPE_SCOUT
    WHERE r.quality_score >= 0.6
    -- Tri : priorité aux recettes avec ingrédients périssants, puis par matching, puis ratio
    ORDER BY rm.has_expiring DESC, rm.matching DESC, match_ratio DESC
    LIMIT p_limit;
$$;

COMMENT ON FUNCTION suggest_recipes_from_fridge(UUID, INT) IS
    'Retourne les p_limit recettes (défaut 5) dont les ingrédients matchent le mieux '
    'le contenu du frigo du foyer p_household_id. '
    'Priorité aux recettes utilisant des ingrédients proches de péremption (anti-gaspi). '
    'Seuil qualité : quality_score >= 0.6. Seuil pertinence : minimum 2 ingrédients matchés. '
    'Les produits staples (is_staple=true) sont exclus du match (toujours disponibles). '
    'Exemple d''appel : SELECT * FROM suggest_recipes_from_fridge(''<household_uuid>'', 10);';

-- Grant d'exécution pour les utilisateurs authentifiés (la fonction tourne en SECURITY DEFINER)
GRANT EXECUTE ON FUNCTION suggest_recipes_from_fridge(UUID, INT) TO authenticated;


-- =============================================================================
-- Message de fin — visible dans les logs Docker au premier démarrage
-- =============================================================================

DO $$ BEGIN
    RAISE NOTICE '04-phase2-schema.sql : Phase 2 appliqué. '
        'subscriptions (+5 colonnes, 3 index), '
        'fridge_items (+2 colonnes, 2 index), '
        'engagement_events (table + RLS + 2 index), '
        'suggest_recipes_from_fridge (fonction + grant).';
END $$;
