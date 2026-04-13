-- =============================================================================
-- 03-rls-policies.sql
-- Row Level Security — MealPlanner SaaS
-- CRITIQUE : Ce fichier protège l'isolation stricte entre foyers (tenants).
--
-- Principe fondamental Supabase :
--   auth.uid() retourne le UUID de l'utilisateur connecté via Supabase Auth JWT.
--   Il correspond à household_members.supabase_user_id.
--
-- PIÈGE SUPABASE : auth.uid() retourne NULL pour les requêtes sans JWT valide
--   ET pour les requêtes faites via le service_role (qui bypass RLS).
--   Le service_role est utilisé par les agents IA (RECIPE_SCOUT, etc.) — c'est voulu.
--
-- Architecture de la vérification d'appartenance :
--   1. auth.uid() → supabase_user_id dans household_members
--   2. household_members.household_id → household_id de la ressource demandée
--   3. Si la chaîne est complète → accès autorisé
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Fonction helper : retourne le household_id de l'utilisateur connecté.
-- Appelée dans toutes les policies pour éviter la duplication de sous-requêtes.
-- SECURITY DEFINER permet à la fonction de lire household_members même si l'appelant
-- n'a pas accès direct à la table (la fonction tourne avec les droits de son propriétaire).
-- -----------------------------------------------------------------------------

-- La fonction get_current_household_id() est créée dans 04-triggers-functions.sql.
-- Ce fichier part du principe qu'elle existe déjà (ordre d'exécution : 04 avant 03
-- ou, mieux, exécuter 04 en premier si standalone).
-- En pratique, Alembic exécute les migrations dans l'ordre de date — planifie en conséquence.
--
-- OPT #2 (review 2026-04-12) : PATTERN Supabase auth.uid() dans les policies RLS.
-- Problème : auth.uid() appelé directement dans une sous-requête USING/WITH CHECK est
-- re-évalué par PostgreSQL pour CHAQUE ligne scannée (comportement non-STABLE).
-- Solution : encapsuler dans get_current_household_id() marquée STABLE + SECURITY DEFINER.
-- PostgreSQL peut alors mettre le résultat en cache pour la durée du statement.
-- Pour les tables à très haute fréquence (recipe_feedbacks, planned_meals à 1M+ rows),
-- remplacer la sous-requête par : (SELECT auth.uid()) — les parenthèses forcent l'évaluation
-- en sous-requête scalaire, ce qui permet l'inlining et le cache par le planner PG16.
-- Référence : https://supabase.com/docs/guides/database/postgres/row-level-security#call-functions-with-select

-- -----------------------------------------------------------------------------
-- ACTIVATION RLS sur toutes les tables tenant-scoped
-- Les tables non listées ici (recipes, ingredients, recipe_ingredients) sont
-- publiques en lecture → pas de RLS nécessaire, accès géré par les GRANTS.
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
-- Un utilisateur ne voit que SON foyer (celui dont il est membre).
-- -----------------------------------------------------------------------------

CREATE POLICY households_select
    ON households
    FOR SELECT
    TO authenticated
    USING (
        id IN (
            SELECT household_id
            FROM household_members
            WHERE supabase_user_id = auth.uid()
        )
    );

CREATE POLICY households_update
    ON households
    FOR UPDATE
    TO authenticated
    USING (
        -- Seul l'owner du foyer peut modifier les informations du foyer
        id IN (
            SELECT household_id
            FROM household_members
            WHERE supabase_user_id = auth.uid()
              AND role = 'owner'
        )
    )
    WITH CHECK (
        id IN (
            SELECT household_id
            FROM household_members
            WHERE supabase_user_id = auth.uid()
              AND role = 'owner'
        )
    );

-- INSERT sur households : autorisé à tout utilisateur authentifié (création de compte)
-- La création d'un household crée aussi le premier household_member (owner) côté API.
CREATE POLICY households_insert
    ON households
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Suppression d'un foyer réservée au service_role (opération irréversible, flux backend)
-- Pas de policy DELETE pour les utilisateurs → rejetée par défaut.

-- -----------------------------------------------------------------------------
-- POLICIES : household_members
-- Un membre voit tous les membres de SON foyer.
-- Seul l'owner peut ajouter/supprimer des membres.
-- -----------------------------------------------------------------------------

CREATE POLICY household_members_select
    ON household_members
    FOR SELECT
    TO authenticated
    USING (
        household_id = get_current_household_id()
    );

-- BUG #2 (review 2026-04-12) : Récursion RLS sur household_members_insert.
-- Problème : la sous-requête ci-dessous interrogeait household_members elle-même
-- pendant l'évaluation RLS FORCE. Lors de la création du PREMIER owner (onboarding),
-- la table est vide → la sous-requête retourne 0 lignes → WITH CHECK échoue → impossible
-- de créer le foyer initial. C'est un deadlock d'onboarding.
--
-- Solution retenue : la policy INSERT est désactivée pour le rôle authenticated.
-- La création du premier owner (household + household_member owner) doit OBLIGATOIREMENT
-- passer par le service_role côté API FastAPI (bypass RLS).
-- La fonction create_household_with_owner() dans 04-triggers-functions.sql encapsule
-- cette logique en SECURITY DEFINER pour un appel atomique depuis le client.
--
-- ATTENTION : ne pas ré-activer de policy INSERT authenticated ici sans résoudre
-- le problème de bootstrap. Toute policy INSERT auto-référentielle sur une table
-- avec FORCE RLS crée ce même deadlock pour les nouveaux utilisateurs.
--
-- Flux d'onboarding documenté :
--   1. Client appelle POST /api/households (endpoint FastAPI)
--   2. L'API utilise supabase_client avec service_role key
--   3. L'API appelle SELECT create_household_with_owner($name, $supabase_uid, $display_name)
--   4. La fonction SECURITY DEFINER insère household + member en mode service_role atomiquement
-- Pas de policy DELETE pour les utilisateurs → rejetée par défaut (opération irréversible).

CREATE POLICY household_members_update
    ON household_members
    FOR UPDATE
    TO authenticated
    USING (
        household_id = get_current_household_id()
        AND (
            -- Un membre peut modifier son propre profil
            supabase_user_id = (SELECT auth.uid())
            -- L'owner peut modifier n'importe quel membre de son foyer
            OR EXISTS (
                SELECT 1 FROM household_members hm
                WHERE hm.supabase_user_id = (SELECT auth.uid())
                  AND hm.household_id = household_members.household_id
                  AND hm.role = 'owner'
            )
        )
    )
    -- FIX #1 (review 2026-04-12) : WITH CHECK manquant → faille cross-tenant.
    -- Sans WITH CHECK, un UPDATE pouvait changer household_id vers un autre foyer.
    -- USING vérifie la ligne AVANT modification, WITH CHECK vérifie la ligne APRÈS.
    -- Les deux clauses sont identiques : on s'assure que la valeur écrite reste
    -- dans le foyer courant (on ne peut pas s'approprier des membres d'un autre foyer).
    WITH CHECK (
        household_id = get_current_household_id()
    );

-- -----------------------------------------------------------------------------
-- POLICIES : member_preferences
-- Lecture : tous les membres du foyer (WEEKLY_PLANNER agrège les contraintes)
-- Écriture : uniquement le membre lui-même ou l'owner
-- -----------------------------------------------------------------------------

CREATE POLICY member_preferences_select
    ON member_preferences
    FOR SELECT
    TO authenticated
    USING (
        member_id IN (
            SELECT id FROM household_members
            WHERE household_id = get_current_household_id()
        )
    );

CREATE POLICY member_preferences_insert
    ON member_preferences
    FOR INSERT
    TO authenticated
    WITH CHECK (
        member_id IN (
            SELECT id FROM household_members
            WHERE household_id = get_current_household_id()
        )
    );

CREATE POLICY member_preferences_update
    ON member_preferences
    FOR UPDATE
    TO authenticated
    USING (
        member_id IN (
            SELECT id FROM household_members
            WHERE household_id = get_current_household_id()
        )
    )
    -- FIX #1 (review 2026-04-12) : WITH CHECK manquant → faille cross-tenant.
    -- Sans WITH CHECK, un UPDATE pouvait changer member_id pour pointer vers
    -- un membre d'un autre foyer (le membre source est bien dans le foyer courant,
    -- mais la ligne résultante appartient à un autre tenant → pollution inter-tenant).
    -- WITH CHECK identique à USING : garantit que la ligne écrite reste dans le foyer.
    WITH CHECK (
        member_id IN (
            SELECT id FROM household_members
            WHERE household_id = get_current_household_id()
        )
    );

-- -----------------------------------------------------------------------------
-- POLICIES : member_taste_vectors
-- Lecture réservée aux membres du foyer.
-- Écriture réservée au service_role (TASTE_PROFILE agent Celery).
-- Les utilisateurs ne modifient JAMAIS directement leur vecteur de goût.
-- -----------------------------------------------------------------------------

CREATE POLICY member_taste_vectors_select
    ON member_taste_vectors
    FOR SELECT
    TO authenticated
    USING (
        member_id IN (
            SELECT id FROM household_members
            WHERE household_id = get_current_household_id()
        )
    );

-- Pas de policy INSERT/UPDATE/DELETE pour authenticated → seul le service_role écrit ici.

-- -----------------------------------------------------------------------------
-- POLICIES : recipe_feedbacks
-- Lecture : tous les membres du foyer (visualisation collective des goûts)
-- Écriture : uniquement le membre lui-même peut créer un feedback
-- -----------------------------------------------------------------------------

CREATE POLICY recipe_feedbacks_select
    ON recipe_feedbacks
    FOR SELECT
    TO authenticated
    USING (
        household_id = get_current_household_id()
    );

CREATE POLICY recipe_feedbacks_insert
    ON recipe_feedbacks
    FOR INSERT
    TO authenticated
    WITH CHECK (
        household_id = get_current_household_id()
        -- Un membre ne peut créer un feedback que pour lui-même
        AND member_id IN (
            SELECT id FROM household_members
            WHERE supabase_user_id = auth.uid()
        )
    );

-- BUG #3 (review 2026-04-12) : Policy DELETE ajoutée sur recipe_feedbacks.
-- Décision : les feedbacks restent immuables une fois soumis (audit trail complet).
-- Un utilisateur souhaitant "corriger" son feedback crée un nouveau feedback.
-- La suppression directe n'est PAS offerte côté authenticated — uniquement service_role.
-- Ce commentaire remplace la policy DELETE absente : l'absence est VOLONTAIRE et documentée.
--
-- Note pour Phase 2 : si le besoin de retrait RGPD (droit à l'oubli) émerge,
-- implémenter une procédure service_role dédiée avec journalisation dans audit_log,
-- plutôt qu'une policy DELETE directe qui contournerait la traçabilité.

-- -----------------------------------------------------------------------------
-- POLICIES : weekly_plans
-- Isolation stricte par household. Supabase Realtime écoute cette table.
-- IMPORTANT : Realtime applique les RLS policies pour filtrer les événements WebSocket.
-- -----------------------------------------------------------------------------

CREATE POLICY weekly_plans_select
    ON weekly_plans
    FOR SELECT
    TO authenticated
    USING (
        household_id = get_current_household_id()
    );

CREATE POLICY weekly_plans_insert
    ON weekly_plans
    FOR INSERT
    TO authenticated
    WITH CHECK (
        household_id = get_current_household_id()
    );

CREATE POLICY weekly_plans_update
    ON weekly_plans
    FOR UPDATE
    TO authenticated
    USING (
        household_id = get_current_household_id()
    )
    WITH CHECK (
        household_id = get_current_household_id()
    );

-- BUG #3 (review 2026-04-12) : Policy DELETE manquante sur weekly_plans.
-- Cas d'usage légitime : un utilisateur veut repartir de zéro sur son plan de la semaine.
-- Restriction : uniquement les plans en status 'draft' peuvent être supprimés.
-- Les plans validated/archived ont déjà déclenché CART_BUILDER et/ou BOOK_GENERATOR →
-- leur suppression via RLS utilisateur est intentionnellement bloquée (service_role uniquement).
CREATE POLICY weekly_plans_delete
    ON weekly_plans
    FOR DELETE
    TO authenticated
    USING (
        household_id = get_current_household_id()
        AND status = 'draft'
    );

-- -----------------------------------------------------------------------------
-- POLICIES : planned_meals
-- Accès via le plan parent — on remonte household_id via weekly_plans.
-- PIÈGE : Supabase RLS ne supporte pas les JOINs complexes dans USING directement.
-- On utilise une sous-requête IN qui reste lisible et performante avec l'index btree.
-- -----------------------------------------------------------------------------

CREATE POLICY planned_meals_select
    ON planned_meals
    FOR SELECT
    TO authenticated
    USING (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
        )
    );

CREATE POLICY planned_meals_insert
    ON planned_meals
    FOR INSERT
    TO authenticated
    WITH CHECK (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
        )
    );

CREATE POLICY planned_meals_update
    ON planned_meals
    FOR UPDATE
    TO authenticated
    USING (
        -- BUG #3 (review 2026-04-12) : Restriction UPDATE aux plans en status 'draft' uniquement.
        -- Raison : un plan validé ou archivé a déjà généré une shopping_list et potentiellement
        -- un weekly_book PDF. Modifier un repas sur un plan non-draft crée une incohérence
        -- entre les données DB et le PDF déjà envoyé à l'utilisateur.
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
              AND status = 'draft'
        )
    )
    -- FIX #1 (review 2026-04-12) : WITH CHECK manquant → faille cross-tenant.
    -- Sans WITH CHECK, un UPDATE pouvait changer plan_id pour pointer vers un plan
    -- d'un autre foyer. WITH CHECK identique à USING : la valeur écrite reste dans
    -- les plans draft du foyer courant.
    WITH CHECK (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
              AND status = 'draft'
        )
    );

CREATE POLICY planned_meals_delete
    ON planned_meals
    FOR DELETE
    TO authenticated
    USING (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
              -- On ne peut supprimer des repas que d'un plan encore en cours d'édition
              AND status = 'draft'
        )
    );

-- -----------------------------------------------------------------------------
-- POLICIES : shopping_lists
-- Partagée en temps réel via Supabase Realtime. RLS filtre les événements WebSocket.
-- -----------------------------------------------------------------------------

CREATE POLICY shopping_lists_select
    ON shopping_lists
    FOR SELECT
    TO authenticated
    USING (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
        )
    );

-- BUG #3 (review 2026-04-12) : Policy UPDATE manquante sur shopping_lists.
-- Cas d'usage légitime : cocher un article de la liste de courses (champ dans items JSONB).
-- L'UPDATE porte sur la colonne items (jsonb patch) — la structure de la liste est
-- générée par CART_BUILDER (service_role), mais le cochage est une action utilisateur.
-- WITH CHECK identique à USING : on ne peut pas déplacer la liste vers un autre plan.
CREATE POLICY shopping_lists_update
    ON shopping_lists
    FOR UPDATE
    TO authenticated
    USING (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
        )
    )
    -- FIX #1 / BUG #3 (review 2026-04-12) : WITH CHECK inclus dès la création
    -- (pas de WITH CHECK absent à corriger ultérieurement sur cette policy).
    WITH CHECK (
        plan_id IN (
            SELECT id FROM weekly_plans
            WHERE household_id = get_current_household_id()
        )
    );

-- -----------------------------------------------------------------------------
-- POLICIES : fridge_items
-- Lecture/écriture pour tous les membres du foyer (frigo partagé).
-- -----------------------------------------------------------------------------

CREATE POLICY fridge_items_select
    ON fridge_items
    FOR SELECT
    TO authenticated
    USING (
        household_id = get_current_household_id()
    );

CREATE POLICY fridge_items_insert
    ON fridge_items
    FOR INSERT
    TO authenticated
    WITH CHECK (
        household_id = get_current_household_id()
    );

CREATE POLICY fridge_items_update
    ON fridge_items
    FOR UPDATE
    TO authenticated
    USING (
        household_id = get_current_household_id()
    )
    -- FIX #1 (review 2026-04-12) : WITH CHECK manquant → faille cross-tenant.
    -- Sans WITH CHECK, un UPDATE pouvait déplacer household_id vers un autre foyer
    -- (exfiltration de données frigo entre tenants via UPDATE + changement household_id).
    -- WITH CHECK identique à USING : la valeur écrite reste dans le foyer courant.
    WITH CHECK (
        household_id = get_current_household_id()
    );

-- BUG #3 (review 2026-04-12) : Policy DELETE sur fridge_items (ingrédient consommé).
-- Cas d'usage : un membre consomme un ingrédient et le retire du frigo.
-- Présente dans le fichier original — conservée sans modification.
CREATE POLICY fridge_items_delete
    ON fridge_items
    FOR DELETE
    TO authenticated
    USING (
        household_id = get_current_household_id()
    );

-- -----------------------------------------------------------------------------
-- POLICIES : weekly_books
-- Lecture seule pour les membres du foyer. Écriture par service_role uniquement.
-- -----------------------------------------------------------------------------

CREATE POLICY weekly_books_select
    ON weekly_books
    FOR SELECT
    TO authenticated
    USING (
        household_id = get_current_household_id()
    );

-- -----------------------------------------------------------------------------
-- POLICIES : subscriptions
-- Lecture pour l'owner uniquement (sensibilité financière).
-- Écriture par service_role (webhook Stripe côté backend FastAPI).
-- -----------------------------------------------------------------------------

CREATE POLICY subscriptions_select
    ON subscriptions
    FOR SELECT
    TO authenticated
    USING (
        household_id IN (
            SELECT household_id
            FROM household_members
            WHERE supabase_user_id = auth.uid()
              AND role = 'owner'
        )
    );

-- -----------------------------------------------------------------------------
-- GRANTS — Tables publiques (recettes, ingrédients)
-- Pas de RLS nécessaire : données non-tenant. On accorde SELECT à anon et authenticated.
-- Les writes sont réservés au service_role.
-- -----------------------------------------------------------------------------

GRANT SELECT ON recipes              TO anon, authenticated;
GRANT SELECT ON recipe_embeddings    TO anon, authenticated;
GRANT SELECT ON ingredients          TO anon, authenticated;
GRANT SELECT ON recipe_ingredients   TO anon, authenticated;

-- Le service_role a accès complet à tout (bypass RLS par définition Supabase).
-- Pas besoin de GRANT explicite pour service_role.
