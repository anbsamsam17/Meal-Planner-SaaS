-- =============================================================================
-- add_missing_tags.sql
-- Ajoute les tags manquants aux recettes du catalogue MealPlanner SaaS :
--   1. Restrictions alimentaires : sans-gluten, sans-lactose,
--      sans-fruits-de-mer, sans-fruits-à-coque
--   2. Catégories de plat : dessert, plat, entrée, accompagnement, petit-déjeuner
--
-- Complète add_diet_budget_tags.sql (végétarien, vegan, sans-porc, halal, budget)
-- et add_seasonal_tags.sql (saisons).
--
-- Idempotent : chaque UPDATE vérifie NOT (tag = ANY(tags)).
-- Compatible PostgreSQL 15+ / Supabase.
-- =============================================================================


-- =============================================================================
-- BLOC 1 : RESTRICTIONS ALIMENTAIRES MANQUANTES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- SANS-GLUTEN
-- Exclusion des ingrédients contenant du gluten (blé, orge, seigle, avoine,
-- pâtes, pain, farine, couscous, semoule, bière, etc.)
-- Une recette est sans-gluten si AUCUN ingrédient n'est à base de gluten.
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'sans-gluten'),
    updated_at = now()
WHERE NOT ('sans-gluten' = ANY(tags))
  AND NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          -- Céréales contenant du gluten
          '%wheat%', '%blé%', '%ble%',
          '%barley%', '%orge%',
          '%rye%', '%seigle%',
          '%oat%', '%avoine%',
          '%spelt%', '%épeautre%',
          -- Produits transformés à base de gluten
          '%flour%', '%farine%',
          '%pasta%', '%pâte%', '%pate%',
          '%noodle%', '%nouille%',
          '%bread%', '%pain%',
          '%couscous%',
          '%semolina%', '%semoule%',
          '%cracker%', '%biscuit%',
          '%croûton%', '%crouton%',
          '%panko%', '%chapelure%',
          '%pizza%',
          '%tortilla%', '%wrap%',
          '%soy sauce%', '%sauce soja%',
          '%beer%', '%bière%', '%biere%',
          -- Pâtisserie
          '%cake%', '%gâteau%', '%gateau%',
          '%pastry%', '%pâtisserie%',
          '%pie crust%', '%pâte brisée%',
          '%puff pastry%', '%pâte feuilletée%'
      ])
  );

-- -----------------------------------------------------------------------------
-- SANS-LACTOSE
-- Exclusion des produits laitiers (lait, beurre, crème, fromage, yaourt, etc.)
-- Note : le tag vegan implique déjà sans-lactose, mais on le pose aussi
-- sur les recettes non-vegan qui n'ont simplement pas de lactose.
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'sans-lactose'),
    updated_at = now()
WHERE NOT ('sans-lactose' = ANY(tags))
  AND NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          '%milk%', '%lait%',
          '%butter%', '%beurre%',
          '%cream%', '%crème%', '%creme%',
          '%cheese%', '%fromage%',
          '%yogurt%', '%yaourt%', '%yoghurt%',
          '%ghee%',
          '%whey%', '%lactosérum%',
          '%ricotta%', '%mascarpone%',
          '%parmesan%', '%mozzarella%', '%cheddar%',
          '%feta%', '%brie%', '%camembert%',
          '%gruyere%', '%gruyère%',
          '%crème fraîche%', '%creme fraiche%',
          '%sour cream%',
          '%ice cream%', '%glace%',
          '%custard%'
      ])
  );

-- -----------------------------------------------------------------------------
-- SANS-FRUITS-DE-MER
-- Exclusion des fruits de mer (crevettes, moules, huîtres, crabe, etc.)
-- Le poisson seul n'est PAS un fruit de mer dans cette classification.
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'sans-fruits-de-mer'),
    updated_at = now()
WHERE NOT ('sans-fruits-de-mer' = ANY(tags))
  AND NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          '%shrimp%', '%crevette%', '%prawn%',
          '%lobster%', '%homard%',
          '%crab%', '%crabe%',
          '%oyster%', '%huître%', '%huitre%',
          '%mussel%', '%moule%',
          '%clam%', '%palourde%',
          '%scallop%', '%coquille%', '%saint-jacques%',
          '%squid%', '%calamari%', '%calmar%',
          '%octopus%', '%pieuvre%', '%poulpe%',
          '%seafood%', '%fruits de mer%',
          '%langoustine%', '%écrevisse%',
          '%cockle%', '%coque%',
          '%sea urchin%', '%oursin%',
          '%abalone%', '%ormeau%',
          '%whelk%', '%bulot%'
      ])
  );

-- -----------------------------------------------------------------------------
-- SANS-FRUITS-À-COQUE
-- Exclusion des fruits à coque (noix, amandes, noisettes, cacahuètes, etc.)
-- Important pour les allergies sévères.
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'sans-fruits-à-coque'),
    updated_at = now()
WHERE NOT ('sans-fruits-à-coque' = ANY(tags))
  AND NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id
      AND i.canonical_name ILIKE ANY (ARRAY[
          '%walnut%', '%noix%',
          '%almond%', '%amande%',
          '%hazelnut%', '%noisette%',
          '%cashew%', '%cajou%',
          '%pistachio%', '%pistache%',
          '%pecan%', '%pécan%', '%pecan%',
          '%macadamia%',
          '%brazil nut%', '%noix du brésil%',
          '%pine nut%', '%pignon%',
          '%chestnut%', '%châtaigne%', '%marron%',
          '%peanut%', '%cacahuète%', '%arachide%',
          '%praline%', '%praliné%',
          '%marzipan%', '%massepain%', '%pâte d''amande%',
          '%nutella%',
          '%tahini%', '%sésame%', '%sesame%'
      ])
  );


-- =============================================================================
-- BLOC 2 : CATÉGORIES DE PLAT
-- Basé sur le titre de la recette, les ingrédients et des heuristiques.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- DESSERT
-- Détection par titre (cake, gâteau, tarte sucrée, mousse, tiramisu, etc.)
-- et par ingrédients typiques (sucre + chocolat, fruits + crème, etc.)
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'dessert'),
    updated_at = now()
WHERE NOT ('dessert' = ANY(tags))
  AND (
    -- Titre contient un mot-clé dessert
    r.title ILIKE ANY (ARRAY[
        '%cake%', '%gâteau%', '%gateau%',
        '%tart%', '%tarte%',
        '%pie%',
        '%cookie%', '%biscuit%',
        '%brownie%',
        '%mousse%',
        '%tiramisu%',
        '%crème brûlée%', '%creme brulee%',
        '%pudding%',
        '%ice cream%', '%glace%', '%sorbet%',
        '%macaron%',
        '%muffin%', '%cupcake%',
        '%cheesecake%',
        '%crumble%',
        '%flan%',
        '%panna cotta%',
        '%profiterole%', '%éclair%',
        '%fondant%',
        '%clafoutis%',
        '%compote%',
        '%crêpe%', '%crepe%', '%pancake%',
        '%waffle%', '%gaufre%',
        '%chocolat%', '%chocolate%',
        '%dessert%',
        '%sweet%', '%sucré%'
    ])
    -- OU la recette a beaucoup de sucre/chocolat et pas de viande
    OR (
      EXISTS (
        SELECT 1
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = r.id
          AND i.canonical_name ILIKE ANY (ARRAY[
              '%chocolate%', '%chocolat%',
              '%cocoa%', '%cacao%',
              '%vanilla extract%', '%extrait de vanille%',
              '%icing sugar%', '%sucre glace%'
          ])
      )
      AND NOT EXISTS (
        SELECT 1
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = r.id
          AND i.canonical_name ILIKE ANY (ARRAY[
              '%beef%', '%chicken%', '%pork%', '%fish%', '%lamb%',
              '%boeuf%', '%poulet%', '%porc%', '%poisson%', '%agneau%'
          ])
      )
    )
  );

-- -----------------------------------------------------------------------------
-- ENTRÉE
-- Détection par titre (salade, soupe, velouté, bruschetta, etc.)
-- et par caractéristiques (peu d'ingrédients + temps court + pas dessert)
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'entrée'),
    updated_at = now()
WHERE NOT ('entrée' = ANY(tags))
  AND NOT ('dessert' = ANY(tags))
  AND (
    r.title ILIKE ANY (ARRAY[
        '%salad%', '%salade%',
        '%soup%', '%soupe%', '%potage%', '%velouté%',
        '%bruschetta%',
        '%carpaccio%',
        '%tartare%',
        '%ceviche%',
        '%terrine%',
        '%gazpacho%',
        '%antipasti%',
        '%hummus%', '%houmous%',
        '%guacamole%',
        '%starter%', '%entrée%', '%entree%'
    ])
  );

-- -----------------------------------------------------------------------------
-- ACCOMPAGNEMENT
-- Détection par titre (purée, gratin, riz, frites, légumes rôtis, etc.)
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'accompagnement'),
    updated_at = now()
WHERE NOT ('accompagnement' = ANY(tags))
  AND NOT ('dessert' = ANY(tags))
  AND NOT ('entrée' = ANY(tags))
  AND (
    r.title ILIKE ANY (ARRAY[
        '%purée%', '%puree%', '%mash%',
        '%gratin%',
        '%frites%', '%fries%',
        '%rice%', '%riz%',
        '%roasted vegetables%', '%légumes rôtis%',
        '%coleslaw%',
        '%ratatouille%',
        '%side dish%', '%accompagnement%',
        '%pilaf%', '%risotto%',
        '%polenta%',
        '%tabbouleh%', '%taboulé%'
    ])
  );

-- -----------------------------------------------------------------------------
-- PETIT-DÉJEUNER
-- Détection par titre (porridge, smoothie, granola, omelette, toast, etc.)
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'petit-déjeuner'),
    updated_at = now()
WHERE NOT ('petit-déjeuner' = ANY(tags))
  AND (
    r.title ILIKE ANY (ARRAY[
        '%porridge%',
        '%smoothie%',
        '%granola%',
        '%muesli%',
        '%omelette%', '%omelet%',
        '%toast%', '%tartine%',
        '%scrambled%', '%brouillé%',
        '%pancake%', '%crêpe%', '%crepe%',
        '%waffle%', '%gaufre%',
        '%breakfast%', '%petit-déjeuner%', '%petit déjeuner%',
        '%brunch%',
        '%french toast%', '%pain perdu%',
        '%açaí%', '%acai%',
        '%overnight oats%'
    ])
  );

-- -----------------------------------------------------------------------------
-- PLAT (principal)
-- Tout ce qui n'est pas dessert, entrée, accompagnement ou petit-déjeuner
-- et qui contient une protéine principale.
-- -----------------------------------------------------------------------------
UPDATE recipes r
SET tags = array_append(tags, 'plat'),
    updated_at = now()
WHERE NOT ('plat' = ANY(tags))
  AND NOT ('dessert' = ANY(tags))
  AND NOT ('entrée' = ANY(tags))
  AND NOT ('accompagnement' = ANY(tags))
  AND NOT ('petit-déjeuner' = ANY(tags))
  AND (
    -- A une protéine principale
    EXISTS (
      SELECT 1
      FROM recipe_ingredients ri
      JOIN ingredients i ON i.id = ri.ingredient_id
      WHERE ri.recipe_id = r.id
        AND i.canonical_name ILIKE ANY (ARRAY[
            '%chicken%', '%poulet%',
            '%beef%', '%boeuf%',
            '%pork%', '%porc%',
            '%lamb%', '%agneau%',
            '%fish%', '%poisson%',
            '%salmon%', '%saumon%',
            '%tuna%', '%thon%',
            '%turkey%', '%dinde%',
            '%duck%', '%canard%',
            '%tofu%', '%tempeh%', '%seitan%',
            '%lentil%', '%lentille%',
            '%chickpea%', '%pois chiche%',
            '%bean%', '%haricot%'
        ])
    )
    -- OU titre contient un mot-clé plat principal
    OR r.title ILIKE ANY (ARRAY[
        '%curry%',
        '%stew%', '%ragoût%',
        '%roast%', '%rôti%',
        '%burger%',
        '%lasagna%', '%lasagne%',
        '%tagine%', '%tajine%',
        '%stir fry%', '%wok%',
        '%casserole%',
        '%grillé%', '%grilled%',
        '%bolognese%', '%bolognaise%',
        '%carbonara%',
        '%paella%',
        '%biryani%',
        '%coq au vin%',
        '%pot-au-feu%',
        '%blanquette%',
        '%bourguignon%'
    ])
  );


-- =============================================================================
-- BLOC 3 : NETTOYAGE — Supprimer les anciens tags préfixés du recipe_scout
-- Les tags "regime:xxx", "occasion:xxx", "budget:xxx" ne sont pas matchés
-- par les filtres frontend. On les remplace par leurs versions nues.
-- =============================================================================

-- Remplacer "regime:vegan" → "vegan", "regime:végétarien" → "végétarien", etc.
UPDATE recipes
SET tags = array_remove(tags, 'regime:vegan') || CASE WHEN NOT ('vegan' = ANY(tags)) THEN ARRAY['vegan'] ELSE '{}' END,
    updated_at = now()
WHERE 'regime:vegan' = ANY(tags);

UPDATE recipes
SET tags = array_remove(tags, 'regime:végétarien') || CASE WHEN NOT ('végétarien' = ANY(tags)) THEN ARRAY['végétarien'] ELSE '{}' END,
    updated_at = now()
WHERE 'regime:végétarien' = ANY(tags);

UPDATE recipes
SET tags = array_remove(tags, 'regime:sans_gluten') || CASE WHEN NOT ('sans-gluten' = ANY(tags)) THEN ARRAY['sans-gluten'] ELSE '{}' END,
    updated_at = now()
WHERE 'regime:sans_gluten' = ANY(tags);

UPDATE recipes
SET tags = array_remove(tags, 'regime:sans_lactose') || CASE WHEN NOT ('sans-lactose' = ANY(tags)) THEN ARRAY['sans-lactose'] ELSE '{}' END,
    updated_at = now()
WHERE 'regime:sans_lactose' = ANY(tags);

UPDATE recipes
SET tags = array_remove(tags, 'regime:sans_porc') || CASE WHEN NOT ('sans-porc' = ANY(tags)) THEN ARRAY['sans-porc'] ELSE '{}' END,
    updated_at = now()
WHERE 'regime:sans_porc' = ANY(tags);

UPDATE recipes
SET tags = array_remove(tags, 'regime:halal') || CASE WHEN NOT ('halal' = ANY(tags)) THEN ARRAY['halal'] ELSE '{}' END,
    updated_at = now()
WHERE 'regime:halal' = ANY(tags);

UPDATE recipes
SET tags = array_remove(tags, 'regime:sans_noix') || CASE WHEN NOT ('sans-fruits-à-coque' = ANY(tags)) THEN ARRAY['sans-fruits-à-coque'] ELSE '{}' END,
    updated_at = now()
WHERE 'regime:sans_noix' = ANY(tags);

-- Remplacer "occasion:dessert" → "dessert", etc.
UPDATE recipes
SET tags = array_remove(tags, 'occasion:dessert') || CASE WHEN NOT ('dessert' = ANY(tags)) THEN ARRAY['dessert'] ELSE '{}' END,
    updated_at = now()
WHERE 'occasion:dessert' = ANY(tags);

UPDATE recipes
SET tags = array_remove(tags, 'occasion:entrée') || CASE WHEN NOT ('entrée' = ANY(tags)) THEN ARRAY['entrée'] ELSE '{}' END,
    updated_at = now()
WHERE 'occasion:entrée' = ANY(tags);

UPDATE recipes
SET tags = array_remove(tags, 'occasion:plat_principal') || CASE WHEN NOT ('plat' = ANY(tags)) THEN ARRAY['plat'] ELSE '{}' END,
    updated_at = now()
WHERE 'occasion:plat_principal' = ANY(tags);

-- Remplacer "budget:xxx" → "xxx"
UPDATE recipes
SET tags = array_remove(tags, 'budget:économique') || CASE WHEN NOT ('économique' = ANY(tags)) THEN ARRAY['économique'] ELSE '{}' END,
    updated_at = now()
WHERE 'budget:économique' = ANY(tags);

UPDATE recipes
SET tags = array_remove(tags, 'budget:moyen') || CASE WHEN NOT ('moyen' = ANY(tags)) THEN ARRAY['moyen'] ELSE '{}' END,
    updated_at = now()
WHERE 'budget:moyen' = ANY(tags);

UPDATE recipes
SET tags = array_remove(tags, 'budget:premium') || CASE WHEN NOT ('premium' = ANY(tags)) THEN ARRAY['premium'] ELSE '{}' END,
    updated_at = now()
WHERE 'budget:premium' = ANY(tags);


-- =============================================================================
-- RAPPORT DE RÉSULTATS
-- =============================================================================
SELECT
    tag,
    COUNT(*) AS nb_recettes
FROM recipes, UNNEST(tags) AS tag
WHERE tag IN (
    'sans-gluten', 'sans-lactose', 'sans-fruits-de-mer', 'sans-fruits-à-coque',
    'dessert', 'plat', 'entrée', 'accompagnement', 'petit-déjeuner',
    'végétarien', 'vegan', 'sans-porc', 'halal',
    'économique', 'moyen', 'premium'
)
GROUP BY tag
ORDER BY tag;
