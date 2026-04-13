-- =============================================================================
-- 04-triggers-functions.sql
-- Fonctions PostgreSQL et triggers — MealPlanner SaaS
-- À exécuter AVANT 03-rls-policies.sql (get_current_household_id est une dépendance).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- FONCTION : get_current_household_id()
-- Retourne le household_id de l'utilisateur Supabase Auth connecté.
-- Utilisée dans TOUTES les policies RLS pour centraliser la logique d'appartenance.
--
-- SECURITY DEFINER : la fonction s'exécute avec les droits de son propriétaire
-- (postgres), pas ceux de l'appelant. Nécessaire car l'utilisateur authenticated
-- n'a pas nécessairement de GRANT SELECT direct sur household_members.
--
-- STABLE : PostgreSQL peut mettre en cache le résultat pour la durée de la transaction,
-- évitant de répéter la sous-requête à chaque évaluation de policy.
-- IMPORTANT : toujours SET search_path TO '' pour éviter les injections via search_path.
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
-- Une seule fonction générique réutilisée par tous les triggers.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
-- FIX residuel (review 2026-04-12) : SECURITY DEFINER + SET search_path TO '' manquants.
-- Même si ce trigger ne lit aucune table tierce, la règle défensive uniforme du projet
-- exige que toutes les fonctions SECURITY DEFINER aient search_path verrouillé à vide.
-- Sans cela, un acteur contrôlant search_path peut substituer la fonction now() par la sienne.
SECURITY DEFINER
SET search_path TO ''
AS $$
BEGIN
    -- On force la mise à jour même si l'appelant tente de passer une valeur explicite.
    -- Cela garantit que updated_at reflète toujours l'heure réelle du dernier changement.
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION trigger_set_updated_at() IS
    'Trigger générique : force updated_at = now() sur tout UPDATE. '
    'Protège contre les mises à jour silencieuses qui oublieraient ce champ.';

-- Déclaration des triggers updated_at sur toutes les tables concernées
CREATE TRIGGER set_updated_at_households
    BEFORE UPDATE ON households
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_household_members
    BEFORE UPDATE ON household_members
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_member_preferences
    BEFORE UPDATE ON member_preferences
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_recipes
    BEFORE UPDATE ON recipes
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_recipe_embeddings
    BEFORE UPDATE ON recipe_embeddings
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_weekly_plans
    BEFORE UPDATE ON weekly_plans
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_subscriptions
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- -----------------------------------------------------------------------------
-- TRIGGER : validation qualité des recettes avant insertion
-- Règle ROADMAP : "une recette mal structurée vaut moins qu'une recette absente"
-- quality_score < 0.6 → rejet. Ce seuil est volontairement strict en phase 0.
-- Il pourra être abaissé par migration en cas de besoin (ex : 0.5 pour les recettes FR rares).
--
-- Cette validation est en DOUBLE avec la contrainte CHECK du schéma.
-- La contrainte CHECK protège contre les inserts directs en base.
-- Le trigger donne un message d'erreur lisible pour les logs Celery (RECIPE_SCOUT).
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_recipe_quality()
RETURNS TRIGGER
LANGUAGE plpgsql
-- FIX residuel (review 2026-04-12) : SECURITY DEFINER + SET search_path TO '' manquants.
-- Le trigger s'exécute BEFORE INSERT OR UPDATE ON recipes avec les droits du caller.
-- En ajoutant SECURITY DEFINER + search_path vide, on prévient l'injection via search_path
-- (ex : substitution de la table recipes vers une table factice dans un schéma malveillant).
-- Le corps utilise NEW.* uniquement (pas de SELECT externe) — pas d'impact fonctionnel.
SECURITY DEFINER
SET search_path TO ''
AS $$
BEGIN
    -- Vérification du seuil de qualité minimum avant insertion
    IF NEW.quality_score < 0.6 THEN
        RAISE EXCEPTION
            'Recette rejetée : quality_score=% insuffisant (seuil=0.6). '
            'Recette : %. Source : %.',
            NEW.quality_score,
            NEW.title,
            NEW.source
            USING ERRCODE = 'check_violation';
    END IF;

    -- Vérification que les instructions ne sont pas vides
    -- Une recette sans instructions est inutilisable pour l'utilisateur
    IF NEW.instructions = '[]'::jsonb OR NEW.instructions IS NULL THEN
        RAISE EXCEPTION
            'Recette rejetée : instructions vides. Recette : %. Source : %.',
            NEW.title,
            NEW.source
            USING ERRCODE = 'check_violation';
    END IF;

    -- Vérification du temps total cohérent
    -- Une recette déclarée à 0 minute est probablement un import mal formé
    IF COALESCE(NEW.prep_time_min, 0) + COALESCE(NEW.cook_time_min, 0) = 0 THEN
        RAISE WARNING
            'Recette % (source: %) : temps total = 0 minute. '
            'Vérifier les données source.',
            NEW.title,
            NEW.source;
        -- WARNING seulement, pas de rejet : certaines recettes (ex: salade) ont 0 min de cuisson
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION validate_recipe_quality() IS
    'Trigger BEFORE INSERT/UPDATE sur recipes. '
    'Rejette les recettes avec quality_score < 0.6 (règle ROADMAP section 10). '
    'Émet un WARNING (sans rejet) pour les recettes à temps zéro. '
    'Le message d''erreur est loggé par RECIPE_SCOUT via Celery loguru.';

CREATE TRIGGER validate_recipe_quality_before_insert
    BEFORE INSERT OR UPDATE ON recipes
    FOR EACH ROW EXECUTE FUNCTION validate_recipe_quality();

-- -----------------------------------------------------------------------------
-- FONCTION : get_household_constraints(p_household_id UUID)
-- Vue agrégée des contraintes de tous les membres d'un foyer.
-- Utilisée par WEEKLY_PLANNER pour construire le filtre de recettes autorisées.
-- Retourne l'UNION des allergies et diet_tags de tous les membres.
-- -----------------------------------------------------------------------------

-- FIX #4 (review 2026-04-12) : Réécriture complète de get_household_constraints().
-- Problèmes corrigés :
--   1. La version originale faisait LEFT JOIN LATERAL des deux tableaux JSONB simultanément,
--      ce qui produisait un produit cartésien (N allergies × M diet_tags lignes par membre).
--      MIN(cooking_time_max) et MIN(budget_pref) étaient calculés sur ces lignes dupliquées.
--      Pour MIN numérique c'est correct par hasard, mais pour budget_pref (TEXT) c'est faux.
--   2. MIN(TEXT) sur budget_pref utilise l'ordre lexicographique unicode, non l'ordre sémantique.
--      Avec locale FR, 'é' > 'p' > 'm', donc MIN retourne 'moyen' au lieu de 'économique'.
--      Des foyers avec membres économiques et premium recevaient des recettes premium.
--   Correction : CTEs séparées pour chaque agrégation → aucun produit cartésien possible.
--   Budget_pref : CASE WHEN avec ordre sémantique explicite 1='économique' < 2='moyen' < 3='premium'.
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
    -- CTE 1 : union des allergies (dépliage JSONB indépendant)
    WITH allergies_cte AS (
        SELECT DISTINCT a.allergy_item
        FROM public.household_members hm
        JOIN public.member_preferences mp ON mp.member_id = hm.id
        CROSS JOIN LATERAL jsonb_array_elements_text(mp.allergies) AS a(allergy_item)
        WHERE hm.household_id = p_household_id
          AND a.allergy_item IS NOT NULL
    ),
    -- CTE 2 : union des régimes alimentaires (dépliage JSONB indépendant)
    diets_cte AS (
        SELECT DISTINCT d.diet_item
        FROM public.household_members hm
        JOIN public.member_preferences mp ON mp.member_id = hm.id
        CROSS JOIN LATERAL jsonb_array_elements_text(mp.diet_tags) AS d(diet_item)
        WHERE hm.household_id = p_household_id
          AND d.diet_item IS NOT NULL
    ),
    -- CTE 3 : contraintes scalaires (sans dépliage JSONB → aucune duplication de lignes)
    scalars_cte AS (
        SELECT
            MIN(mp.cooking_time_max) AS max_cooking_time,
            -- FIX #4 (review 2026-04-12) : ordre sémantique explicite via CASE WHEN.
            -- On mappe sur un entier, MIN retourne le plus économique, on remappe en TEXT.
            -- Protège contre toute variation de locale FR qui trie 'é' différemment.
            MIN(
                CASE mp.budget_pref
                    WHEN 'économique' THEN 1
                    WHEN 'moyen'      THEN 2
                    WHEN 'premium'    THEN 3
                    ELSE NULL  -- Membres sans préférence ignorés (pas de contrainte)
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
        -- Conversion retour entier → TEXT sémantique
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
    'Règle : toute contrainte individuelle devient une contrainte du foyer entier. '
    'FIX #4 (2026-04-12) : CTEs séparées pour éviter le produit cartésien JSONB. '
    'Budget_pref résolu par CASE WHEN (ordre sémantique) et non MIN(TEXT) (ordre lexicographique).';

-- -----------------------------------------------------------------------------
-- FONCTION : cleanup_old_embeddings()
-- Supprime les embeddings orphelins (recettes supprimées).
-- Planifiée via pg_cron ou Celery beat (hebdomadaire).
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION cleanup_old_embeddings()
RETURNS INT
LANGUAGE plpgsql
-- Ajout SET search_path pour cohérence défensive (debug-audit.md point MEDIUM)
SET search_path TO ''
AS $$
DECLARE
    deleted_count INT;
BEGIN
    -- HIGH-3 (review 2026-04-12) : remplacement de NOT IN par NOT EXISTS.
    -- Raison : NOT IN avec sous-requête est dangereux si un seul id vaut NULL
    -- (NOT IN retourne FALSE pour toutes les lignes → aucune suppression, bug silencieux).
    -- recipes.id est NOT NULL (PK) mais la règle s'applique défensivement.
    -- NOT EXISTS est aussi plus favorable au planner pour les hash join sur 50 000 rows.
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
-- BUG #2 (review 2026-04-12) : Fonction create_household_with_owner()
-- Résout le deadlock d'onboarding causé par la récursion RLS sur household_members_insert.
--
-- Principe : cette fonction tourne en SECURITY DEFINER (droits du propriétaire = postgres),
-- ce qui bypasse la RLS de household_members. Elle encapsule de façon atomique :
--   1. INSERT households (nouveau foyer)
--   2. INSERT household_members (premier owner)
-- L'atomicité (transaction implicite en PL/pgSQL) garantit qu'on ne crée jamais un foyer
-- sans owner ni un owner sans foyer.
--
-- Sécurité : la fonction vérifie que supabase_user_id n'appartient pas déjà à un foyer
-- (contrainte UNIQUE sur household_members.supabase_user_id), ce qui empêche les doublons.
--
-- Utilisation côté API FastAPI (avec service_role key) :
--   SELECT * FROM create_household_with_owner(
--       'Famille Dupont',           -- p_household_name
--       'uuid-supabase-user-id',    -- p_supabase_user_id
--       'Marie'                     -- p_display_name
--   );
-- Retourne : household_id (UUID) et member_id (UUID) du owner créé.
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
    -- Vérification que l'utilisateur n'a pas déjà un foyer (contrainte UNIQUE respectée).
    -- On remonte une erreur claire plutôt que de laisser PostgreSQL générer une violation UNIQUE.
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

    -- Insertion atomique du foyer
    INSERT INTO public.households (name)
    VALUES (p_household_name)
    RETURNING id INTO v_household_id;

    -- Insertion atomique du premier owner (bypass RLS grâce à SECURITY DEFINER)
    INSERT INTO public.household_members (household_id, supabase_user_id, role, display_name)
    VALUES (v_household_id, p_supabase_user_id, 'owner', p_display_name)
    RETURNING id INTO v_member_id;

    RETURN QUERY SELECT v_household_id, v_member_id;
END;
$$;

COMMENT ON FUNCTION create_household_with_owner(TEXT, UUID, TEXT) IS
    'BUG #2 (2026-04-12) : Création atomique d''un foyer avec son premier owner. '
    'Bypasse la RLS via SECURITY DEFINER pour résoudre le deadlock d''onboarding. '
    'La policy INSERT household_members authenticated est désactivée : '
    'TOUTE création de foyer doit passer par cette fonction via service_role. '
    'Appelée côté API FastAPI avec supabase_client configuré avec SUPABASE_SERVICE_ROLE_KEY.';

-- -----------------------------------------------------------------------------
-- OPT #1 (review 2026-04-12) : Trigger de synchronisation des colonnes dénormalisées
-- dans recipe_embeddings depuis recipes.
-- Raison : les colonnes tags, total_time_min, difficulty, cuisine_type ont été
-- dénormalisées dans recipe_embeddings pour permettre le pré-filtrage HNSW (voir
-- 01-schema-core.sql et 02-indexes.sql). Ce trigger maintient la cohérence automatiquement.
--
-- Déclenchement : AFTER UPDATE sur recipes, uniquement si les colonnes dénormalisées changent.
-- Pas de trigger INSERT : lors de l'insertion d'un embedding (RECIPE_SCOUT),
-- le pipeline doit passer les valeurs explicitement (voir commentaire dans recipe_embeddings).
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION recipe_embeddings_sync_metadata()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path TO ''
AS $$
BEGIN
    -- Synchronisation uniquement si l'une des colonnes dénormalisées a réellement changé.
    -- Évite une mise à jour inutile de recipe_embeddings sur chaque UPDATE recette.
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
    '(tags, total_time_min, difficulty, cuisine_type) ont réellement changé. '
    'Évite les mises à jour en cascade inutiles sur photo_url, description, etc.';

CREATE TRIGGER sync_recipe_embeddings_metadata
    AFTER UPDATE ON recipes
    FOR EACH ROW EXECUTE FUNCTION recipe_embeddings_sync_metadata();
