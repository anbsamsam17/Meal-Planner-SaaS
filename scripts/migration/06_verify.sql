-- =============================================================================
-- FICHIER 06/06 — RESET ET VÉRIFICATION FINALE
-- Exécuter EN DERNIER, après tous les fichiers de migration.
-- =============================================================================

-- =============================================================================
-- Fin du script de migration
-- =============================================================================
-- Restaurer le comportement normal des triggers
RESET session_replication_role;

-- Vérifications post-import (optionnel — exécuter après l'import)
SELECT 'ingredients' AS table_name, COUNT(*) AS rows FROM public.ingredients
UNION ALL SELECT 'recipes', COUNT(*) FROM public.recipes
UNION ALL SELECT 'recipe_ingredients', COUNT(*) FROM public.recipe_ingredients
UNION ALL SELECT 'recipe_embeddings', COUNT(*) FROM public.recipe_embeddings;
-- Résultats attendus : 1000 / 338 / 2670 / 305
