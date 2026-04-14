-- =============================================================================
-- add_diet_budget_tags.sql
-- Ajoute des tags régime et budget aux recettes du catalogue MealPlanner SaaS
-- en analysant les ingrédients canoniques via recipe_ingredients.
--
-- Tags régime couverts   : végétarien, vegan, sans-porc, halal
-- Tags budget couverts   : économique, moyen, premium
--
-- Logique :
--   - végétarien = sans viande ni poisson (liste ILIKE exhaustive)
--   - vegan      = végétarien + sans produits animaux (oeufs, lait, beurre, etc.)
--   - sans-porc  = sans porc, bacon, jambon, lard, saucisse de porc
--   - halal      = sans-porc + sans alcool dans les ingrédients
--   - économique = nb ingrédients <= 6 ET difficulty <= 2
--   - moyen      = 7 à 10 ingrédients
--   - premium    = > 10 ingrédients OU difficulty >= 4
--
-- Idempotent : chaque UPDATE vérifie NOT (tag = ANY(tags)).
-- Ordre d'application : végétarien → vegan → sans-porc → halal → budget.
-- Compatible PostgreSQL 15+ / Supabase.
-- =============================================================================


-- =============================================================================
-- BLOC 1 : Comptage initial (audit avant modification)
-- =============================================================================

-- (Décommenter pour vérification avant exécution)
-- SELECT COUNT(*) AS total_recipes FROM recipes;
-- SELECT UNNEST(tags) AS tag, COUNT(*) FROM recipes GROUP BY tag ORDER BY tag;


-- =============================================================================
-- BLOC 2 : TAGS RÉGIME
-- =============================================================================

-- -----------------------------------------------------------------------------
-- CTE : ingrédients de viande / poisson / produits animaux
-- Centralisés pour être réutilisés dans plusieurs blocs UPDATE.
-- -----------------------------------------------------------------------------

-- VEGETARIEN
-- Logique d'exclusion : une recette est végétarienne si AUCUN de ses ingrédients
-- ne fait partie de la liste des viandes et poissons.
UPDATE recipes r
SET tags = array_append(tags, 'végétarien'),
    updated_at = now()
WHERE NOT ('végétarien' = ANY(tags))
  AND NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          -- Viandes rouges et blanches
          '%beef%', '%boeuf%', '%veal%', '%veau%',
          '%pork%', '%porc%', '%pig%',
          '%lamb%', '%agneau%', '%mutton%', '%mouton%',
          '%chicken%', '%poulet%', '%turkey%', '%dinde%',
          '%duck%', '%canard%', '%goose%', '%oie%',
          '%rabbit%', '%lapin%', '%venison%', '%gibier%',
          '%ham%', '%jambon%', '%bacon%', '%lard%',
          '%sausage%', '%saucisse%', '%salami%', '%chorizo%',
          '%mince%', '%haché%', '%steak%',
          '%prosciutto%', '%pancetta%', '%mortadella%',
          -- Abats
          '%liver%', '%foie%', '%kidney%', '%rognon%',
          '%tripe%', '%triperie%',
          -- Poissons et fruits de mer
          '%fish%', '%poisson%',
          '%salmon%', '%saumon%', '%tuna%', '%thon%',
          '%cod%', '%cabillaud%', '%haddock%',
          '%shrimp%', '%crevette%', '%prawn%',
          '%lobster%', '%homard%', '%crab%', '%crabe%',
          '%oyster%', '%huître%', '%mussel%', '%moule%',
          '%clam%', '%palourde%', '%scallop%', '%coquille%',
          '%anchovy%', '%anchois%', '%sardine%',
          '%squid%', '%calamari%', '%calmar%',
          '%octopus%', '%pieuvre%',
          -- Bouillons et gélatines animaux
          '%beef stock%', '%chicken stock%', '%fish stock%',
          '%bouillon de boeuf%', '%bouillon de poulet%',
          '%gelatin%', '%gélatine%'
      ])
  );

-- -----------------------------------------------------------------------------
-- VEGAN
-- Végétarien + sans produits d'origine animale (lait, oeufs, beurre, crème, fromage, miel)
-- Un tag 'vegan' n'a de sens que si la recette est aussi végétarienne.
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'vegan'),
    updated_at = now()
WHERE NOT ('vegan' = ANY(tags))
  AND 'végétarien' = ANY(tags)
  AND NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          -- Oeufs
          '%egg%', '%oeuf%',
          -- Produits laitiers
          '%milk%', '%lait%',
          '%butter%', '%beurre%',
          '%cream%', '%crème%',
          '%cheese%', '%fromage%',
          '%yogurt%', '%yaourt%', '%yoghurt%',
          '%ghee%',
          -- Miel et dérivés
          '%honey%', '%miel%',
          '%beeswax%',
          -- Gélatine (déjà exclue par végétarien, mais doublon de sécurité)
          '%gelatin%', '%gélatine%',
          -- Parmesan, ricotta, mascarpone, feta, mozzarella...
          '%parmesan%', '%ricotta%', '%mascarpone%',
          '%feta%', '%mozzarella%', '%cheddar%',
          '%brie%', '%camembert%', '%gruyere%', '%gruyère%'
      ])
  );

-- -----------------------------------------------------------------------------
-- SANS-PORC
-- Recettes sans porc, bacon, jambon, lard, saucisse de porc, pancetta, etc.
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'sans-porc'),
    updated_at = now()
WHERE NOT ('sans-porc' = ANY(tags))
  AND NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          '%pork%', '%porc%',
          '%pig%', '%cochon%',
          '%bacon%',
          '%ham%', '%jambon%',
          '%lard%', '%lardon%',
          '%sausage%', '%saucisse%',
          '%chorizo%',
          '%salami%',
          '%pancetta%',
          '%prosciutto%',
          '%mortadella%',
          '%spare rib%', '%travers%',
          '%gammon%',
          '%pork belly%', '%poitrine de porc%',
          '%pork chop%', '%côtelette%',
          '%pork mince%', '%haché de porc%'
      ])
  );

-- -----------------------------------------------------------------------------
-- HALAL
-- Sans-porc + sans alcool dans les ingrédients (vin, bière, alcool de cuisine)
-- IMPORTANT : halal est une approximation ; seule une certification officielle
-- garantit le statut halal. Ce tag indique l'absence de porc et d'alcool visible.
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'halal'),
    updated_at = now()
WHERE NOT ('halal' = ANY(tags))
  AND 'sans-porc' = ANY(tags)
  AND NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          '%wine%', '%vin%',
          '%beer%', '%bière%', '%biere%',
          '%rum%', '%rhum%',
          '%vodka%',
          '%whisky%', '%whiskey%',
          '%brandy%', '%cognac%',
          '%champagne%',
          '%sake%',
          '%cider%', '%cidre%',
          '%sherry%', '%xeres%',
          '%port%', '%porto%',
          '%vermouth%',
          '%liqueur%',
          '%kirsch%',
          '%calvados%',
          '%armagnac%',
          '%marsala%',
          '%mirin%'
      ])
  );


-- =============================================================================
-- BLOC 3 : TAGS BUDGET
-- Basé sur le nombre d'ingrédients (JOIN COUNT) et le niveau de difficulté.
-- =============================================================================

-- Sous-requête réutilisable : nombre d'ingrédients par recette
-- Matérialisée ici via CTE dans chaque UPDATE pour lisibilité.

-- -----------------------------------------------------------------------------
-- ECONOMIQUE : <= 6 ingrédients ET difficulty <= 2
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'économique'),
    updated_at = now()
WHERE NOT ('économique' = ANY(tags))
  AND COALESCE(r.difficulty, 2) <= 2
  AND (
    SELECT COUNT(*)
    FROM recipe_ingredients ri
    WHERE ri.recipe_id = r.id
  ) <= 6;

-- -----------------------------------------------------------------------------
-- MOYEN : 7 à 10 ingrédients (indépendant de la difficulté)
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'moyen'),
    updated_at = now()
WHERE NOT ('moyen' = ANY(tags))
  AND (
    SELECT COUNT(*)
    FROM recipe_ingredients ri
    WHERE ri.recipe_id = r.id
  ) BETWEEN 7 AND 10;

-- -----------------------------------------------------------------------------
-- PREMIUM : > 10 ingrédients OU difficulty >= 4
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'premium'),
    updated_at = now()
WHERE NOT ('premium' = ANY(tags))
  AND (
    COALESCE(r.difficulty, 1) >= 4
    OR (
      SELECT COUNT(*)
      FROM recipe_ingredients ri
      WHERE ri.recipe_id = r.id
    ) > 10
  );

-- =============================================================================
-- RAPPORT DE RÉSULTATS
-- =============================================================================
SELECT
    tag,
    COUNT(*) AS nb_recettes
FROM recipes, UNNEST(tags) AS tag
WHERE tag IN (
    'végétarien', 'vegan', 'sans-porc', 'halal',
    'économique', 'moyen', 'premium'
)
GROUP BY tag
ORDER BY tag;
