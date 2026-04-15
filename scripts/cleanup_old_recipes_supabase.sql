-- =============================================================================
-- cleanup_old_recipes_supabase.sql
-- Migration : suppression des anciennes recettes non-françaises sur Supabase
-- =============================================================================
--
-- OBJECTIF
-- Supprimer toutes les recettes dont la source n'est pas 'marmiton' ou '750g'
-- ou dont la langue n'est pas 'fr', ainsi que toutes leurs données liées.
--
-- TABLES RÉFÉRENÇANT recipes (via FK)
-- ┌────────────────────┬───────────────┬─────────────────────────────────────┐
-- │ Table              │ ON DELETE     │ Action requise                      │
-- ├────────────────────┼───────────────┼─────────────────────────────────────┤
-- │ planned_meals      │ RESTRICT      │ DELETE MANUEL OBLIGATOIRE en premier│
-- │ recipe_feedbacks   │ CASCADE       │ Auto-supprimé avec recipes           │
-- │ recipe_embeddings  │ CASCADE       │ Auto-supprimé avec recipes           │
-- │ recipe_ingredients │ CASCADE       │ Auto-supprimé avec recipes           │
-- └────────────────────┴───────────────┴─────────────────────────────────────┘
--
-- TRIGGERS SUR recipes
-- - set_updated_at_recipes         → BEFORE UPDATE  (inoffensif pour DELETE)
-- - sync_recipe_embeddings_metadata → AFTER UPDATE   (inoffensif pour DELETE)
-- - validate_recipe_quality_before_insert → BEFORE INSERT/UPDATE (inoffensif pour DELETE)
-- Les triggers ne s'exécutent pas sur DELETE — aucune désactivation nécessaire.
--
-- RLS
-- - recipes, recipe_ingredients, recipe_embeddings : RLS désactivé (relrowsecurity=false)
-- - planned_meals : RLS activé et forcé — le script doit s'exécuter en tant que
--   superuser (postgres) ou service_role pour contourner les policies.
-- - recipe_feedbacks : RLS activé et forcé — même contrainte.
--
-- RISQUE PRINCIPAL : planned_meals avec ON DELETE RESTRICT
-- Si des utilisateurs en production ont des meal plans actifs référençant des
-- anciennes recettes, la suppression directe de ces recettes sera BLOQUÉE par
-- la FK RESTRICT. Le script supprime d'abord les planned_meals concernées.
-- CONSÉQUENCE : les meal plans des utilisateurs qui contenaient ces recettes
-- seront incomplets (créneaux vides). Les weekly_plans et weekly_books parent
-- restent intacts — seules les entrées planned_meals ciblées sont supprimées.
--
-- EXÉCUTION
-- Sur Supabase : SQL Editor en tant que service_role, ou via psql avec
-- la connection string service_role (pas anon).
--
-- Commande locale de test (Docker) :
--   docker exec mealplanner_postgres psql -U mealplanner -d mealplanner_dev \
--     -f /path/to/cleanup_old_recipes_supabase.sql
--
-- =============================================================================

BEGIN;

-- Sécurité : s'assurer que le script est annulable si une erreur survient
SET LOCAL statement_timeout = '10min';

-- =============================================================================
-- PRÉ-REQUIS : Ajouter la colonne language si elle n'existe pas encore
-- (ajoutée en dev local via commit 4e79a0a mais jamais migrée en prod)
-- =============================================================================

ALTER TABLE public.recipes ADD COLUMN IF NOT EXISTS language text;

-- Marquer toutes les recettes existantes sans language comme non-FR
-- (ce sont les anciennes recettes anglaises à supprimer)
UPDATE public.recipes SET language = 'en' WHERE language IS NULL;

-- =============================================================================
-- ÉTAPE 0 : DIAGNOSTIC INITIAL — COUNTS AVANT SUPPRESSION
-- =============================================================================

DO $$
DECLARE
    v_recipes_total         INTEGER;
    v_recipes_to_delete     INTEGER;
    v_recipes_to_keep       INTEGER;
    v_planned_meals_at_risk INTEGER;
    v_feedbacks_at_risk     INTEGER;
    v_embeddings_at_risk    INTEGER;
    v_ingredients_at_risk   INTEGER;
BEGIN
    -- Total recettes
    SELECT COUNT(*) INTO v_recipes_total FROM public.recipes;

    -- Recettes à supprimer (non FR ou source non connue)
    SELECT COUNT(*) INTO v_recipes_to_delete
    FROM public.recipes
    WHERE source NOT IN ('marmiton', '750g')
       OR language IS DISTINCT FROM 'fr';

    -- Recettes à conserver
    v_recipes_to_keep := v_recipes_total - v_recipes_to_delete;

    -- planned_meals bloquants (FK RESTRICT)
    SELECT COUNT(*) INTO v_planned_meals_at_risk
    FROM public.planned_meals pm
    JOIN public.recipes r ON pm.recipe_id = r.id
    WHERE r.source NOT IN ('marmiton', '750g')
       OR r.language IS DISTINCT FROM 'fr';

    -- recipe_feedbacks à cascader
    SELECT COUNT(*) INTO v_feedbacks_at_risk
    FROM public.recipe_feedbacks rf
    JOIN public.recipes r ON rf.recipe_id = r.id
    WHERE r.source NOT IN ('marmiton', '750g')
       OR r.language IS DISTINCT FROM 'fr';

    -- recipe_embeddings à cascader
    SELECT COUNT(*) INTO v_embeddings_at_risk
    FROM public.recipe_embeddings re
    JOIN public.recipes r ON re.recipe_id = r.id
    WHERE r.source NOT IN ('marmiton', '750g')
       OR r.language IS DISTINCT FROM 'fr';

    -- recipe_ingredients à cascader
    SELECT COUNT(*) INTO v_ingredients_at_risk
    FROM public.recipe_ingredients ri
    JOIN public.recipes r ON ri.recipe_id = r.id
    WHERE r.source NOT IN ('marmiton', '750g')
       OR r.language IS DISTINCT FROM 'fr';

    RAISE NOTICE '==================================================';
    RAISE NOTICE 'DIAGNOSTIC AVANT SUPPRESSION';
    RAISE NOTICE '==================================================';
    RAISE NOTICE 'recipes total              : %', v_recipes_total;
    RAISE NOTICE 'recipes à supprimer        : %', v_recipes_to_delete;
    RAISE NOTICE 'recipes à conserver        : %', v_recipes_to_keep;
    RAISE NOTICE '--------------------------------------------------';
    RAISE NOTICE 'planned_meals impactées    : % (FK RESTRICT — suppression manuelle)', v_planned_meals_at_risk;
    RAISE NOTICE 'recipe_feedbacks impactées : % (CASCADE auto)', v_feedbacks_at_risk;
    RAISE NOTICE 'recipe_embeddings impactées: % (CASCADE auto)', v_embeddings_at_risk;
    RAISE NOTICE 'recipe_ingredients impactées: % (CASCADE auto)', v_ingredients_at_risk;
    RAISE NOTICE '==================================================';

    -- Garde-fou : si aucune recette à supprimer, terminer proprement
    IF v_recipes_to_delete = 0 THEN
        RAISE NOTICE 'AUCUNE recette à supprimer — base déjà propre. Transaction annulée.';
        RAISE EXCEPTION 'NOTHING_TO_DELETE' USING ERRCODE = 'P0001';
    END IF;
END;
$$;

-- =============================================================================
-- ÉTAPE 1 : IDENTIFIER LES RECETTES CIBLES
-- Table temporaire pour éviter des sous-requêtes répétées
-- =============================================================================

CREATE TEMP TABLE _recipes_to_delete AS
SELECT id, title, source, language
FROM public.recipes
WHERE source NOT IN ('marmiton', '750g')
   OR language IS DISTINCT FROM 'fr';

-- Index pour les jointures suivantes
CREATE INDEX ON _recipes_to_delete (id);

DO $$
BEGIN
    RAISE NOTICE 'ÉTAPE 1 — Table temporaire _recipes_to_delete créée avec % entrées.',
        (SELECT COUNT(*) FROM _recipes_to_delete);
END;
$$;

-- =============================================================================
-- ÉTAPE 2 : planned_meals — suppression manuelle (FK RESTRICT)
-- RISQUE : des créneaux de meal plans utilisateurs seront perdus pour ces recettes.
-- Les weekly_plans et weekly_books RESTENT INTACTS.
-- =============================================================================

DO $$
DECLARE
    v_deleted_planned_meals INTEGER;
    v_households_affected   INTEGER;
BEGIN
    -- Identifier les foyers affectés avant suppression (pour log d'audit)
    SELECT COUNT(DISTINCT wp.household_id) INTO v_households_affected
    FROM public.planned_meals pm
    JOIN _recipes_to_delete rtd ON pm.recipe_id = rtd.id
    JOIN public.weekly_plans wp ON pm.plan_id = wp.id;

    -- Supprimer les planned_meals référençant des recettes ciblées
    DELETE FROM public.planned_meals pm
    WHERE pm.recipe_id IN (SELECT id FROM _recipes_to_delete);

    GET DIAGNOSTICS v_deleted_planned_meals = ROW_COUNT;

    RAISE NOTICE 'ÉTAPE 2 — planned_meals supprimées : % (% foyers affectés)',
        v_deleted_planned_meals, v_households_affected;
END;
$$;

-- =============================================================================
-- ÉTAPE 3 : Suppression des recettes cibles
-- Les tables avec CASCADE (recipe_ingredients, recipe_embeddings, recipe_feedbacks)
-- sont nettoyées automatiquement par PostgreSQL.
-- =============================================================================

DO $$
DECLARE
    v_deleted_recipes INTEGER;
BEGIN
    DELETE FROM public.recipes r
    WHERE r.id IN (SELECT id FROM _recipes_to_delete);

    GET DIAGNOSTICS v_deleted_recipes = ROW_COUNT;

    RAISE NOTICE 'ÉTAPE 3 — recipes supprimées : %', v_deleted_recipes;
END;
$$;

-- =============================================================================
-- ÉTAPE 4 : NETTOYAGE DES EMBEDDINGS ORPHELINS (sécurité supplémentaire)
-- Appel de la fonction existante cleanup_old_embeddings()
-- =============================================================================

DO $$
DECLARE
    v_orphan_embeddings INTEGER;
BEGIN
    SELECT public.cleanup_old_embeddings() INTO v_orphan_embeddings;
    RAISE NOTICE 'ÉTAPE 4 — embeddings orphelins nettoyés : %', v_orphan_embeddings;
END;
$$;

-- =============================================================================
-- ÉTAPE 5 : DIAGNOSTIC FINAL — COUNTS APRÈS SUPPRESSION
-- =============================================================================

DO $$
DECLARE
    v_recipes_remaining     INTEGER;
    v_planned_meals_remain  INTEGER;
    v_feedbacks_remain      INTEGER;
    v_embeddings_remain     INTEGER;
    v_ingredients_remain    INTEGER;
    v_marmiton_count        INTEGER;
    v_750g_count            INTEGER;
    v_orphan_check          INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_recipes_remaining FROM public.recipes;
    SELECT COUNT(*) INTO v_planned_meals_remain FROM public.planned_meals;
    SELECT COUNT(*) INTO v_feedbacks_remain FROM public.recipe_feedbacks;
    SELECT COUNT(*) INTO v_embeddings_remain FROM public.recipe_embeddings;
    SELECT COUNT(*) INTO v_ingredients_remain FROM public.recipe_ingredients;

    SELECT COUNT(*) INTO v_marmiton_count FROM public.recipes WHERE source = 'marmiton' AND language = 'fr';
    SELECT COUNT(*) INTO v_750g_count FROM public.recipes WHERE source = '750g' AND language = 'fr';

    -- Vérification d'intégrité : aucune recette non-FR ne doit subsister
    SELECT COUNT(*) INTO v_orphan_check
    FROM public.recipes
    WHERE source NOT IN ('marmiton', '750g')
       OR language IS DISTINCT FROM 'fr';

    RAISE NOTICE '==================================================';
    RAISE NOTICE 'DIAGNOSTIC APRÈS SUPPRESSION';
    RAISE NOTICE '==================================================';
    RAISE NOTICE 'recipes restantes          : %', v_recipes_remaining;
    RAISE NOTICE '  dont marmiton/fr         : %', v_marmiton_count;
    RAISE NOTICE '  dont 750g/fr             : %', v_750g_count;
    RAISE NOTICE 'planned_meals restantes    : %', v_planned_meals_remain;
    RAISE NOTICE 'recipe_feedbacks restantes : %', v_feedbacks_remain;
    RAISE NOTICE 'recipe_embeddings restantes: %', v_embeddings_remain;
    RAISE NOTICE 'recipe_ingredients restantes: %', v_ingredients_remain;
    RAISE NOTICE '--------------------------------------------------';
    RAISE NOTICE 'VÉRIFICATION INTÉGRITÉ';
    RAISE NOTICE 'Recettes non-FR subsistantes: % (doit être 0)', v_orphan_check;

    IF v_orphan_check > 0 THEN
        RAISE EXCEPTION 'ÉCHEC INTÉGRITÉ : % recettes non-FR subsistent après nettoyage',
            v_orphan_check;
    END IF;

    RAISE NOTICE 'INTÉGRITÉ OK — aucune recette non-FR restante.';
    RAISE NOTICE '==================================================';
END;
$$;

-- =============================================================================
-- ÉTAPE 6 : NETTOYAGE DE LA TABLE TEMPORAIRE
-- =============================================================================

DROP TABLE IF EXISTS _recipes_to_delete;

-- =============================================================================
-- COMMIT FINAL
-- En cas de doute, remplacer COMMIT par ROLLBACK pour un dry-run.
-- =============================================================================

COMMIT;

-- Après COMMIT, vérification finale hors transaction
SELECT
    source,
    COALESCE(language, '(null)') AS language,
    COUNT(*) AS count_restant
FROM public.recipes
GROUP BY source, language
ORDER BY count_restant DESC;
