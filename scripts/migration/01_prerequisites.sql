-- =============================================================================
-- FICHIER 01/07 — PRÉ-REQUIS + NETTOYAGE INGRÉDIENTS
-- Exécuter EN PREMIER avant tous les autres fichiers de migration.
-- =============================================================================
-- Ce script :
--   1. Ajoute la colonne `language` si absente
--   2. Supprime TOUS les anciens ingrédients orphelins (sûr car les anciennes
--      recettes + recipe_ingredients ont déjà été supprimées par le cleanup)
--   3. Active session_replication_role = replica pour les INSERT suivants
-- =============================================================================

-- 1. Colonne language (ajoutée en dev, pas encore migrée en prod)
ALTER TABLE public.recipes ADD COLUMN IF NOT EXISTS language text;

-- 2. Nettoyage des anciens ingrédients
-- Après le cleanup, les old recipes sont supprimées → recipe_ingredients CASCADE.
-- Il ne reste que des ingrédients orphelins avec des UUID différents de Docker.
-- On doit les supprimer pour insérer les nouveaux avec les bons UUID.
--
-- Géré via DO block pour :
--   a) Vérifier que recipe_ingredients est bien vide (sinon ABORT)
--   b) Gérer le cas où fridge_items n'existe pas en prod
DO $$
DECLARE
    v_ri_count INTEGER;
    v_fi_count INTEGER := 0;
    v_ing_deleted INTEGER;
    v_fridge_exists BOOLEAN;
BEGIN
    -- Combien de recipe_ingredients restent ?
    SELECT COUNT(*) INTO v_ri_count FROM public.recipe_ingredients;

    IF v_ri_count > 0 THEN
        RAISE WARNING 'recipe_ingredients contient encore % lignes — suppression en cascade', v_ri_count;
        DELETE FROM public.recipe_ingredients;
    END IF;

    -- fridge_items existe-t-elle ?
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'fridge_items'
    ) INTO v_fridge_exists;

    IF v_fridge_exists THEN
        SELECT COUNT(*) INTO v_fi_count
        FROM public.fridge_items
        WHERE ingredient_id IS NOT NULL;
    END IF;

    IF v_fi_count > 0 THEN
        -- Supprimer uniquement les ingrédients NON référencés par fridge_items
        DELETE FROM public.ingredients
        WHERE id NOT IN (
            SELECT DISTINCT ingredient_id FROM public.fridge_items
            WHERE ingredient_id IS NOT NULL
        );
        GET DIAGNOSTICS v_ing_deleted = ROW_COUNT;
        RAISE NOTICE 'Ingrédients supprimés : % (% protégés par fridge_items)', v_ing_deleted, v_fi_count;
    ELSE
        -- Aucun fridge_item — on peut tout supprimer
        DELETE FROM public.ingredients;
        GET DIAGNOSTICS v_ing_deleted = ROW_COUNT;
        RAISE NOTICE 'Ingrédients supprimés : % (aucun fridge_item trouvé)', v_ing_deleted;
    END IF;
END;
$$;

-- 3. Désactiver les triggers pour les INSERT en masse
SET session_replication_role = replica;
