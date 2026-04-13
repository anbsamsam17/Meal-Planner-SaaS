-- =============================================================================
-- 07-seed-data.sql
-- Données de seed — MealPlanner SaaS
-- À utiliser UNIQUEMENT en environnement dev/staging.
-- Ne JAMAIS exécuter en production (le trigger de qualité bloquera les recettes
-- avec quality_score < 0.6, et les données de test polluent la prod).
--
-- Ce seed crée :
--   - 10 ingrédients canoniques de base
--   - 1 household de test
--   - 1 membre owner de test
--   - 3 recettes d'exemple avec embeddings factices (vecteurs zéro)
-- =============================================================================

-- Désactiver les triggers de validation pendant le seed dev
-- (les recettes seed ont un quality_score valide mais les embeddings sont factices)
SET session_replication_role = replica;

-- -----------------------------------------------------------------------------
-- INGRÉDIENTS CANONIQUES
-- Ces 10 ingrédients couvrent les recettes seed et servent de base
-- pour tester l'autocomplétion et le mapping Open Food Facts (Phase 4).
-- -----------------------------------------------------------------------------

INSERT INTO ingredients (id, canonical_name, category, unit_default, off_id) VALUES
    ('a1000000-0000-0000-0000-000000000001', 'carotte',          'légume',          'g',     NULL),
    ('a1000000-0000-0000-0000-000000000002', 'oignon',           'légume',          'pièce', NULL),
    ('a1000000-0000-0000-0000-000000000003', 'pomme de terre',   'légume',          'g',     NULL),
    ('a1000000-0000-0000-0000-000000000004', 'poulet',           'viande',          'g',     NULL),
    ('a1000000-0000-0000-0000-000000000005', 'pâtes',            'épicerie',        'g',     NULL),
    ('a1000000-0000-0000-0000-000000000006', 'tomate',           'légume',          'g',     NULL),
    ('a1000000-0000-0000-0000-000000000007', 'ail',              'condiment',       'g',     NULL),
    ('a1000000-0000-0000-0000-000000000008', 'huile d''olive',   'matière-grasse',  'ml',    NULL),
    ('a1000000-0000-0000-0000-000000000009', 'sel',              'condiment',       'g',     NULL),
    ('a1000000-0000-0000-0000-000000000010', 'poivre noir',      'condiment',       'g',     NULL)
ON CONFLICT (canonical_name) DO NOTHING;

-- -----------------------------------------------------------------------------
-- HOUSEHOLD DE TEST
-- UUID prévisible pour faciliter les tests (pas aléatoire).
-- -----------------------------------------------------------------------------

INSERT INTO households (id, name, plan, created_at) VALUES
    ('b1000000-0000-0000-0000-000000000001', 'Famille Test', 'famille', now())
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- MEMBRE OWNER DE TEST
-- supabase_user_id correspond à l'UUID qu'on configure dans les tests d'intégration.
-- En dev local avec Supabase CLI, créer d'abord l'utilisateur dans auth.users.
-- -----------------------------------------------------------------------------

INSERT INTO household_members (
    id, household_id, supabase_user_id, role, display_name, birth_date, is_child
) VALUES
    (
        'c1000000-0000-0000-0000-000000000001',
        'b1000000-0000-0000-0000-000000000001',
        'd1000000-0000-0000-0000-000000000001',  -- Correspond à un utilisateur test Supabase Auth
        'owner',
        'Alice (Test)',
        '1990-03-15',
        false
    )
ON CONFLICT DO NOTHING;

-- Préférences du membre test
INSERT INTO member_preferences (
    id, member_id, diet_tags, allergies, dislikes, cooking_time_max, budget_pref
) VALUES
    (
        'e1000000-0000-0000-0000-000000000001',
        'c1000000-0000-0000-0000-000000000001',
        '[]'::jsonb,
        '[]'::jsonb,
        '["céleri"]'::jsonb,
        45,
        'moyen'
    )
ON CONFLICT (member_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- RECETTES D'EXEMPLE
-- 3 recettes avec quality_score >= 0.6 pour passer la validation trigger.
-- Les instructions sont en JSONB structuré pour correspondre au schéma attendu.
-- -----------------------------------------------------------------------------

-- Recette 1 : Poulet rôti classique
INSERT INTO recipes (
    id, source, source_url, title, slug, description,
    instructions, servings, prep_time_min, cook_time_min,
    difficulty, cuisine_type, photo_url, nutrition, tags, quality_score
) VALUES (
    'f1000000-0000-0000-0000-000000000001',
    'seed',
    NULL,
    'Poulet rôti aux herbes de Provence',
    'poulet-roti-aux-herbes-de-provence',
    'Le grand classique familial : un poulet doré et parfumé, idéal pour le dimanche.',
    '[
        {"step": 1, "text": "Préchauffer le four à 200°C.", "duration_min": 10},
        {"step": 2, "text": "Frotter le poulet avec de l''huile d''olive, du sel, du poivre et les herbes de Provence.", "duration_min": 5},
        {"step": 3, "text": "Disposer dans un plat allant au four avec les carottes et les pommes de terre en morceaux.", "duration_min": 5},
        {"step": 4, "text": "Enfourner 1h15 en arrosant toutes les 20 minutes.", "duration_min": 75}
    ]'::jsonb,
    4,
    20,
    75,
    1,
    'française',
    NULL,
    '{"calories": 420, "proteins_g": 38, "carbs_g": 22, "fat_g": 18}'::jsonb,
    ARRAY['volaille', 'four', 'classique', 'dimanche', 'sans-gluten'],
    0.85
),

-- Recette 2 : Pâtes à la bolognaise simple
(
    'f1000000-0000-0000-0000-000000000002',
    'seed',
    NULL,
    'Pâtes bolognaise maison',
    'pates-bolognaise-maison',
    'Une bolognaise mijotée comme en Italie, avec des tomates fraîches et un fond de bœuf haché.',
    '[
        {"step": 1, "text": "Faire revenir l''oignon et l''ail émincés dans l''huile d''olive pendant 5 minutes.", "duration_min": 5},
        {"step": 2, "text": "Ajouter 400g de bœuf haché et faire dorer.", "duration_min": 8},
        {"step": 3, "text": "Incorporer les tomates concassées, saler, poivrer et laisser mijoter 30 minutes.", "duration_min": 30},
        {"step": 4, "text": "Cuire les pâtes al dente selon le paquet. Servir avec la sauce.", "duration_min": 10}
    ]'::jsonb,
    4,
    15,
    40,
    1,
    'italienne',
    NULL,
    '{"calories": 520, "proteins_g": 28, "carbs_g": 68, "fat_g": 14}'::jsonb,
    ARRAY['pâtes', 'bœuf', 'rapide', 'enfants', 'familial'],
    0.88
),

-- Recette 3 : Soupe de légumes maison
(
    'f1000000-0000-0000-0000-000000000003',
    'seed',
    NULL,
    'Soupe de légumes d''hiver',
    'soupe-de-legumes-dhiver',
    'Une soupe réconfortante et anti-gaspi qui utilise les légumes du frigo.',
    '[
        {"step": 1, "text": "Éplucher et couper en dés les carottes, pommes de terre et oignons.", "duration_min": 10},
        {"step": 2, "text": "Faire revenir les légumes 5 minutes dans l''huile d''olive.", "duration_min": 5},
        {"step": 3, "text": "Couvrir d''eau froide (1,5L), saler et cuire 25 minutes.", "duration_min": 25},
        {"step": 4, "text": "Mixer et ajuster l''assaisonnement. Servir chaud.", "duration_min": 5}
    ]'::jsonb,
    6,
    15,
    30,
    1,
    'française',
    NULL,
    '{"calories": 180, "proteins_g": 4, "carbs_g": 30, "fat_g": 5}'::jsonb,
    ARRAY['soupe', 'légumes', 'hiver', 'végétarien', 'vegan', 'anti-gaspi', 'économique'],
    0.82
)
ON CONFLICT (slug) DO NOTHING;

-- -----------------------------------------------------------------------------
-- INGRÉDIENTS DES RECETTES
-- -----------------------------------------------------------------------------

-- Poulet rôti
INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit, notes, position) VALUES
    ('f1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000004', 1500, 'g',     'poulet entier',       1),
    ('f1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 300,  'g',     'coupées en tronçons', 2),
    ('f1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000003', 400,  'g',     'épluchées',           3),
    ('f1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000008', 30,   'ml',    NULL,                  4),
    ('f1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000009', 5,    'g',     NULL,                  5),
    ('f1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000010', 2,    'g',     NULL,                  6)
ON CONFLICT DO NOTHING;

-- Bolognaise
INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit, notes, position) VALUES
    ('f1000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000005', 400,  'g',     NULL,                  1),
    ('f1000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000006', 400,  'g',     'tomates concassées',  2),
    ('f1000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000002', 1,    'pièce', 'émincé',              3),
    ('f1000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000007', 3,    'g',     '2 gousses',           4),
    ('f1000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000008', 20,   'ml',    NULL,                  5)
ON CONFLICT DO NOTHING;

-- Soupe de légumes
INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit, notes, position) VALUES
    ('f1000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000001', 400,  'g',     NULL,                  1),
    ('f1000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000003', 400,  'g',     NULL,                  2),
    ('f1000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000002', 2,    'pièce', NULL,                  3),
    ('f1000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000008', 15,   'ml',    NULL,                  4),
    ('f1000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000009', 5,    'g',     NULL,                  5)
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- EMBEDDINGS FACTICES (vecteurs zéro pour les tests)
-- En production, ces vecteurs sont générés par RECIPE_SCOUT via sentence-transformers.
-- Un vecteur tout à zéro est invalide pour la recherche cosine (division par zéro),
-- mais il est utile pour tester le schéma et les policies sans dépendance ML.
-- AVANT les tests de recommandation, régénérer ces embeddings avec le vrai modèle.
-- -----------------------------------------------------------------------------

INSERT INTO recipe_embeddings (recipe_id, embedding) VALUES
    (
        'f1000000-0000-0000-0000-000000000001',
        -- Vecteur factice : 384 dimensions à valeur 0.001 (pas exactement zéro pour éviter
        -- l'erreur de division par zéro dans vector_cosine_ops lors des tests de requête)
        (SELECT array_fill(0.001::float4, ARRAY[384])::vector(384))
    ),
    (
        'f1000000-0000-0000-0000-000000000002',
        (SELECT array_fill(0.001::float4, ARRAY[384])::vector(384))
    ),
    (
        'f1000000-0000-0000-0000-000000000003',
        (SELECT array_fill(0.001::float4, ARRAY[384])::vector(384))
    )
ON CONFLICT (recipe_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- PLAN HEBDOMADAIRE DE TEST (semaine du 13 avril 2026, un lundi)
-- -----------------------------------------------------------------------------

INSERT INTO weekly_plans (id, household_id, week_start, status) VALUES
    (
        'g1000000-0000-0000-0000-000000000001',
        'b1000000-0000-0000-0000-000000000001',
        '2026-04-13',
        'draft'
    )
ON CONFLICT DO NOTHING;

-- Repas planifiés pour la semaine test
INSERT INTO planned_meals (plan_id, day_of_week, slot, recipe_id, servings_adjusted) VALUES
    ('g1000000-0000-0000-0000-000000000001', 1, 'dinner', 'f1000000-0000-0000-0000-000000000001', 4), -- Lundi : poulet rôti
    ('g1000000-0000-0000-0000-000000000001', 2, 'dinner', 'f1000000-0000-0000-0000-000000000002', 4), -- Mardi : bolognaise
    ('g1000000-0000-0000-0000-000000000001', 3, 'dinner', 'f1000000-0000-0000-0000-000000000003', 4)  -- Mercredi : soupe
ON CONFLICT DO NOTHING;

-- Réactivation des triggers après le seed
SET session_replication_role = DEFAULT;

-- Vérification finale
DO $$
BEGIN
    ASSERT (SELECT COUNT(*) FROM ingredients) >= 10,
        'Seed KO : moins de 10 ingrédients insérés';
    ASSERT (SELECT COUNT(*) FROM recipes) >= 3,
        'Seed KO : moins de 3 recettes insérées';
    ASSERT (SELECT COUNT(*) FROM recipe_embeddings) >= 3,
        'Seed KO : embeddings manquants';
    RAISE NOTICE 'Seed OK : % ingrédients, % recettes, % embeddings.',
        (SELECT COUNT(*) FROM ingredients),
        (SELECT COUNT(*) FROM recipes),
        (SELECT COUNT(*) FROM recipe_embeddings);
END;
$$;
