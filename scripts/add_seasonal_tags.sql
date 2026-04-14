-- =============================================================================
-- add_seasonal_tags.sql
-- Ajoute des tags saisonniers aux recettes du catalogue MealPlanner SaaS
-- basés sur les ingrédients canoniques présents dans recipe_ingredients.
--
-- Saisons couvertes : hiver, printemps, ete, automne
-- Une recette peut avoir plusieurs saisons (tag ajouté pour chacune applicable).
--
-- Idempotent : un tag n'est ajouté que s'il est absent (NOT x = ANY(tags)).
-- Compatible PostgreSQL 15+ / Supabase.
--
-- Usage : exécuter directement dans Supabase SQL Editor ou via psql.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- HIVER
-- Ingrédients typiques : agneau, chou, poireau, navet, soupe, raclette, fondue
-- Recherche ILIKE pour couvrir anglais (TheMealDB) et français
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'hiver'),
    updated_at = now()
WHERE NOT ('hiver' = ANY(tags))
  AND EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          -- Viandes et protéines hivernales
          '%lamb%', '%agneau%',
          '%mutton%', '%mouton%',
          '%venison%', '%gibier%',
          -- Légumes racines et crucifères d'hiver
          '%cabbage%', '%chou%',
          '%leek%', '%poireau%',
          '%turnip%', '%navet%',
          '%parsnip%', '%panais%',
          '%kale%', '%chou frisé%',
          '%brussels sprout%', '%chou de bruxelles%',
          '%beetroot%', '%betterave%',
          -- Cucurbitacées et légumineuses d'hiver
          '%lentil%', '%lentille%',
          -- Plats chauds emblématiques
          '%raclette%',
          '%fondue%'
      ])
  );

-- Recettes dont le titre contient des mots-clés hivernaux (soupe, potage, etc.)
UPDATE recipes r
SET tags = array_append(tags, 'hiver'),
    updated_at = now()
WHERE NOT ('hiver' = ANY(tags))
  AND (
    r.title ILIKE '%soup%'
    OR r.title ILIKE '%soupe%'
    OR r.title ILIKE '%potage%'
    OR r.title ILIKE '%stew%'
    OR r.title ILIKE '%ragoût%'
    OR r.title ILIKE '%raclette%'
    OR r.title ILIKE '%fondue%'
    OR r.title ILIKE '%hotpot%'
    OR r.title ILIKE '%chili%'
  );

-- -----------------------------------------------------------------------------
-- PRINTEMPS
-- Ingrédients typiques : asperge, petit pois, fraise, radis, salade
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'printemps'),
    updated_at = now()
WHERE NOT ('printemps' = ANY(tags))
  AND EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          '%asparagus%', '%asperge%',
          '%pea%', '%petit pois%',
          '%spring pea%',
          '%strawberr%', '%fraise%',
          '%radish%', '%radis%',
          '%artichoke%', '%artichaut%',
          '%spinach%', '%épinard%',
          '%rhubarb%', '%rhubarbe%',
          '%spring onion%', '%oignon nouveau%',
          '%new potato%', '%pomme de terre nouvelle%',
          '%broad bean%', '%fève%',
          '%fennel%', '%fenouil%'
      ])
  );

-- Recettes dont le titre contient des mots-clés printaniers
UPDATE recipes r
SET tags = array_append(tags, 'printemps'),
    updated_at = now()
WHERE NOT ('printemps' = ANY(tags))
  AND (
    r.title ILIKE '%spring%'
    OR r.title ILIKE '%primavera%'
    OR r.title ILIKE '%asperge%'
    OR r.title ILIKE '%asparagus%'
  );

-- -----------------------------------------------------------------------------
-- ETE
-- Ingrédients typiques : tomate, courgette, aubergine, melon, barbecue, salade, gazpacho
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'ete'),
    updated_at = now()
WHERE NOT ('ete' = ANY(tags))
  AND EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          '%tomato%', '%tomate%',
          '%courgette%', '%zucchini%',
          '%aubergine%', '%eggplant%',
          '%melon%',
          '%watermelon%', '%pastèque%',
          '%peach%', '%pêche%',
          '%nectarine%',
          '%corn%', '%maïs%',
          '%cucumber%', '%concombre%',
          '%pepper%', '%poivron%',
          '%basil%', '%basilic%',
          '%mint%', '%menthe%',
          '%apricot%', '%abricot%',
          '%cherry%', '%cerise%',
          '%raspberry%', '%framboise%'
      ])
  );

-- Recettes dont le titre contient des mots-clés estivaux
UPDATE recipes r
SET tags = array_append(tags, 'ete'),
    updated_at = now()
WHERE NOT ('ete' = ANY(tags))
  AND (
    r.title ILIKE '%barbecue%'
    OR r.title ILIKE '%bbq%'
    OR r.title ILIKE '%salade%'
    OR r.title ILIKE '%salad%'
    OR r.title ILIKE '%gazpacho%'
    OR r.title ILIKE '%grillé%'
    OR r.title ILIKE '%grilled%'
    OR r.title ILIKE '%summer%'
    OR r.title ILIKE '%été%'
  );

-- -----------------------------------------------------------------------------
-- AUTOMNE
-- Ingrédients typiques : potiron, champignon, châtaigne, pomme, courge
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'automne'),
    updated_at = now()
WHERE NOT ('automne' = ANY(tags))
  AND EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          '%pumpkin%', '%potiron%',
          '%squash%', '%courge%',
          '%butternut%',
          '%mushroom%', '%champignon%',
          '%chestnut%', '%châtaigne%',
          '%apple%', '%pomme%',
          '%pear%', '%poire%',
          '%grape%', '%raisin%',
          '%fig%', '%figue%',
          '%quince%', '%coing%',
          '%walnut%', '%noix%',
          '%hazelnut%', '%noisette%',
          '%sweet potato%', '%patate douce%',
          '%parsnip%', '%panais%',
          '%celeriac%', '%céleri-rave%',
          '%truffle%', '%truffe%'
      ])
  );

-- Recettes dont le titre contient des mots-clés automnaux
UPDATE recipes r
SET tags = array_append(tags, 'automne'),
    updated_at = now()
WHERE NOT ('automne' = ANY(tags))
  AND (
    r.title ILIKE '%pumpkin%'
    OR r.title ILIKE '%potiron%'
    OR r.title ILIKE '%mushroom%'
    OR r.title ILIKE '%champignon%'
    OR r.title ILIKE '%autumn%'
    OR r.title ILIKE '%fall%'
    OR r.title ILIKE '%harvest%'
    OR r.title ILIKE '%butternut%'
  );

-- =============================================================================
-- RAPPORT DE RÉSULTATS
-- Affiche le nombre de recettes par tag saisonnier après mise à jour
-- =============================================================================
SELECT
    tag,
    COUNT(*) AS nb_recettes
FROM recipes, UNNEST(tags) AS tag
WHERE tag IN ('hiver', 'printemps', 'ete', 'automne')
GROUP BY tag
ORDER BY tag;
