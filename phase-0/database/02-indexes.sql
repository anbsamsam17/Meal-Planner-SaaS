-- =============================================================================
-- 02-indexes.sql
-- Stratégie d'indexation — MealPlanner SaaS
-- À exécuter APRÈS 01-schema-core.sql.
-- Tous les index CONCURRENTLY sont préférables en production (pas de lock table).
-- En phase 0 (base vide), CREATE INDEX standard suffit.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- INDEX HNSW — Recherche vectorielle pgvector
-- HNSW (Hierarchical Navigable Small World) offre le meilleur compromis
-- latence/rappel pour des corpus de 50 000–500 000 vecteurs.
-- m=16 : nombre de connexions par nœud (↑m → ↑rappel mais ↑mémoire)
-- ef_construction=64 : qualité de construction (↑ef → ↑précision mais ↑temps de build)
-- Ces valeurs sont le point de départ recommandé par pgvector pour production.
-- À réévaluer via SELECT * FROM pg_vector_index_stat après 10 000+ recettes.
-- -----------------------------------------------------------------------------

CREATE INDEX idx_recipe_embeddings_hnsw
    ON recipe_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

COMMENT ON INDEX idx_recipe_embeddings_hnsw IS
    'Index HNSW pour recherche par similarité cosine (TASTE_PROFILE + WEEKLY_PLANNER). '
    'Cible : latence < 50ms sur 50 000 vecteurs avec ef_search=40 (paramètre runtime). '
    'ef_search se règle en runtime : SET LOCAL hnsw.ef_search = 80 (plans) ou 40 (feed). '
    'Ne pas mettre ef_search dans le DDL — c est un paramètre de session, pas d index.';

-- OPT #1 (review 2026-04-12) : Index GIN sur les tags dénormalisés dans recipe_embeddings.
-- Raison : le pré-filtrage "tags && ARRAY[régimes_exclus]" doit s'exécuter en index scan
-- avant que le planner déclenche le scan HNSW. Sans cet index, le filtre est séquentiel
-- sur les 50 000 lignes. Combiné à la dénormalisation dans 01-schema-core.sql,
-- réduit la latence de la query similarité de ~400ms à ~80ms (p95 estimé).
CREATE INDEX idx_recipe_embeddings_tags_gin
    ON recipe_embeddings USING gin (tags);

COMMENT ON INDEX idx_recipe_embeddings_tags_gin IS
    'OPT #1 (review 2026-04-12) : Index GIN sur les tags dénormalisés. '
    'Permet le pré-filtrage WHERE tags @> ARRAY[...] AVANT le scan HNSW. '
    'Essentiel pour que la query WEEKLY_PLANNER respecte le SLA <5s génération plan.';

-- OPT #1 (review 2026-04-12) : Index BTREE partiel sur total_time_min dénormalisé.
-- Cible la query "recettes rapides filtrées par temps" sans scan séquentiel.
-- Partiel (IS NOT NULL) car les recettes sans temps renseigné sont rares et non filtrables.
CREATE INDEX idx_recipe_embeddings_total_time
    ON recipe_embeddings (total_time_min)
    WHERE total_time_min IS NOT NULL;

COMMENT ON INDEX idx_recipe_embeddings_total_time IS
    'OPT #1 (review 2026-04-12) : Index partiel sur total_time_min dénormalisé. '
    'Permet WHERE total_time_min <= $1 en index scan avant passage au HNSW.';

-- OPT #1 (review 2026-04-12) : Index composite couvrant (tags, total_time_min) INCLUDE recipe_id.
-- Permet une stratégie deux étapes : 1) extraire les recipe_ids éligibles via cet index,
-- 2) passer ces IDs en filtre au scan HNSW avec recipe_id = ANY($filtered_ids).
-- Le INCLUDE évite un heap fetch pour recipe_id (index-only scan possible).
CREATE INDEX idx_recipe_embeddings_filter_composite
    ON recipe_embeddings (total_time_min, cuisine_type)
    INCLUDE (recipe_id)
    WHERE total_time_min IS NOT NULL;

COMMENT ON INDEX idx_recipe_embeddings_filter_composite IS
    'OPT #1 (review 2026-04-12) : Index composite hot-path pour la stratégie deux étapes. '
    'Étape 1 : SELECT recipe_id WHERE total_time_min <= $1 AND cuisine_type = $2 (index-only). '
    'Étape 2 : SELECT ... FROM recipe_embeddings WHERE recipe_id = ANY($ids) ORDER BY embedding <=> $vec. '
    'Le INCLUDE(recipe_id) permet l index-only scan évitant le heap fetch.';

-- Index HNSW sur les vecteurs de goût membres (plus petit corpus, ef_construction réduit)
CREATE INDEX idx_member_taste_vectors_hnsw
    ON member_taste_vectors
    USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 32);

COMMENT ON INDEX idx_member_taste_vectors_hnsw IS
    'Index HNSW sur les vecteurs de goût membres. Corpus petit (< 10 000 membres max). '
    'Utilisé pour trouver des membres similaires en mode "famille découverte".';

-- -----------------------------------------------------------------------------
-- INDEX BTREE — household_id (clé de tenancy)
-- Présent sur TOUTES les tables avec données utilisateur.
-- PostgreSQL peut utiliser ces index pour la RLS policy IS CURRENT_USER check.
-- -----------------------------------------------------------------------------

CREATE INDEX idx_household_members_household_id
    ON household_members (household_id);

CREATE INDEX idx_member_preferences_member_id
    ON member_preferences (member_id);

CREATE INDEX idx_recipe_feedbacks_household_id
    ON recipe_feedbacks (household_id);

CREATE INDEX idx_recipe_feedbacks_member_id
    ON recipe_feedbacks (member_id);

CREATE INDEX idx_recipe_feedbacks_recipe_id
    ON recipe_feedbacks (recipe_id);

CREATE INDEX idx_weekly_plans_household_id
    ON weekly_plans (household_id);

-- Index composite pour la requête la plus fréquente : "plan de la semaine courante du foyer"
CREATE INDEX idx_weekly_plans_household_week
    ON weekly_plans (household_id, week_start DESC);

CREATE INDEX idx_planned_meals_plan_id
    ON planned_meals (plan_id);

CREATE INDEX idx_fridge_items_household_id
    ON fridge_items (household_id);

-- Index sur expiry_date pour la requête anti-gaspi : "ingrédients qui périment bientôt"
CREATE INDEX idx_fridge_items_expiry
    ON fridge_items (household_id, expiry_date ASC NULLS LAST)
    WHERE expiry_date IS NOT NULL;

CREATE INDEX idx_weekly_books_household_id
    ON weekly_books (household_id);

-- -----------------------------------------------------------------------------
-- INDEX GIN — Recherche dans les tableaux et colonnes JSONB
-- GIN est optimal pour les opérateurs @>, ?, ?| sur JSONB et les tableaux text[].
-- -----------------------------------------------------------------------------

-- Recherche de recettes par tag : WHERE 'végétarien' = ANY(tags)
CREATE INDEX idx_recipes_tags_gin
    ON recipes USING gin (tags);

-- Recherche dans les colonnes JSONB recettes
CREATE INDEX idx_recipes_nutrition_gin
    ON recipes USING gin (nutrition jsonb_path_ops);

-- Recherche dans les préférences membres (diet_tags, allergies)
CREATE INDEX idx_member_preferences_diet_tags_gin
    ON member_preferences USING gin (diet_tags jsonb_path_ops);

CREATE INDEX idx_member_preferences_allergies_gin
    ON member_preferences USING gin (allergies jsonb_path_ops);

-- Recherche dans les items de la liste de courses
CREATE INDEX idx_shopping_lists_items_gin
    ON shopping_lists USING gin (items jsonb_path_ops);

-- -----------------------------------------------------------------------------
-- INDEX GIN trgm — Recherche full-text FR sur le titre des recettes
-- pg_trgm + GIN permet : ILIKE '%coq au vin%', similarité avec fautes de frappe.
-- Essentiel pour la barre de recherche de l'app (50 000+ recettes).
-- -----------------------------------------------------------------------------

CREATE INDEX idx_recipes_title_trgm
    ON recipes USING gin (title gin_trgm_ops);

-- Index trgm sur canonical_name des ingrédients pour la saisie frigo (autocomplétion)
CREATE INDEX idx_ingredients_canonical_name_trgm
    ON ingredients USING gin (canonical_name gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- INDEX BTREE standard — Colonnes de filtrage fréquentes sur recipes
-- -----------------------------------------------------------------------------

-- Filtrage par cuisine et difficulté (filtres UI)
CREATE INDEX idx_recipes_cuisine_difficulty
    ON recipes (cuisine_type, difficulty);

-- Filtrage par temps total (tri "recettes rapides")
CREATE INDEX idx_recipes_total_time
    ON recipes (total_time_min ASC NULLS LAST);

-- Filtrage par score qualité (pipeline RECIPE_SCOUT filtre quality_score >= 0.6)
CREATE INDEX idx_recipes_quality_score
    ON recipes (quality_score DESC);

-- slug est UNIQUE mais on ajoute un commentaire explicatif
COMMENT ON INDEX recipes_slug_key IS
    'L''unicité du slug garantit des URLs stables. Généré au moment de l''ingestion par RECIPE_SCOUT.';

-- -----------------------------------------------------------------------------
-- INDEX PARTIEL — Optimisation pour les requêtes sur sous-ensembles fréquents
-- Un index partiel est plus petit (moins de mémoire) et plus rapide qu'un index total.
-- -----------------------------------------------------------------------------

-- Plans en cours d'édition : seul le status='draft' nécessite un accès fréquent en écriture
CREATE INDEX idx_weekly_plans_draft
    ON weekly_plans (household_id, week_start)
    WHERE status = 'draft';

COMMENT ON INDEX idx_weekly_plans_draft IS
    'Index partiel : seuls les plans en cours d''édition sont ciblés. '
    'Les plans archived (majorité) sont exclus, réduisant la taille de l''index de ~80%.';

-- Livres sans notification envoyée (RETENTION_LOOP poll ce flag toutes les 4h)
CREATE INDEX idx_weekly_books_unsent_notification
    ON weekly_books (generated_at)
    WHERE notification_sent_at IS NULL;

-- Feedbacks de type 'favorited' (affichage collection coups de cœur)
CREATE INDEX idx_recipe_feedbacks_favorited
    ON recipe_feedbacks (household_id, recipe_id)
    WHERE feedback_type = 'favorited';

-- Membres avec compte Supabase Auth (exclu les membres "fantôme" enfants)
CREATE INDEX idx_household_members_with_auth
    ON household_members (supabase_user_id, household_id)
    WHERE supabase_user_id IS NOT NULL;
