-- =============================================================================
-- 06-add-photo-urls.sql — Ajout de photo_url aux 75 recettes seed
-- Projet : MealPlanner SaaS / Presto
-- Date   : 2026-04-12
-- Usage  : Exécuter dans Supabase SQL Editor ou via Docker init-scripts
--
-- URLs Unsplash par catégorie (20+ URLs différentes utilisées)
-- Format : https://images.unsplash.com/photo-{ID}?w=800&auto=format&fit=crop
-- =============================================================================

-- ============================================================
-- RECETTES FRANÇAISES (18)
-- ============================================================

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&auto=format&fit=crop'
WHERE slug = 'blanquette-de-veau-traditionnelle';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1547592180-85f173990554?w=800&auto=format&fit=crop'
WHERE slug = 'cassoulet-toulousain';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1518492104633-130d0cc84637?w=800&auto=format&fit=crop'
WHERE slug = 'gratin-dauphinois';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&auto=format&fit=crop'
WHERE slug = 'quiche-lorraine-maison';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1511690743698-d9d85f2fbf38?w=800&auto=format&fit=crop'
WHERE slug = 'pot-au-feu-du-dimanche';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1528736235302-52922df5c122?w=800&auto=format&fit=crop'
WHERE slug = 'croque-monsieur-gratine';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1544025162-d76694265947?w=800&auto=format&fit=crop'
WHERE slug = 'boeuf-bourguignon';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1547592166-23ac45744acd?w=800&auto=format&fit=crop'
WHERE slug = 'soupe-a-l-oignon-gratinee';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1572453800999-e8d2d1589b7c?w=800&auto=format&fit=crop'
WHERE slug = 'ratatouille-nicoise';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=800&auto=format&fit=crop'
WHERE slug = 'coq-au-vin-rouge';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1568571780765-9276ac8b75a2?w=800&auto=format&fit=crop'
WHERE slug = 'tarte-tatin-aux-pommes';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1470324161839-ce2bb6fa6bc3?w=800&auto=format&fit=crop'
WHERE slug = 'creme-brulee-a-la-vanille';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1565680018434-b0d5d9893bd4?w=800&auto=format&fit=crop'
WHERE slug = 'bouillabaisse-marseillaise';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1587314168485-3236d6710814?w=800&auto=format&fit=crop'
WHERE slug = 'profiteroles-sauce-chocolat';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&auto=format&fit=crop'
WHERE slug = 'salade-nicoise-complete';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800&auto=format&fit=crop'
WHERE slug = 'flamiche-aux-poireaux';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&auto=format&fit=crop'
WHERE slug = 'confit-de-canard-aux-sarladaises';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=800&auto=format&fit=crop'
WHERE slug = 'moules-marinieres-a-la-creme';

-- ============================================================
-- RECETTES ITALIENNES (9)
-- ============================================================

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=800&auto=format&fit=crop'
WHERE slug = 'risotto-aux-champignons-porcini';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1473093226795-af9932fe5856?w=800&auto=format&fit=crop'
WHERE slug = 'pates-carbonara-romaines';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&auto=format&fit=crop'
WHERE slug = 'osso-buco-alla-milanese';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=800&auto=format&fit=crop'
WHERE slug = 'tiramisu-au-cafe-espresso';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1562802378-063ec186a863?w=800&auto=format&fit=crop'
WHERE slug = 'bruschetta-tomates-basilic';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800&auto=format&fit=crop'
WHERE slug = 'pizza-margherita-napolitaine';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1574894709920-11b28be1f8e8?w=800&auto=format&fit=crop'
WHERE slug = 'lasagnes-bolognaise-maison';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=800&auto=format&fit=crop'
WHERE slug = 'panna-cotta-aux-fruits-rouges';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&auto=format&fit=crop'
WHERE slug = 'gnocchis-sauce-gorgonzola';

-- ============================================================
-- RECETTES ASIATIQUES (7)
-- ============================================================

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=800&auto=format&fit=crop'
WHERE slug = 'pad-thai-aux-crevettes';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1557872943-16a5ac26437e?w=800&auto=format&fit=crop'
WHERE slug = 'ramen-tonkotsu-maison';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1590301157890-4810ed352733?w=800&auto=format&fit=crop'
WHERE slug = 'bibimbap-coreen';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=800&auto=format&fit=crop'
WHERE slug = 'curry-vert-thai-au-poulet';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1496116218417-1a781b1c416c?w=800&auto=format&fit=crop'
WHERE slug = 'nems-vietnamiens-croustillants';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1526318472351-c75fcf070305?w=800&auto=format&fit=crop'
WHERE slug = 'gyoza-japonais-poeles';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1617196034183-421b4040ed20?w=800&auto=format&fit=crop'
WHERE slug = 'chirashi-sushi-bowl';

-- ============================================================
-- RECETTES INDIENNES (6)
-- ============================================================

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800&auto=format&fit=crop'
WHERE slug = 'poulet-tikka-masala';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=800&auto=format&fit=crop'
WHERE slug = 'dal-lentilles-corail';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=800&auto=format&fit=crop'
WHERE slug = 'naans-au-beurre-maison';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1631515243349-e0cb75fb8d3a?w=800&auto=format&fit=crop'
WHERE slug = 'biryani-poulet-safran';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=800&auto=format&fit=crop'
WHERE slug = 'samosa-maison-aux-legumes';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1567188040759-fb8a883dc6d6?w=800&auto=format&fit=crop'
WHERE slug = 'palak-paneer-epinards-fromage';

-- ============================================================
-- RECETTES MEXICAINES (6)
-- ============================================================

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=800&auto=format&fit=crop'
WHERE slug = 'tacos-al-pastor-maison';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1541528551664-a26fd4e51c1c?w=800&auto=format&fit=crop'
WHERE slug = 'guacamole-frais-maison';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1628294895950-9805252327bc?w=800&auto=format&fit=crop'
WHERE slug = 'enchiladas-poulet-mole';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=800&auto=format&fit=crop'
WHERE slug = 'chili-con-carne-authentique';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1600891964092-4316c288032e?w=800&auto=format&fit=crop'
WHERE slug = 'quesadillas-fromage-jalapeños';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1535399831218-d5bd36d1a6b3?w=800&auto=format&fit=crop'
WHERE slug = 'ceviche-de-poisson-blanc';

-- ============================================================
-- RECETTES LIBANAISES / MÉDITERRANÉENNES (6)
-- ============================================================

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1590301157284-bd2fd05e3e30?w=800&auto=format&fit=crop'
WHERE slug = 'houmous-maison-onctueux';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1505253758473-96b7015fcd40?w=800&auto=format&fit=crop'
WHERE slug = 'tabboule-libanais-au-persil';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1593560708920-61dd98c46a4e?w=800&auto=format&fit=crop'
WHERE slug = 'falafels-croustillants-maison';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1600335895229-6e75511892c8?w=800&auto=format&fit=crop'
WHERE slug = 'moussaka-grecque-gratinee';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1590409516756-c0088aa44b90?w=800&auto=format&fit=crop'
WHERE slug = 'shakshuka-aux-poivrons';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&auto=format&fit=crop'
WHERE slug = 'fattoush-salade-du-levant';

-- ============================================================
-- RECETTES RAPIDES (6)
-- ============================================================

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=800&auto=format&fit=crop'
WHERE slug = 'omelette-aux-herbes-express';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1550304943-4f24f54ddde9?w=800&auto=format&fit=crop'
WHERE slug = 'salade-cesar-poulet-grille';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=800&auto=format&fit=crop'
WHERE slug = 'wraps-thon-avocat-epice';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=800&auto=format&fit=crop'
WHERE slug = 'pates-aglio-e-olio';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1511690656952-34342bb7c2f2?w=800&auto=format&fit=crop'
WHERE slug = 'smoothie-bowl-tropical-express';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&auto=format&fit=crop'
WHERE slug = 'bruschetta-champignons-ailles';

-- ============================================================
-- RECETTES VÉGÉTARIENNES / VEGAN (8)
-- ============================================================

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&auto=format&fit=crop'
WHERE slug = 'buddha-bowl-quinoa-legumes-rotis';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1574484284002-952d92456975?w=800&auto=format&fit=crop'
WHERE slug = 'curry-pois-chiches-epinards';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1568625365131-079e026a927d?w=800&auto=format&fit=crop'
WHERE slug = 'gratin-chou-fleur-au-curry';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1547592180-85f173990554?w=800&auto=format&fit=crop'
WHERE slug = 'soupe-lentilles-au-citron';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800&auto=format&fit=crop'
WHERE slug = 'burger-vegetalien-aux-betteraves';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=800&auto=format&fit=crop'
WHERE slug = 'risotto-petits-pois-menthe';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=800&auto=format&fit=crop'
WHERE slug = 'tacos-chou-fleur-roti';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1476718406336-bb5a9690ee2a?w=800&auto=format&fit=crop'
WHERE slug = 'veloute-butternut-gingembre';

-- ============================================================
-- DESSERTS (5)
-- ============================================================

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&auto=format&fit=crop'
WHERE slug = 'fondant-chocolat-coeur-coulant';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1519915028121-7d3463d5b1ff?w=800&auto=format&fit=crop'
WHERE slug = 'tarte-citron-meringuee';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1511381939415-e44571d27f41?w=800&auto=format&fit=crop'
WHERE slug = 'mousse-chocolat-aerienne';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1506459225024-1428097a7e18?w=800&auto=format&fit=crop'
WHERE slug = 'clafoutis-aux-cerises';

UPDATE recipes SET photo_url = 'https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=800&auto=format&fit=crop'
WHERE slug = 'banoffee-pie-au-caramel';

-- =============================================================================
-- Vérification : compter les recettes avec photo_url mis à jour
-- Résultat attendu : 75 lignes avec photo_url NOT NULL
-- =============================================================================
-- SELECT COUNT(*) FROM recipes WHERE photo_url IS NOT NULL;
-- SELECT slug, photo_url FROM recipes WHERE photo_url IS NULL ORDER BY slug;
