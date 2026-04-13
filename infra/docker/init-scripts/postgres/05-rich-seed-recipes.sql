-- =============================================================================
-- 05-rich-seed-recipes.sql — Seed enrichi de 75 recettes multi-cuisines
-- Projet : MealPlanner SaaS / Presto
-- Date   : 2026-04-12
-- Usage  : Exécuter dans Supabase SQL Editor ou via Docker init-scripts
--
-- Contenu :
--   - 18 recettes françaises classiques
--   - 9  recettes italiennes
--   - 7  recettes asiatiques (Japon, Thaïlande, Corée, Vietnam, Chine)
--   - 6  recettes indiennes
--   - 6  recettes mexicaines
--   - 6  recettes libanaises / méditerranéennes
--   - 6  recettes rapides (< 20 min)
--   - 8  recettes végétariennes / vegan
--   - 5  desserts
-- Total  : 75 recettes
--
-- IMPORTANT : total_time_min est une colonne GENERATED — exclue de cet INSERT.
-- =============================================================================

INSERT INTO recipes (
    id, source, title, slug, description, instructions,
    servings, prep_time_min, cook_time_min,
    difficulty, cuisine_type, tags, quality_score
) VALUES

-- ============================================================
-- RECETTES FRANÇAISES (18)
-- ============================================================

(gen_random_uuid(), 'curated', 'Blanquette de veau traditionnelle', 'blanquette-de-veau-traditionnelle',
 'La blanquette de veau à l''ancienne, sauce crémeuse et légumes fondants. Un grand classique de la cuisine familiale française.',
 '[{"step":1,"text":"Couper le veau en morceaux réguliers de 4 cm et les faire blanchir 5 min dans l''eau bouillante salée. Égoutter et rincer."},{"step":2,"text":"Mettre la viande dans une cocotte, couvrir d''eau froide, ajouter carottes, oignons, céleri et bouquet garni. Porter à ébullition."},{"step":3,"text":"Écumer soigneusement, puis laisser mijoter à feu doux 1h30 jusqu''à tendreté du veau."},{"step":4,"text":"Retirer la viande. Filtrer le bouillon. Préparer un roux blanc (beurre + farine) et délayer avec 500 ml de bouillon chaud."},{"step":5,"text":"Lier hors du feu avec un mélange crème fraîche + 2 jaunes d''œuf. Rectifier l''assaisonnement. Remettre la viande et servir avec du riz."}]'::jsonb,
 6, 30, 120, 3, 'française', ARRAY['veau','mijoté','classique','hiver','familial','crème','sans-porc'], 0.92),

(gen_random_uuid(), 'curated', 'Cassoulet toulousain', 'cassoulet-toulousain',
 'Le cassoulet authentique de Toulouse : haricots blancs fondants, confit de canard et saucisses dorées sous une croûte croustillante.',
 '[{"step":1,"text":"Faire tremper les haricots blancs 12h dans de l''eau froide. Les égoutter et les cuire 45 min dans de l''eau non salée."},{"step":2,"text":"Faire revenir les saucisses de Toulouse et les lardons dans une cocotte en fonte. Réserver."},{"step":3,"text":"Faire dorer les cuisses de canard confites côté peau. Réserver avec les viandes."},{"step":4,"text":"Dans la cocotte, faire suer oignons et ail, ajouter les tomates concassées et le bouillon. Incorporer les haricots et toutes les viandes."},{"step":5,"text":"Enfourner à 160°C pendant 2h. Casser la croûte 3 fois pendant la cuisson en arrosant avec le bouillon."},{"step":6,"text":"Servir directement dans la cocotte bien chaude."}]'::jsonb,
 8, 30, 180, 4, 'française', ARRAY['canard','haricots','mijoté','hiver','familial','sud-ouest','sans-lactose'], 0.91),

(gen_random_uuid(), 'curated', 'Gratin dauphinois', 'gratin-dauphinois',
 'Le gratin dauphinois authentique : pommes de terre fondantes infusées à l''ail dans une crème riche et dorée.',
 '[{"step":1,"text":"Préchauffer le four à 180°C. Frotter un plat à gratin avec une gousse d''ail coupée, puis le beurrer généreusement."},{"step":2,"text":"Éplucher et couper les pommes de terre en tranches très fines (2 mm) à la mandoline. Ne pas les rincer pour conserver l''amidon."},{"step":3,"text":"Faire chauffer la crème fraîche avec l''ail émincé, sel, poivre et noix de muscade. Ne pas faire bouillir."},{"step":4,"text":"Disposer les pommes de terre en couches dans le plat en les chevauchant. Verser la crème chaude par-dessus."},{"step":5,"text":"Enfourner 1h15 jusqu''à ce que le dessus soit bien doré et qu''un couteau s''enfonce sans résistance."}]'::jsonb,
 6, 20, 75, 2, 'française', ARRAY['pommes-de-terre','crème','végétarien','hiver','familial','gratin','sans-gluten'], 0.90),

(gen_random_uuid(), 'curated', 'Quiche lorraine maison', 'quiche-lorraine-maison',
 'La quiche lorraine incontournable : pâte brisée croustillante, appareil crème-œuf et lardons fumés généreux.',
 '[{"step":1,"text":"Préparer la pâte brisée : mélanger 250g de farine, 125g de beurre froid en dés, 1 pincée de sel et 3-4 cuil. à soupe d''eau froide. Abaisser et foncer un moule de 28 cm."},{"step":2,"text":"Précuire le fond de tarte 10 min à blanc à 180°C avec des billes de cuisson."},{"step":3,"text":"Faire revenir les lardons à sec dans une poêle chaude. Égoutter sur du papier absorbant."},{"step":4,"text":"Battre 4 œufs avec 30 cl de crème fraîche épaisse, sel, poivre et noix de muscade."},{"step":5,"text":"Répartir les lardons sur le fond de tarte, verser l''appareil crémeux. Enfourner 35 min à 180°C jusqu''à prise et coloration dorée."}]'::jsonb,
 6, 25, 45, 2, 'française', ARRAY['tarte','lardons','crème','familial','toute-saison','plat'], 0.89),

(gen_random_uuid(), 'curated', 'Pot-au-feu du dimanche', 'pot-au-feu-du-dimanche',
 'Le pot-au-feu dominical réconfortant : viandes mijotées avec légumes de saison dans un bouillon doré savoureux.',
 '[{"step":1,"text":"Mettre le jarret et le paleron dans une grande marmite, couvrir d''eau froide. Porter à ébullition et écumer soigneusement pendant 10 min."},{"step":2,"text":"Ajouter les os à moelle ficelés, l''oignon brûlé, le bouquet garni, sel et poivre en grains. Laisser frémir 2h à couvert."},{"step":3,"text":"Ajouter les carottes, navets, poireaux, céleri et panais en tronçons. Cuire encore 45 min."},{"step":4,"text":"Ajouter les pommes de terre 25 min avant la fin. Retirer les os à moelle et les servir à part avec fleur de sel."},{"step":5,"text":"Servir le bouillon en entrée, puis la viande tranchée avec les légumes, moutarde, cornichons et gros sel."}]'::jsonb,
 8, 30, 180, 2, 'française', ARRAY['bœuf','mijoté','hiver','familial','bouillon','classique','sans-gluten','sans-lactose'], 0.91),

(gen_random_uuid(), 'curated', 'Croque-monsieur gratiné', 'croque-monsieur-gratine',
 'Le croque-monsieur façon bistrot parisien : béchamel veloutée, jambon généreux et emmental gratiné à la perfection.',
 '[{"step":1,"text":"Préparer la béchamel : faire fondre 30g de beurre, ajouter 30g de farine, puis verser 300 ml de lait chaud en fouettant. Assaisonner sel, poivre, muscade."},{"step":2,"text":"Tartiner généreusement de béchamel l''intérieur des tranches de pain de mie."},{"step":3,"text":"Disposer une tranche de jambon blanc et de l''emmental râpé sur la moitié des tranches. Refermer les sandwichs."},{"step":4,"text":"Napper le dessus des croque-monsieur de béchamel et parsemer d''emmental râpé."},{"step":5,"text":"Passer au four à 200°C (gril) pendant 8-10 min jusqu''à coloration dorée et bullante."}]'::jsonb,
 4, 15, 15, 1, 'française', ARRAY['jambon','fromage','rapide','toute-saison','enfants','bistrot'], 0.87),

(gen_random_uuid(), 'curated', 'Bœuf bourguignon', 'boeuf-bourguignon',
 'Le bœuf bourguignon mijoté longuement dans le vin rouge de Bourgogne avec champignons et lardons : un plat d''exception.',
 '[{"step":1,"text":"Couper le bœuf en gros cubes. Faire mariner 12h dans du vin rouge avec carottes, oignons, ail et bouquet garni."},{"step":2,"text":"Égoutter la viande, la sécher. Faire dorer en petites quantités dans une cocotte avec de l''huile très chaude."},{"step":3,"text":"Dans la même cocotte, faire revenir les lardons et les oignons grelots. Ajouter la farine, les légumes de la marinade, puis le vin filtré et le bouillon."},{"step":4,"text":"Remettre la viande, couvrir et laisser mijoter 2h30 à feu très doux ou au four à 150°C."},{"step":5,"text":"Poêler les champignons de Paris au beurre. Les ajouter en fin de cuisson. Rectifier l''assaisonnement et servir avec des pommes de terre vapeur."}]'::jsonb,
 6, 30, 180, 3, 'française', ARRAY['bœuf','vin-rouge','mijoté','hiver','classique','bourguignon','sans-gluten'], 0.94),

(gen_random_uuid(), 'curated', 'Soupe à l''oignon gratinée', 'soupe-a-l-oignon-gratinee',
 'La soupe à l''oignon des halles parisiennes : oignons caramélisés, bouillon de bœuf corsé et croûtons gratinés.',
 '[{"step":1,"text":"Émincer finement 1 kg d''oignons jaunes. Les faire caraméliser 45 min à feu doux dans du beurre, en remuant régulièrement."},{"step":2,"text":"Saupoudrer de farine, remuer 2 min, puis déglacer avec 10 cl de vin blanc sec."},{"step":3,"text":"Ajouter 1,5 L de bouillon de bœuf chaud, sel, poivre. Mijoter 20 min."},{"step":4,"text":"Verser la soupe dans des bols allant au four. Déposer des tranches de baguette grillées sur le dessus."},{"step":5,"text":"Couvrir généreusement de gruyère râpé. Gratiner 5-8 min sous le gril du four jusqu''à belle coloration."}]'::jsonb,
 4, 15, 60, 2, 'française', ARRAY['soupe','oignon','gratiné','hiver','végétarien','bistrot','entrée'], 0.88),

(gen_random_uuid(), 'curated', 'Ratatouille niçoise', 'ratatouille-nicoise',
 'La ratatouille provençale aux légumes du soleil, mijotée dans l''huile d''olive avec herbes de Provence.',
 '[{"step":1,"text":"Couper en dés réguliers : 2 courgettes, 2 aubergines, 3 poivrons (rouge, jaune, vert) et 4 tomates. Saler les aubergines 20 min, puis rincer."},{"step":2,"text":"Faire revenir séparément chaque légume dans l''huile d''olive en les saisissant rapidement. Réserver."},{"step":3,"text":"Dans la même poêle, faire suer 2 oignons et 4 gousses d''ail émincés."},{"step":4,"text":"Réunir tous les légumes dans une cocotte, ajouter herbes de Provence, thym, laurier et un filet d''huile d''olive. Assaisonner."},{"step":5,"text":"Mijoter 30 min à feu doux à couvert. Découvrir les 10 dernières minutes pour concentrer les saveurs."}]'::jsonb,
 6, 30, 60, 2, 'française', ARRAY['légumes','vegan','végétarien','été','méditerranéen','sans-gluten','sans-lactose','économique'], 0.88),

(gen_random_uuid(), 'curated', 'Coq au vin rouge', 'coq-au-vin-rouge',
 'Le coq au vin mijoté dans le Bourgogne avec champignons, lardons et oignons grelots : un classique réconfortant.',
 '[{"step":1,"text":"Découper le coq en morceaux, les assaisonner et les faire dorer dans une cocotte avec beurre et huile."},{"step":2,"text":"Retirer le coq. Faire revenir les lardons, oignons grelots et champignons dans la cocotte."},{"step":3,"text":"Remettre les morceaux de coq, flamber au cognac puis mouiller avec 75 cl de vin rouge de Bourgogne."},{"step":4,"text":"Ajouter ail, bouquet garni, sel et poivre. Porter à frémissement, couvrir et mijoter 1h30 à feu doux."},{"step":5,"text":"Lier la sauce si nécessaire avec du beurre manié. Servir avec des pâtes fraîches ou une purée."}]'::jsonb,
 6, 25, 100, 3, 'française', ARRAY['poulet','vin-rouge','mijoté','hiver','classique','sans-gluten'], 0.90),

(gen_random_uuid(), 'curated', 'Tarte tatin aux pommes', 'tarte-tatin-aux-pommes',
 'La légendaire tarte tatin des sœurs Tatin : caramel ambré, pommes fondantes et pâte feuilletée croustillante renversée.',
 '[{"step":1,"text":"Préparer le caramel : faire fondre 100g de sucre avec 50g de beurre dans une poêle allant au four jusqu''à coloration ambrée."},{"step":2,"text":"Éplucher et couper en quartiers 8 pommes Golden. Les disposer serrées, debout, dans le caramel."},{"step":3,"text":"Cuire les pommes à feu moyen 10 min pour les faire compoter légèrement."},{"step":4,"text":"Couvrir avec une abaisse de pâte feuilletée en rentrant les bords. Piquer avec une fourchette."},{"step":5,"text":"Enfourner 25 min à 200°C. Attendre 5 min hors du four puis retourner sur un plat de service. Servir tiède avec de la crème fraîche."}]'::jsonb,
 8, 20, 40, 3, 'française', ARRAY['dessert','pommes','caramel','végétarien','toute-saison','tarte'], 0.92),

(gen_random_uuid(), 'curated', 'Crème brûlée à la vanille', 'creme-brulee-a-la-vanille',
 'La crème brûlée à la vanille de Madagascar, dorée au chalumeau : fondante et craquante à la fois.',
 '[{"step":1,"text":"Préchauffer le four à 150°C. Fendre et gratter 2 gousses de vanille dans 50 cl de crème entière. Chauffer doucement sans faire bouillir."},{"step":2,"text":"Blanchir 6 jaunes d''œuf avec 80g de sucre. Verser la crème vanillée chaude en filet en fouettant."},{"step":3,"text":"Filtrer l''appareil, verser dans 6 ramequins. Cuire au bain-marie 40 min à 150°C : la crème doit trembler légèrement au centre."},{"step":4,"text":"Laisser refroidir, puis réfrigérer au moins 4h."},{"step":5,"text":"Au moment de servir, saupoudrer de cassonade et caraméliser au chalumeau ou sous le gril."}]'::jsonb,
 6, 20, 45, 3, 'française', ARRAY['dessert','vanille','crème','végétarien','toute-saison','premium','sans-gluten'], 0.93),

(gen_random_uuid(), 'curated', 'Bouillabaisse marseillaise', 'bouillabaisse-marseillaise',
 'La bouillabaisse authentique de Marseille : rougets, daurades et Saint-Pierre dans un bouillon safrane, servie avec la rouille.',
 '[{"step":1,"text":"Préparer la rouille : mixer ail, safran, huile d''olive, jaune d''œuf et mie de pain trempée. Réserver au frais."},{"step":2,"text":"Faire revenir dans l''huile d''olive : oignons, poireaux, fenouil, tomates concassées, ail et zeste d''orange."},{"step":3,"text":"Mouiller avec 1,5 L de fumet de poisson, ajouter safran, thym, laurier, sel et piment de Cayenne. Cuire 20 min."},{"step":4,"text":"Ajouter les poissons à chair ferme en premier (Saint-Pierre, grondin), puis les plus délicats (rouget, vive) 5 min après."},{"step":5,"text":"Servir le bouillon en premier avec des croûtons frottés à l''ail, puis les poissons avec la rouille et les pommes de terre."}]'::jsonb,
 6, 40, 45, 4, 'française', ARRAY['poisson','soupe','méditerranéen','été','premium','sans-gluten','sans-lactose'], 0.91),

(gen_random_uuid(), 'curated', 'Profiteroles sauce chocolat', 'profiteroles-sauce-chocolat',
 'Des choux légers garnis de glace vanille nappés d''une sauce chocolat chaude : le grand classique des desserts brasserie.',
 '[{"step":1,"text":"Préparer la pâte à choux : faire bouillir 25 cl d''eau avec 100g de beurre et 1 pincée de sel. Incorporer 150g de farine en une fois et dessécher 2 min. Ajouter 4 œufs un par un."},{"step":2,"text":"Pocher des petites boules sur une plaque à l''aide d''une poche à douille. Enfourner 20 min à 200°C sans ouvrir le four."},{"step":3,"text":"Laisser refroidir complètement sur une grille."},{"step":4,"text":"Préparer la sauce chocolat : faire fondre 200g de chocolat noir avec 20 cl de crème chaude. Lisser."},{"step":5,"text":"Garnir les choux de glace vanille, les dresser dans des assiettes creuses et napper de sauce chocolat chaude."}]'::jsonb,
 6, 30, 25, 3, 'française', ARRAY['dessert','chocolat','choux','végétarien','toute-saison','brasserie'], 0.89),

(gen_random_uuid(), 'curated', 'Salade niçoise complète', 'salade-nicoise-complete',
 'La vraie salade niçoise avec thon, anchois, œufs durs, olives et légumes crus : fraîche et généreuse.',
 '[{"step":1,"text":"Cuire les haricots verts al dente dans l''eau bouillante salée (7 min). Refroidir dans de l''eau glacée."},{"step":2,"text":"Cuire les œufs durs (10 min), les écaler et les couper en quartiers. Couper les tomates en quartiers."},{"step":3,"text":"Égoutter le thon en conserve et les anchois. Préparer les olives niçoises, les tranches de poivron cru."},{"step":4,"text":"Préparer la vinaigrette : huile d''olive, vinaigre de vin rouge, sel, poivre et herbes de Provence."},{"step":5,"text":"Dresser joliment tous les ingrédients dans un grand saladier. Arroser de vinaigrette au dernier moment."}]'::jsonb,
 4, 20, 10, 1, 'française', ARRAY['salade','thon','été','rapide','sans-gluten','sans-lactose','méditerranéen','entrée'], 0.87),

(gen_random_uuid(), 'curated', 'Flamiche aux poireaux', 'flamiche-aux-poireaux',
 'La flamiche picarde aux poireaux fondants dans une crème onctueuse, enfermée dans une pâte brisée généreuse.',
 '[{"step":1,"text":"Nettoyer et émincer finement 1 kg de poireaux (blanc et vert tendre). Les faire fondre 20 min à l''étouffée dans du beurre avec sel et poivre."},{"step":2,"text":"Mélanger les poireaux avec 20 cl de crème fraîche épaisse, 3 œufs battus et 100g de gruyère râpé."},{"step":3,"text":"Foncer un moule de 30 cm avec une pâte brisée maison ou feuilletée. Piquer le fond."},{"step":4,"text":"Verser la garniture aux poireaux. Recouvrir avec le reste de pâte en soudant bien les bords."},{"step":5,"text":"Dorer au jaune d''œuf, faire une cheminée au centre. Cuire 35 min à 200°C."}]'::jsonb,
 6, 25, 55, 2, 'française', ARRAY['poireau','tarte','végétarien','hiver','familial','nord-france'], 0.86),

(gen_random_uuid(), 'curated', 'Confit de canard aux sarladaises', 'confit-de-canard-aux-sarladaises',
 'Les cuisses de canard confites dorées à la poêle, servies avec les pommes de terre sarladaises à l''ail et au persil.',
 '[{"step":1,"text":"Préchauffer le four à 200°C. Sortir les cuisses de canard confites de leur graisse et les déposer côté peau dans une poêle allant au four."},{"step":2,"text":"Enfourner 25 min jusqu''à ce que la peau soit croustillante et dorée."},{"step":3,"text":"Pendant ce temps, couper en tranches fines des pommes de terre cuites à la vapeur. Les faire revenir à la graisse de canard avec ail et persil plat ciselés."},{"step":4,"text":"Assaisonner les sarladaises de sel et poivre. Cuire jusqu''à coloration dorée en retournant régulièrement."},{"step":5,"text":"Dresser la cuisse croustillante sur les pommes sarladaises. Décorer de persil et servir immédiatement."}]'::jsonb,
 4, 15, 30, 2, 'française', ARRAY['canard','pommes-de-terre','sans-gluten','hiver','premium','sud-ouest'], 0.90),

(gen_random_uuid(), 'curated', 'Moules marinières à la crème', 'moules-marinieres-a-la-creme',
 'Les moules de bouchot ouvertes dans un court-bouillon de vin blanc, avec échalotes et une touche de crème fraîche.',
 '[{"step":1,"text":"Gratter et rincer soigneusement 2 kg de moules. Éliminer celles qui sont ouvertes et ne se referment pas."},{"step":2,"text":"Émincer finement 4 échalotes. Les faire suer dans une grande cocotte avec du beurre sans coloration."},{"step":3,"text":"Verser 20 cl de vin blanc sec et porter à ébullition. Ajouter les moules, couvrir et cuire à feu vif 4-5 min en secouant la cocotte."},{"step":4,"text":"Retirer les moules ouvertes et les réserver. Filtrer le jus. Ajouter 10 cl de crème fraîche et faire réduire 2 min."},{"step":5,"text":"Verser la sauce crémée sur les moules, parsemer de persil plat haché. Servir avec des frites."}]'::jsonb,
 4, 15, 15, 1, 'française', ARRAY['moules','fruits-de-mer','rapide','toute-saison','sans-gluten'], 0.88),

-- ============================================================
-- RECETTES ITALIENNES (9)
-- ============================================================

(gen_random_uuid(), 'curated', 'Risotto aux champignons porcini', 'risotto-aux-champignons-porcini',
 'Un risotto crémeux et parfumé aux champignons porcini séchés, mantecato au parmesan et beurre froid.',
 '[{"step":1,"text":"Réhydrater 30g de porcini séchés dans 50 cl d''eau tiède 20 min. Filtrer et réserver le jus. Chauffer 1 L de bouillon de légumes."},{"step":2,"text":"Faire suer 1 oignon émincé dans du beurre. Ajouter 320g de riz Arborio, nacrer 2 min en remuant."},{"step":3,"text":"Déglacer avec 10 cl de vin blanc sec. Ajouter le jus de trempage filtré puis le bouillon louche par louche en remuant constamment."},{"step":4,"text":"Après 16 min de cuisson, incorporer les porcini réhydratés et les champignons de Paris sautés au beurre."},{"step":5,"text":"Hors du feu, mantecato : incorporer vigoureusement 40g de beurre froid en dés et 60g de parmesan râpé. Couvrir 2 min et servir."}]'::jsonb,
 4, 20, 25, 3, 'italienne', ARRAY['risotto','champignons','végétarien','hiver','premium','sans-gluten'], 0.93),

(gen_random_uuid(), 'curated', 'Pâtes carbonara romaines', 'pates-carbonara-romaines',
 'La vraie carbonara de Rome : guanciale croustillant, sauce aux jaunes d''œuf et pecorino, sans crème.',
 '[{"step":1,"text":"Faire revenir des dés de guanciale (ou pancetta) dans une poêle sans matière grasse jusqu''à ce qu''ils soient croustillants. Réserver."},{"step":2,"text":"Fouetter vigoureusement 4 jaunes d''œuf + 1 entier avec 80g de pecorino romano râpé et poivre noir fraîchement moulu."},{"step":3,"text":"Cuire 400g de spaghetti dans un grand volume d''eau bouillante salée al dente. Conserver 2 louches d''eau de cuisson."},{"step":4,"text":"Hors du feu, mélanger les pâtes chaudes avec le guanciale et son gras. Verser la sauce œuf-fromage en remuant vigoureusement."},{"step":5,"text":"Ajouter l''eau de cuisson petit à petit pour obtenir une sauce crémeuse et nappante. Servir immédiatement avec du pecorino et du poivre."}]'::jsonb,
 4, 10, 15, 2, 'italienne', ARRAY['pâtes','porc','rapide','toute-saison','classique','sans-lactose'], 0.94),

(gen_random_uuid(), 'curated', 'Osso buco alla milanese', 'osso-buco-alla-milanese',
 'L''osso buco milanais : jarrets de veau braisés dans un fond de tomates et légumes, servis avec la gremolata.',
 '[{"step":1,"text":"Fariner les jarrets de veau et les faire dorer de chaque côté dans l''huile d''olive et le beurre."},{"step":2,"text":"Retirer la viande. Faire suer oignons, carottes et céleri en brunoise dans la même cocotte."},{"step":3,"text":"Ajouter l''ail, les tomates concassées, le vin blanc, le bouillon et le zeste de citron. Remettre les jarrets."},{"step":4,"text":"Couvrir et cuire 1h30 à feu doux (ou four 160°C) jusqu''à ce que la viande se détache de l''os."},{"step":5,"text":"Préparer la gremolata : mélanger zeste de citron, ail émincé et persil haché. Parsemer sur l''osso buco au service. Accompagner de risotto milanais au safran."}]'::jsonb,
 4, 25, 100, 3, 'italienne', ARRAY['veau','mijoté','hiver','classique','premium','sans-gluten'], 0.91),

(gen_random_uuid(), 'curated', 'Tiramisu au café espresso', 'tiramisu-au-cafe-espresso',
 'Le tiramisu authentique : biscuits imbibés d''espresso, crème mascarpone aérienne et cacao en poudre.',
 '[{"step":1,"text":"Préparer 30 cl d''espresso fort. Laisser refroidir et ajouter 2 cuil. à soupe d''Amaretto (facultatif)."},{"step":2,"text":"Séparer 4 œufs. Fouetter les jaunes avec 100g de sucre jusqu''à blanchiment. Incorporer 500g de mascarpone."},{"step":3,"text":"Monter les blancs en neige ferme et les incorporer délicatement à la préparation mascarpone."},{"step":4,"text":"Tremper rapidement les biscuits Savoiardi dans le café et les disposer en couche dans un plat. Verser la moitié de la crème."},{"step":5,"text":"Recommencer une couche de biscuits imbibés et terminer par la crème. Saupoudrer de cacao amer. Réfrigérer 4h minimum."}]'::jsonb,
 8, 30, 0, 2, 'italienne', ARRAY['dessert','café','végétarien','toute-saison','classique','sans-cuisson'], 0.92),

(gen_random_uuid(), 'curated', 'Bruschetta tomates basilic', 'bruschetta-tomates-basilic',
 'La bruschetta authentique : pain grillé frotté à l''ail, tomates cerises marinées et basilic frais généreux.',
 '[{"step":1,"text":"Couper en dés 400g de tomates cerises ou tomates cœur-de-bœuf. Assaisonner avec sel, poivre, huile d''olive et basilic ciselé. Laisser mariner 15 min."},{"step":2,"text":"Couper une baguette ou du pain de campagne en tranches épaisses de 1,5 cm."},{"step":3,"text":"Passer les tranches au gril ou à la poêle sèche jusqu''à coloration dorée et croustillante."},{"step":4,"text":"Frotter chaque tranche avec une gousse d''ail coupée en deux."},{"step":5,"text":"Disposer les tomates marinées sur les tranches, arroser d''un filet d''huile d''olive extra vierge. Servir immédiatement."}]'::jsonb,
 4, 15, 5, 1, 'italienne', ARRAY['apéritif','tomate','végétarien','vegan','été','express','entrée'], 0.86),

(gen_random_uuid(), 'curated', 'Pizza Margherita napolitaine', 'pizza-margherita-napolitaine',
 'La pizza Margherita STG : pâte à la farine 00, San Marzano, fior di latte et basilic frais. Cuite à très haute température.',
 '[{"step":1,"text":"Préparer la pâte : 500g de farine 00, 325 ml d''eau froide, 10g de sel, 1g de levure sèche. Pétrir 15 min, laisser lever 24h au réfrigérateur."},{"step":2,"text":"Sortir les pâtons 2h avant. Préchauffer le four au maximum (250°C ou plus) avec une pierre à pizza ou une plaque épaisse."},{"step":3,"text":"Étaler la pâte à la main en disque de 30 cm sans rouleau."},{"step":4,"text":"Napper de tomates San Marzano concassées assaisonnées. Répartir la fior di latte (mozzarella fraîche) en morceaux."},{"step":5,"text":"Cuire 6-8 min jusqu''à ce que les bords soient gonflés et noirs par endroits. Ajouter basilic frais et un filet d''huile d''olive à la sortie du four."}]'::jsonb,
 4, 30, 10, 3, 'italienne', ARRAY['pizza','végétarien','toute-saison','classique','familial'], 0.91),

(gen_random_uuid(), 'curated', 'Lasagnes bolognaise maison', 'lasagnes-bolognaise-maison',
 'Les lasagnes maison avec ragù bolognaise mijoté 3h, béchamel crémeuse et parmesan fondu en couches généreuses.',
 '[{"step":1,"text":"Préparer le ragù : faire revenir un soffritto (oignon, carotte, céleri), ajouter 600g de viande mixte (bœuf + porc). Mouiller avec vin rouge et tomates pelées. Mijoter 3h à feu très doux."},{"step":2,"text":"Préparer la béchamel : faire un roux beurre-farine, délayer avec 1 L de lait chaud, assaisonner sel, poivre, noix de muscade."},{"step":3,"text":"Dans un grand plat à gratin, alterner couches de pâtes fraîches (ou sèches précuites), ragù et béchamel."},{"step":4,"text":"Terminer par la béchamel et couvrir généreusement de parmesan râpé."},{"step":5,"text":"Cuire 45 min à 180°C. Laisser reposer 10 min avant de couper et servir."}]'::jsonb,
 8, 40, 220, 3, 'italienne', ARRAY['pâtes','bœuf','porc','familial','hiver','classique'], 0.90),

(gen_random_uuid(), 'curated', 'Panna cotta aux fruits rouges', 'panna-cotta-aux-fruits-rouges',
 'La panna cotta crémeuse à la vanille, nappée d''un coulis de fruits rouges : fraîche et élégante.',
 '[{"step":1,"text":"Hydrater 3g de gélatine en poudre dans 2 cuil. à soupe d''eau froide. Ou ramollir 3 feuilles dans de l''eau froide."},{"step":2,"text":"Chauffer 50 cl de crème entière avec 50g de sucre et 1 gousse de vanille. Ne pas faire bouillir."},{"step":3,"text":"Hors du feu, incorporer la gélatine essorée. Mélanger jusqu''à dissolution complète."},{"step":4,"text":"Verser dans des ramequins ou verrines légèrement huilés. Réfrigérer au moins 4h."},{"step":5,"text":"Préparer le coulis : mixer 250g de framboises avec 2 cuil. à soupe de sucre et un filet de citron. Filtrer. Démouler la panna cotta et napper de coulis."}]'::jsonb,
 6, 15, 10, 2, 'italienne', ARRAY['dessert','végétarien','été','fruits-rouges','sans-gluten','premium'], 0.89),

(gen_random_uuid(), 'curated', 'Gnocchis à la sauce gorgonzola', 'gnocchis-sauce-gorgonzola',
 'Des gnocchis maison moelleux nappés d''une sauce gorgonzola dolce crémeuse et noix torréfiées.',
 '[{"step":1,"text":"Cuire 800g de pommes de terre à la vapeur. Les éplucher chaudes et les passer au moulin à légumes."},{"step":2,"text":"Mélanger avec 200g de farine, 1 œuf, sel et muscade. Pétrir rapidement sans trop travailler la pâte."},{"step":3,"text":"Rouler la pâte en boudins de 2 cm, couper en tronçons et rouler sur les dents d''une fourchette."},{"step":4,"text":"Plonger les gnocchis dans l''eau bouillante salée. Les récupérer dès qu''ils remontent à la surface."},{"step":5,"text":"Faire fondre 150g de gorgonzola dolce dans 15 cl de crème chaude. Napper les gnocchis et parsemer de noix torréfiées grossièrement concassées."}]'::jsonb,
 4, 40, 10, 3, 'italienne', ARRAY['gnocchis','végétarien','hiver','fromage','premium'], 0.88),

-- ============================================================
-- RECETTES ASIATIQUES (7)
-- ============================================================

(gen_random_uuid(), 'curated', 'Pad Thaï aux crevettes', 'pad-thai-aux-crevettes',
 'Le pad thaï authentique : nouilles de riz sautées avec crevettes, œufs, sauce tamarin et cacahuètes grillées.',
 '[{"step":1,"text":"Faire tremper les nouilles de riz plates dans l''eau froide 30 min. Égoutter."},{"step":2,"text":"Préparer la sauce : mélanger 3 cuil. à soupe de sauce tamarin, 2 cuil. à soupe de sauce poisson, 1 cuil. à soupe de sucre de palme."},{"step":3,"text":"Faire sauter les crevettes décortiquées dans un wok très chaud avec de l''huile. Réserver."},{"step":4,"text":"Dans le même wok, faire revenir l''ail et les échalotes, ajouter les nouilles égouttées et la sauce. Mélanger vigoureusement."},{"step":5,"text":"Pousser les nouilles sur le côté, faire brouiller 2 œufs. Mélanger avec les nouilles. Ajouter les crevettes, germes de soja, ciboulette thaïe. Servir avec cacahuètes, citron vert et piment rouge."}]'::jsonb,
 2, 30, 15, 2, 'thaïlandaise', ARRAY['crevettes','nouilles','sans-gluten','sans-lactose','toute-saison','wok'], 0.90),

(gen_random_uuid(), 'curated', 'Ramen tonkotsu maison', 'ramen-tonkotsu-maison',
 'Un ramen tonkotsu au bouillon de porc laiteux mijoté 8h, chashu fondant, œuf mariné et nori.',
 '[{"step":1,"text":"Blanchir 1 kg d''os de porc (cou et pied) 5 min. Rincer. Cuire à gros bouillons dans 3 L d''eau pendant 8h en maintenant l''ébullition pour un bouillon laiteux."},{"step":2,"text":"Préparer le chashu : rouler et ficeler de la poitrine de porc. Faire braiser 2h dans soja, mirin, saké et sucre. Refroidir et trancher."},{"step":3,"text":"Préparer les œufs marinés : cuire 6 min 30, écaler et tremper 4h dans la sauce du chashu diluée."},{"step":4,"text":"Préparer le tare (assaisonnement) : mélanger sauce soja, mirin et sel."},{"step":5,"text":"Cuire les nouilles ramen. Dresser : bouillon chaud + tare dans un bol, nouilles, chashu tranché, demi-œuf mariné, nori, ciboulette et graines de sésame."}]'::jsonb,
 4, 60, 480, 5, 'japonaise', ARRAY['porc','soupe','hiver','premium','ramen','sans-lactose'], 0.90),

(gen_random_uuid(), 'curated', 'Bibimbap coréen', 'bibimbap-coreen',
 'Le bibimbap coréen : riz chaud garni de légumes assaisonnés, bœuf sauté, œuf et sauce gochujang épicée.',
 '[{"step":1,"text":"Cuire le riz coréen à grains courts. Préparer les namul : blanchir séparément épinards, carottes râpées et courgettes. Assaisonner chaque légume avec sésame, ail, sauce soja et huile de sésame."},{"step":2,"text":"Mariner le bœuf émincé dans sauce soja, sucre, ail, huile de sésame et poivre. Faire sauter à feu vif."},{"step":3,"text":"Faire revenir les shiitakés coupés en lamelles dans un peu d''huile."},{"step":4,"text":"Préparer la sauce gochujang : mélanger gochujang, huile de sésame, vinaigre de riz, sucre et ail."},{"step":5,"text":"Servir dans un bol chaud : riz, légumes disposés par section, bœuf au centre, œuf au plat par-dessus. Ajouter la sauce et mélanger énergiquement avant de manger."}]'::jsonb,
 2, 40, 20, 2, 'coréenne', ARRAY['riz','bœuf','végétarien-adaptable','sans-gluten','sans-lactose','toute-saison'], 0.89),

(gen_random_uuid(), 'curated', 'Curry vert thaï au poulet', 'curry-vert-thai-au-poulet',
 'Le curry vert thaïlandais : poulet fondant dans une sauce au lait de coco parfumée à la pâte de curry vert et basilic thaï.',
 '[{"step":1,"text":"Faire chauffer une cuillère de pâte de curry vert dans une casserole avec un peu d''huile. Faire sauter 2 min jusqu''à ce que les arômes se libèrent."},{"step":2,"text":"Verser 40 cl de lait de coco, porter à frémissement. Ajouter les blancs de poulet coupés en morceaux."},{"step":3,"text":"Ajouter sauce poisson, sucre de palme, feuilles de kaffir et tiges de citronnelle écrasées."},{"step":4,"text":"Cuire 15 min à feu doux. Ajouter aubergines thaïes et pois mange-tout les 5 dernières minutes."},{"step":5,"text":"Hors du feu, incorporer le basilic thaï. Servir avec du riz jasmin et quartiers de citron vert."}]'::jsonb,
 4, 15, 25, 2, 'thaïlandaise', ARRAY['poulet','curry','noix-de-coco','sans-gluten','sans-lactose','toute-saison','épicé'], 0.91),

(gen_random_uuid(), 'curated', 'Nems vietnamiens croustillants', 'nems-vietnamiens-croustillants',
 'Des nems croustillants maison farcis de porc, crevettes, vermicelles et champignons noirs, frits à l''or.',
 '[{"step":1,"text":"Tremper les vermicelles de riz 10 min dans l''eau tiède. Réhydrater les champignons noirs séchés 20 min."},{"step":2,"text":"Mélanger 200g de porc haché, 100g de crevettes hachées, vermicelles et champignons émincés, carottes râpées, échalotes, ail, sauce poisson et poivre."},{"step":3,"text":"Tremper les feuilles de riz rapidement dans l''eau tiède. Poser sur un torchon humide."},{"step":4,"text":"Déposer une cuillère de farce, plier les côtés et rouler serré. Réserver sur un plateau fariné."},{"step":5,"text":"Faire frire les nems dans l''huile à 170°C pendant 4-5 min jusqu''à dorure et croustillant. Servir avec salade et sauce nuoc cham."}]'::jsonb,
 4, 45, 20, 3, 'vietnamienne', ARRAY['porc','crevettes','friture','apéritif','entrée','sans-lactose'], 0.87),

(gen_random_uuid(), 'curated', 'Gyoza japonais poêlés', 'gyoza-japonais-poeles',
 'Les gyoza japonais : raviolis farcis au porc et chou chinois, croustillants en dessous et vapeur au-dessus.',
 '[{"step":1,"text":"Mélanger 250g de porc haché avec du chou chinois finement émincé (bien essoré), ail, gingembre, sauce soja, huile de sésame et sel."},{"step":2,"text":"Placer une cuillère de farce au centre d''une galette à gyoza. Humidifier le bord, replier en demi-lune et plisser soigneusement."},{"step":3,"text":"Faire chauffer une poêle anti-adhésive avec un peu d''huile. Disposer les gyoza à plat. Faire dorer la base 2 min."},{"step":4,"text":"Verser 10 cl d''eau chaude dans la poêle et couvrir immédiatement. Cuire à la vapeur 5 min jusqu''à évaporation complète."},{"step":5,"text":"Retirer le couvercle, laisser dorer encore 1 min. Servir face croustillante vers le haut avec sauce dipping soja-vinaigre-piment."}]'::jsonb,
 4, 45, 10, 3, 'japonaise', ARRAY['porc','raviolis','apéritif','entrée','sans-lactose','toute-saison'], 0.88),

(gen_random_uuid(), 'curated', 'Bol de riz sushi et sashimis', 'chirashi-sushi-bowl',
 'Le chirashi sushi bowl : riz vinaigré garni de sashimis de saumon et thon, avocat et gingembre mariné.',
 '[{"step":1,"text":"Cuire 300g de riz japonais. Assaisonner chaud avec un mélange de vinaigre de riz, sucre et sel. Refroidir en éventant."},{"step":2,"text":"Préparer les garnitures : trancher en sashimis 200g de saumon et 150g de thon de qualité sashimi-grade. Couper l''avocat en tranches."},{"step":3,"text":"Préparer la sauce ponzu ou servir du soja + wasabi + gingembre mariné."},{"step":4,"text":"Répartir le riz dans des bols. Disposer harmonieusement les sashimis, l''avocat, le gingembre et les graines de sésame."},{"step":5,"text":"Servir avec wasabi, soja réduit en sel et thé vert japonais."}]'::jsonb,
 2, 30, 20, 2, 'japonaise', ARRAY['poisson','riz','saumon','sans-gluten','sans-lactose','été','premium'], 0.87),

-- ============================================================
-- RECETTES INDIENNES (6)
-- ============================================================

(gen_random_uuid(), 'curated', 'Poulet tikka masala', 'poulet-tikka-masala',
 'Le tikka masala : poulet mariné au yaourt et épices, grillé puis mijoté dans une sauce tomate crémeuse parfumée.',
 '[{"step":1,"text":"Mariner les morceaux de poulet 4h dans : yaourt nature, garam masala, curcuma, paprika fumé, gingembre et ail râpés, sel et jus de citron."},{"step":2,"text":"Griller le poulet mariné au four à 220°C (15 min) ou sous le gril jusqu''à légère carbonisation des bords."},{"step":3,"text":"Préparer la sauce : faire revenir oignons, ail et gingembre dans du beurre clarifié. Ajouter épices (garam masala, cumin, coriandre, cardamome). Cuire 2 min."},{"step":4,"text":"Incorporer les tomates concassées, cuire 15 min. Mixer. Ajouter 20 cl de crème fraîche et mijoter 10 min."},{"step":5,"text":"Incorporer le poulet grillé dans la sauce, réchauffer 5 min. Parsemer de coriandre fraîche. Servir avec du riz basmati et des naans."}]'::jsonb,
 4, 30, 40, 2, 'indienne', ARRAY['poulet','curry','crème','sans-gluten','toute-saison','épicé'], 0.92),

(gen_random_uuid(), 'curated', 'Dal de lentilles corail aux épices', 'dal-lentilles-corail',
 'Le dal de lentilles corail : fondant, parfumé au cumin et curcuma, avec un tarka d''épices grillées à l''huile.',
 '[{"step":1,"text":"Rincer 300g de lentilles corail. Les cuire 20 min dans 750 ml d''eau avec curcuma, gingembre râpé et sel jusqu''à consistance crémeuse."},{"step":2,"text":"Préparer le tarka : chauffer 3 cuil. à soupe d''huile dans une petite casserole. Faire grésiller graines de cumin, graines de moutarde et feuilles de curry."},{"step":3,"text":"Ajouter ail émincé, oignon haché et piment vert. Faire dorer. Incorporer tomates concassées et cuire 5 min."},{"step":4,"text":"Verser le tarka sur les lentilles cuites. Bien mélanger et laisser infuser 5 min."},{"step":5,"text":"Servir avec du riz basmati ou des naans. Garnir de coriandre fraîche et d''un trait de jus de citron."}]'::jsonb,
 4, 10, 30, 1, 'indienne', ARRAY['lentilles','vegan','végétarien','sans-gluten','sans-lactose','économique','toute-saison'], 0.89),

(gen_random_uuid(), 'curated', 'Naans au beurre maison', 'naans-au-beurre-maison',
 'Les naans moelleux cuits à la poêle bien chaude, garnis de beurre clarifié et ail : irrésistibles à l''apéritif.',
 '[{"step":1,"text":"Mélanger 300g de farine, 1 cuil. à café de levure instantanée, 1 cuil. à café de sucre et 1 pincée de sel. Creuser un puits."},{"step":2,"text":"Ajouter 150g de yaourt nature et 80 ml d''eau tiède. Pétrir 10 min jusqu''à obtenir une pâte lisse. Laisser lever 1h sous un torchon."},{"step":3,"text":"Diviser la pâte en 6 boules. Étaler chaque boule en ovale fin de 5 mm d''épaisseur."},{"step":4,"text":"Faire chauffer une poêle à fond épais ou une plancha à feu très vif. Cuire chaque naan 2-3 min par côté jusqu''à formation de bulles dorées."},{"step":5,"text":"Badigeonner immédiatement de beurre clarifié et ail haché. Parsemer de coriandre ciselée si désiré."}]'::jsonb,
 6, 20, 20, 2, 'indienne', ARRAY['pain','végétarien','apéritif','toute-saison','familial'], 0.87),

(gen_random_uuid(), 'curated', 'Biryani de poulet au safran', 'biryani-poulet-safran',
 'Le biryani de poulet : riz basmati parfumé au safran, poulet mariné aux épices et oignons frits croustillants.',
 '[{"step":1,"text":"Mariner le poulet 2h dans yaourt, garam masala, curcuma, piment rouge, ail et gingembre."},{"step":2,"text":"Faire frire des rondelles d''oignons jusqu''à coloration dorée et croustillante. Égoutter."},{"step":3,"text":"Cuire le poulet mariné dans du beurre clarifié avec épices entières (cardamome, cannelle, clous de girofle) jusqu''à mi-cuisson."},{"step":4,"text":"Cuire le riz basmati à 70% dans de l''eau safranée. Égoutter."},{"step":5,"text":"Alterner dans la cocotte : poulet, riz, oignons frits. Fermer hermétiquement et cuire 25 min à feu doux (dum). Servir en déposant délicatement les couches."}]'::jsonb,
 6, 30, 60, 4, 'indienne', ARRAY['poulet','riz','sans-gluten','toute-saison','premium','épicé'], 0.91),

(gen_random_uuid(), 'curated', 'Samosa maison aux légumes', 'samosa-maison-aux-legumes',
 'Des samosas croustillants farcis aux pommes de terre épicées, petits pois et coriandre, frits jusqu''à dorure.',
 '[{"step":1,"text":"Préparer la farce : faire revenir dans l''huile graines de cumin, ail et gingembre. Ajouter pommes de terre cuites en dés, petits pois, garam masala, curcuma, sel et coriandre fraîche hachée."},{"step":2,"text":"Préparer la pâte : mélanger 250g de farine, 1 cuil. à café de sel, 4 cuil. à soupe d''huile et de l''eau tiède pour former une pâte ferme. Reposer 30 min."},{"step":3,"text":"Diviser la pâte en boules, étaler en disques, couper en demi-lune. Former un cône, remplir de farce et sceller."},{"step":4,"text":"Frire les samosas à 170°C environ 5-6 min jusqu''à dorure uniforme et croustillant."},{"step":5,"text":"Égoutter sur du papier absorbant. Servir avec chutney à la menthe et chutney tamarin."}]'::jsonb,
 4, 40, 30, 3, 'indienne', ARRAY['végétarien','vegan','apéritif','entrée','sans-lactose','toute-saison'], 0.86),

(gen_random_uuid(), 'curated', 'Palak paneer épinards-fromage', 'palak-paneer-epinards-fromage',
 'Le palak paneer : fromage indien ferme dans une sauce crémeuse aux épinards et épices. Végétarien et généreux.',
 '[{"step":1,"text":"Blanchir 500g d''épinards 2 min dans l''eau bouillante. Refroidir et mixer en purée lisse avec un peu d''eau."},{"step":2,"text":"Faire dorer les cubes de paneer dans du beurre clarifié. Réserver."},{"step":3,"text":"Dans la même poêle, faire suer oignons, ail et gingembre. Ajouter garam masala, cumin et coriandre en poudre."},{"step":4,"text":"Incorporer la purée d''épinards, un peu de crème fraîche et sel. Mijoter 10 min."},{"step":5,"text":"Ajouter le paneer doré, mélanger délicatement. Servir avec du riz basmati ou des chapatis."}]'::jsonb,
 4, 20, 25, 2, 'indienne', ARRAY['végétarien','épinards','fromage','sans-gluten','toute-saison','épicé'], 0.88),

-- ============================================================
-- RECETTES MEXICAINES (6)
-- ============================================================

(gen_random_uuid(), 'curated', 'Tacos al pastor maison', 'tacos-al-pastor-maison',
 'Les tacos al pastor : porc mariné aux épices et ananas, grillé et servi dans des tortillas avec coriandre et oignon.',
 '[{"step":1,"text":"Préparer la marinade al pastor : guajillo séché réhydraté, ancho, chipotle en adobo, ananas, ail, vinaigre de cidre, cumin, origan mexicain, sel. Mixer."},{"step":2,"text":"Couper le porc (échine) en tranches fines. Mariner 4h ou toute la nuit dans la marinade al pastor."},{"step":3,"text":"Faire griller le porc à feu vif dans une poêle ou sur le gril jusqu''à légère carbonisation des bords. Hacher grossièrement."},{"step":4,"text":"Faire chauffer les tortillas de maïs directement sur la flamme ou à la poêle sèche."},{"step":5,"text":"Garnir les tortillas de porc grillé, oignon blanc ciselé, coriandre fraîche, ananas en dés et salsa verde. Servir avec quartiers de citron vert."}]'::jsonb,
 4, 30, 20, 2, 'mexicaine', ARRAY['porc','tacos','sans-gluten','sans-lactose','épicé','été','familial'], 0.91),

(gen_random_uuid(), 'curated', 'Guacamole frais maison', 'guacamole-frais-maison',
 'Le guacamole authentique : avocats mûrs écrasés avec citron vert, coriandre, oignon rouge et piment jalapeño.',
 '[{"step":1,"text":"Couper 3 avocats mûrs en deux, retirer le noyau. Prélever la chair à la cuillère."},{"step":2,"text":"Écraser grossièrement la chair d''avocat à la fourchette — ne pas mixer pour garder du relief."},{"step":3,"text":"Incorporer le jus de 2 citrons verts, 1/2 oignon rouge finement ciselé, 1 piment jalapeño épépiné haché, 1/2 tomate en dés épépinée."},{"step":4,"text":"Ajouter une généreuse poignée de coriandre fraîche hachée, sel et poivre. Mélanger."},{"step":5,"text":"Glisser le noyau au centre pour limiter l''oxydation. Couvrir au contact de film plastique. Servir immédiatement avec chips de tortilla."}]'::jsonb,
 4, 10, 0, 1, 'mexicaine', ARRAY['avocat','vegan','végétarien','sans-gluten','sans-lactose','express','apéritif','été'], 0.89),

(gen_random_uuid(), 'curated', 'Enchiladas au poulet et mole', 'enchiladas-poulet-mole',
 'Des enchiladas moelleuses garnies de poulet effiloché, nappées de mole rouge maison et fromage fondu.',
 '[{"step":1,"text":"Cuire et effilocher 600g de poitrine de poulet dans un bouillon épicé. Réserver."},{"step":2,"text":"Préparer la sauce mole : réhydrater piments ancho et mulato séchés. Mixer avec tomates grillées, ail, cannelle, cumin, chocolat noir 70% et bouillon de poulet. Cuire 20 min."},{"step":3,"text":"Faire chauffer les tortillas de maïs dans une poêle huilée, les tremper rapidement dans la sauce mole."},{"step":4,"text":"Garnir chaque tortilla de poulet effiloché et d''oignon, rouler et déposer dans un plat à gratin."},{"step":5,"text":"Napper du reste de mole, parsemer de fromage râpé (Oaxaca ou cheddar). Gratiner 15 min à 200°C. Garnir de crème, coriandre et oignon rouge."}]'::jsonb,
 6, 40, 40, 3, 'mexicaine', ARRAY['poulet','épicé','sans-gluten','familial','toute-saison'], 0.87),

(gen_random_uuid(), 'curated', 'Chili con carne authentique', 'chili-con-carne-authentique',
 'Le chili con carne texan : bœuf haché, haricots rouges, piments chipotle et cumin mijoté pour une sauce épaisse et fumée.',
 '[{"step":1,"text":"Faire revenir 800g de bœuf haché grossièrement dans une cocotte jusqu''à coloration. Réserver."},{"step":2,"text":"Dans la même cocotte, faire suer 2 oignons, 4 gousses d''ail et 2 poivrons. Ajouter 2 piments chipotle en adobo hachés."},{"step":3,"text":"Incorporer cumin moulu, poudre de chili, origan, sel et coriandre. Cuire les épices 2 min."},{"step":4,"text":"Ajouter la viande, les tomates concassées et 50 cl de bouillon de bœuf. Mijoter 45 min à feu doux."},{"step":5,"text":"Ajouter les haricots rouges égouttés les 15 dernières minutes. Ajuster l''assaisonnement. Servir avec riz, crème et coriandre."}]'::jsonb,
 6, 20, 60, 2, 'mexicaine', ARRAY['bœuf','haricots','épicé','sans-gluten','sans-lactose','hiver','familial','économique'], 0.89),

(gen_random_uuid(), 'curated', 'Quesadillas au fromage et jalapeños', 'quesadillas-fromage-jalapeños',
 'Les quesadillas croustillantes dorées à la poêle : fromage fondu et jalapeños dans des tortillas de blé.',
 '[{"step":1,"text":"Râper généreusement du fromage Oaxaca ou cheddar (ou mélange mozzarella-mimolette)."},{"step":2,"text":"Déposer une tortilla de farine dans une poêle sèche chauffée à feu moyen."},{"step":3,"text":"Couvrir une moitié de fromage râpé, quelques rondelles de jalapeños et coriandre ciselée."},{"step":4,"text":"Replier la tortilla en demi-lune. Appuyer légèrement avec une spatule. Cuire 2 min par côté jusqu''à fromage fondu et tortilla dorée."},{"step":5,"text":"Couper en triangles. Servir avec guacamole, salsa et crème fraîche."}]'::jsonb,
 2, 5, 10, 1, 'mexicaine', ARRAY['végétarien','fromage','rapide','express','apéritif','enfants'], 0.85),

(gen_random_uuid(), 'curated', 'Ceviche de poisson blanc', 'ceviche-de-poisson-blanc',
 'Le ceviche péruvien-mexicain : poisson blanc ''cuit'' dans le jus de citron vert avec tomates, concombre et coriandre.',
 '[{"step":1,"text":"Couper 500g de filet de poisson blanc très frais (cabillaud, dorade) en dés de 1 cm. Déposer dans un plat."},{"step":2,"text":"Couvrir généreusement du jus de 8 citrons verts et du jus de 2 oranges. Saler. Laisser mariner 20 min au réfrigérateur."},{"step":3,"text":"Pendant ce temps, préparer tomates épépinées en dés, concombre épépiné en dés, oignon rouge ciselé, coriandre fraîche et piment rouge haché."},{"step":4,"text":"Lorsque le poisson a blanchi (''cuit'' à l''acide), incorporer les légumes et le piment délicatement."},{"step":5,"text":"Servir dans des verres ou des verrines avec des chips de plantain ou de tortilla. Consommer dans l''heure."}]'::jsonb,
 4, 30, 0, 2, 'mexicaine', ARRAY['poisson','sans-cuisson','été','sans-gluten','sans-lactose','entrée','léger'], 0.87),

-- ============================================================
-- RECETTES LIBANAISES / MÉDITERRANÉENNES (6)
-- ============================================================

(gen_random_uuid(), 'curated', 'Houmous maison onctueux', 'houmous-maison-onctueux',
 'Le houmous libanais parfait : pois chiches mixés avec tahini, citron, ail et huile d''olive. Lisse et soyeux.',
 '[{"step":1,"text":"Faire tremper 300g de pois chiches secs 12h dans l''eau froide. Cuire 1h30 avec 1/2 cuil. à café de bicarbonate jusqu''à très tendreté. Ou utiliser 800g de pois chiches en conserve bien rincés."},{"step":2,"text":"Mixer les pois chiches encore chauds dans un robot puissant avec 4 cuil. à soupe de tahini, jus de 2 citrons, 1 gousse d''ail et 1 cuil. à café de sel."},{"step":3,"text":"Ajouter 3-4 cuil. à soupe d''eau glacée progressivement en mixant pour alléger la texture."},{"step":4,"text":"Goûter et ajuster tahini, citron et sel. Mixer encore 3 min pour obtenir une texture parfaitement lisse."},{"step":5,"text":"Servir dans un plat creusé au centre, garnir d''un filet d''huile d''olive, paprika fumé et persil haché. Accompagner de pita chaude."}]'::jsonb,
 6, 20, 90, 1, 'libanaise', ARRAY['pois-chiches','vegan','végétarien','sans-gluten','sans-lactose','apéritif','toute-saison','économique'], 0.92),

(gen_random_uuid(), 'curated', 'Taboulé libanais au persil', 'tabboule-libanais-au-persil',
 'Le vrai taboulé libanais : une mer de persil frais avec peu de boulgour, tomates, menthe et vinaigrette citronnée.',
 '[{"step":1,"text":"Laver et sécher soigneusement 4 grosses bottes de persil plat. Effeuiller et hacher très finement au couteau (ne pas mixer)."},{"step":2,"text":"Hydrater 60g de boulgour fin dans l''eau froide 15 min. Égoutter et essuyer."},{"step":3,"text":"Couper 4 tomates fermes en très petits dés. Saler légèrement et égoutter."},{"step":4,"text":"Ciseler finement 1 botte de menthe fraîche. Émincer 4 oignons verts."},{"step":5,"text":"Mélanger persil, boulgour, tomates, menthe et oignons verts. Assaisonner généreusement avec jus de citron, huile d''olive extra vierge et sel. Le jus de citron doit dominer. Réfrigérer 30 min avant de servir."}]'::jsonb,
 6, 30, 0, 1, 'libanaise', ARRAY['persil','vegan','végétarien','sans-gluten','sans-lactose','été','léger','apéritif'], 0.90),

(gen_random_uuid(), 'curated', 'Falafels croustillants maison', 'falafels-croustillants-maison',
 'Des falafels croustillants à base de pois chiches crus et herbes fraîches, frits et servis en pita avec tarator.',
 '[{"step":1,"text":"IMPORTANT : utiliser des pois chiches secs trempés 24h (pas en conserve) — le résultat est incomparable. Égoutter sans cuire."},{"step":2,"text":"Mixer les pois chiches avec oignon, ail, persil, coriandre, cumin, coriandre moulue, sel, bicarbonate et farine de pois chiche. La texture doit être granuleuse, pas lisse."},{"step":3,"text":"Réfrigérer la pâte 1h. Former des boulettes aplaties avec une cuillère ou un moule à falafel."},{"step":4,"text":"Frire à 175°C pendant 3-4 min jusqu''à coloration brun-doré. Égoutter sur du papier absorbant."},{"step":5,"text":"Servir dans des pitas avec salade, tomates, tarator (tahini + citron + ail + eau), concombre et pickles."}]'::jsonb,
 4, 30, 15, 2, 'libanaise', ARRAY['pois-chiches','vegan','végétarien','sans-gluten','sans-lactose','toute-saison'], 0.91),

(gen_random_uuid(), 'curated', 'Moussaka grecque gratinée', 'moussaka-grecque-gratinee',
 'La moussaka grecque : aubergines grillées, farce d''agneau épicée et béchamel gratinée. Un plat de fête méditerranéen.',
 '[{"step":1,"text":"Couper 2 grosses aubergines en rondelles de 1 cm. Badigeonner d''huile d''olive, saler et griller au four 20 min à 200°C en retournant à mi-cuisson."},{"step":2,"text":"Faire revenir 600g d''agneau haché avec oignons et ail. Ajouter tomates concassées, cannelle, allspice, origan et vin rouge. Mijoter 20 min jusqu''à sauce épaisse."},{"step":3,"text":"Préparer une béchamel épaisse : roux beurre-farine, lait, œuf, fromage kefalotyri (ou parmesan) râpé, sel et muscade."},{"step":4,"text":"Dans un plat à gratin, alterner : aubergines grillées, farce d''agneau, aubergines."},{"step":5,"text":"Napper généreusement de béchamel. Saupoudrer de fromage râpé. Cuire 45 min à 180°C jusqu''à dorure. Laisser reposer 15 min avant de couper."}]'::jsonb,
 8, 40, 85, 3, 'grecque', ARRAY['agneau','aubergines','hiver','familial','méditerranéen','toute-saison'], 0.90),

(gen_random_uuid(), 'curated', 'Shakshuka aux poivrons', 'shakshuka-aux-poivrons',
 'La shakshuka épicée : œufs pochés dans une sauce tomate et poivrons parfumée au cumin et à la harissa.',
 '[{"step":1,"text":"Faire chauffer de l''huile d''olive dans une grande poêle. Faire suer 1 oignon et 3 gousses d''ail. Ajouter 2 poivrons en dés."},{"step":2,"text":"Incorporer 1 cuil. à café de cumin, 1 cuil. à café de paprika fumé et 1 cuil. à soupe de harissa. Cuire 2 min."},{"step":3,"text":"Ajouter 800g de tomates pelées concassées, sel et poivre. Mijoter 15 min à feu moyen jusqu''à sauce épaisse."},{"step":4,"text":"Creuser 4 à 6 puits dans la sauce. Casser un œuf dans chaque puits."},{"step":5,"text":"Couvrir et cuire 5-8 min jusqu''à ce que les blancs soient pris mais les jaunes encore coulants. Parsemer de feta émiettée, coriandre et servir avec du pain pita."}]'::jsonb,
 4, 10, 30, 1, 'libanaise', ARRAY['œufs','végétarien','sans-gluten','sans-lactose','toute-saison','économique','brunch'], 0.90),

(gen_random_uuid(), 'curated', 'Fattoush salade du Levant', 'fattoush-salade-du-levant',
 'Le fattoush libanais : salade croquante de légumes frais, pain pita grillé et vinaigrette sumac acidulée.',
 '[{"step":1,"text":"Faire griller ou frire des morceaux de pita jusqu''à ce qu''ils soient dorés et croustillants."},{"step":2,"text":"Couper en morceaux grossiers : 3 tomates, 2 concombres libanais, 4 radis, 4 oignons verts et 1 cœur de romaine."},{"step":3,"text":"Effeuiller persil plat et menthe fraîche."},{"step":4,"text":"Préparer la vinaigrette au sumac : jus de citron, huile d''olive, 2 cuil. à café de sumac, sel, poivre et une pointe d''ail."},{"step":5,"text":"Mélanger légumes et herbes, arroser de vinaigrette. Ajouter les chips de pita au dernier moment pour conserver le croustillant. Servir immédiatement."}]'::jsonb,
 4, 15, 10, 1, 'libanaise', ARRAY['salade','végétarien','vegan','été','léger','entrée','rapide'], 0.86),

-- ============================================================
-- RECETTES RAPIDES (< 20 MIN) (6)
-- ============================================================

(gen_random_uuid(), 'curated', 'Omelette aux herbes express', 'omelette-aux-herbes-express',
 'L''omelette baveuse aux herbes fraîches : cuite en 3 minutes, moelleuse à cœur et parfumée au ciboulette et cerfeuil.',
 '[{"step":1,"text":"Casser 3 œufs par personne dans un bol. Battre vigoureusement à la fourchette avec sel, poivre et une pincée d''eau (pas de lait)."},{"step":2,"text":"Ciseler finement ciboulette, cerfeuil et persil plat. Incorporer aux œufs battus."},{"step":3,"text":"Faire chauffer une poêle anti-adhésive à feu vif avec du beurre jusqu''à ce qu''il mousse et commence à dorer."},{"step":4,"text":"Verser les œufs d''un coup. Agiter la poêle et remuer rapidement les œufs avec une spatule pour former de gros plis."},{"step":5,"text":"Avant que l''omelette soit complètement prise, rouler d''un coup de poignet sur l''assiette, face non colorée vers le haut. Servir immédiatement."}]'::jsonb,
 1, 5, 4, 1, 'française', ARRAY['œufs','végétarien','sans-gluten','express','rapide','toute-saison','économique'], 0.85),

(gen_random_uuid(), 'curated', 'Salade César au poulet grillé', 'salade-cesar-poulet-grille',
 'La salade César complète : laitue romaine, escalopes grillées, croûtons dorés et sauce César maison crémeuse.',
 '[{"step":1,"text":"Préparer la sauce César : mixer 1 jaune d''œuf, 2 anchois, 1 gousse d''ail, jus de citron, sauce Worcestershire. Incorporer en filet 10 cl d''huile d''olive pour émulsionner. Ajouter parmesan râpé."},{"step":2,"text":"Faire griller les escalopes de poulet assaisonnées sel, poivre, herbes de Provence sur une poêle-gril bien chaude. Trancher en lamelles."},{"step":3,"text":"Faire dorer des cubes de baguette rassis au beurre avec ail jusqu''à croustillant doré."},{"step":4,"text":"Déchirer la romaine en feuilles. Mélanger délicatement avec la sauce César."},{"step":5,"text":"Dresser la salade dans des assiettes, disposer le poulet grillé et les croûtons. Parsemer de copeaux de parmesan et poivre moulu."}]'::jsonb,
 2, 15, 15, 2, 'américaine', ARRAY['salade','poulet','rapide','toute-saison','entrée','sans-lactose'], 0.87),

(gen_random_uuid(), 'curated', 'Wraps thon avocat épicé', 'wraps-thon-avocat-epice',
 'Des wraps express au thon, avocat écrasé, concombre et sauce sriracha : lunch healthy prêt en 10 min.',
 '[{"step":1,"text":"Égoutter une boîte de thon au naturel (185g). Écraser 1 avocat mûr avec sel, poivre et quelques gouttes de jus de citron."},{"step":2,"text":"Couper le concombre en bâtonnets fins. Émincer la ciboulette ou les oignons verts."},{"step":3,"text":"Mélanger le thon avec une cuil. à soupe de mayonnaise allégée, une cuil. à café de sriracha et sel."},{"step":4,"text":"Étaler l''avocat écrasé sur les tortillas. Répartir la préparation au thon, les bâtonnets de concombre et les oignons verts."},{"step":5,"text":"Rouler serré. Couper en deux en biais. Servir immédiatement ou conserver 2h au réfrigérateur filmé."}]'::jsonb,
 2, 10, 0, 1, 'américaine', ARRAY['thon','avocat','express','rapide','sans-cuisson','léger','toute-saison'], 0.84),

(gen_random_uuid(), 'curated', 'Pâtes aglio e olio en 12 minutes', 'pates-aglio-e-olio',
 'La pasta aglio e olio napolitaine en 12 minutes : spaghetti cuits à la perfection, ail doré et huile d''olive infusée.',
 '[{"step":1,"text":"Porter une grande casserole d''eau à ébullition. Saler généreusement (l''eau doit avoir le goût de la mer). Cuire 350g de spaghetti selon les indications, al dente."},{"step":2,"text":"Pendant la cuisson des pâtes, émincer finement 6 gousses d''ail. Faire chauffer doucement 8 cuil. à soupe d''huile d''olive dans une grande poêle."},{"step":3,"text":"Ajouter l''ail et faire dorer très lentement à feu doux — l''ail ne doit surtout pas brûler. Ajouter du piment rouge séché selon goût."},{"step":4,"text":"Réserver 2 louches d''eau de cuisson des pâtes. Égoutter les spaghetti."},{"step":5,"text":"Verser les pâtes dans la poêle avec l''huile aillée. Ajouter l''eau de cuisson progressivement en remuant pour créer une émulsion. Parsemer de persil haché et parmesan si désiré."}]'::jsonb,
 2, 5, 12, 1, 'italienne', ARRAY['pâtes','vegan','végétarien','rapide','économique','toute-saison','sans-lactose'], 0.88),

(gen_random_uuid(), 'curated', 'Smoothie bowl tropical express', 'smoothie-bowl-tropical-express',
 'Un smoothie bowl tropical coloré et nutritif : mangue, banane et lait de coco, garni de granola et fruits frais.',
 '[{"step":1,"text":"Mixer ensemble : 1 mangue congelée, 1 banane congelée, 5 cl de lait de coco et 2 cuil. à soupe de yaourt grec. La texture doit être épaisse."},{"step":2,"text":"Si trop épais, ajouter un peu de lait de coco. Si trop liquide, ajouter de la mangue ou de la banane congelée."},{"step":3,"text":"Verser dans un bol."},{"step":4,"text":"Garnir joliment : granola croustillant, tranches de kiwi, fraises coupées, fruits de la passion et copeaux de noix de coco."},{"step":5,"text":"Arroser d''un filet de miel ou sirop d''agave. Servir immédiatement."}]'::jsonb,
 1, 10, 0, 1, 'internationale', ARRAY['végétarien','vegan-adaptable','express','été','petit-déjeuner','sans-gluten'], 0.84),

(gen_random_uuid(), 'curated', 'Bruschetta aux champignons aillés', 'bruschetta-champignons-ailles',
 'Des bruschetta généreuses aux champignons sautés à l''ail, thym et persil sur pain de campagne grillé.',
 '[{"step":1,"text":"Nettoyer et couper 400g de champignons de Paris et shiitakés en lamelles."},{"step":2,"text":"Faire chauffer une grande poêle à feu vif avec huile d''olive. Saisir les champignons sans les remuer 2 min pour les dorer."},{"step":3,"text":"Ajouter ail émincé, thym frais et sel. Sauter encore 2 min. Parsemer de persil haché hors du feu."},{"step":4,"text":"Toaster des tranches de pain de campagne et les frotter d''ail."},{"step":5,"text":"Répartir les champignons sautés sur les toasts. Finir d''un filet d''huile d''olive et quelques feuilles de persil. Servir immédiatement."}]'::jsonb,
 4, 5, 10, 1, 'italienne', ARRAY['champignons','végétarien','vegan','rapide','apéritif','entrée','toute-saison'], 0.85),

-- ============================================================
-- RECETTES VÉGÉTARIENNES / VEGAN (8)
-- ============================================================

(gen_random_uuid(), 'curated', 'Buddha bowl quinoa et légumes rôtis', 'buddha-bowl-quinoa-legumes-rotis',
 'Un buddha bowl nutritif : quinoa, légumes rôtis colorés, avocat, edamame et sauce tahini-citron.',
 '[{"step":1,"text":"Préchauffer le four à 200°C. Couper en dés patate douce, courgette, poivrons et betterave. Enrober d''huile d''olive, sel, cumin et paprika. Rôtir 25 min."},{"step":2,"text":"Rincer et cuire le quinoa (1 volume de quinoa pour 2 volumes d''eau bouillante salée). Cuire 15 min, laisser gonfler 5 min à couvert."},{"step":3,"text":"Préparer la sauce tahini : mélanger tahini, jus de citron, ail émincé, eau, sel jusqu''à consistance nappante."},{"step":4,"text":"Préparer les garnitures : trancher l''avocat, cuire les edamame surgelés 3 min, préparer du chou kale massé à l''huile d''olive."},{"step":5,"text":"Assembler les bols : quinoa en base, légumes rôtis, avocat, edamame, kale. Napper de sauce tahini. Parsemer de graines de sésame et piment d''Espelette."}]'::jsonb,
 2, 20, 25, 2, 'internationale', ARRAY['végétarien','vegan','quinoa','sans-gluten','sans-lactose','toute-saison','léger','premium'], 0.89),

(gen_random_uuid(), 'curated', 'Curry de pois chiches et épinards', 'curry-pois-chiches-epinards',
 'Un curry vegan réconfortant : pois chiches fondants et épinards dans une sauce tomate épicée au lait de coco.',
 '[{"step":1,"text":"Faire revenir 1 oignon émincé dans l''huile de coco. Ajouter ail et gingembre râpés, cuire 2 min."},{"step":2,"text":"Incorporer 1 cuil. à soupe de garam masala, 1 cuil. à café de curcuma, 1 cuil. à café de cumin et 1/2 cuil. à café de piment rouge. Griller les épices 1 min."},{"step":3,"text":"Ajouter 400g de tomates concassées en conserve et 40 cl de lait de coco. Porter à ébullition."},{"step":4,"text":"Incorporer 2 boîtes de pois chiches égouttés. Mijoter 15 min."},{"step":5,"text":"Ajouter 200g d''épinards frais ou surgelés. Cuire encore 3 min. Servir avec du riz basmati et du citron vert."}]'::jsonb,
 4, 10, 30, 1, 'indienne', ARRAY['pois-chiches','épinards','vegan','végétarien','sans-gluten','sans-lactose','économique','hiver'], 0.91),

(gen_random_uuid(), 'curated', 'Gratin de chou-fleur au curry', 'gratin-chou-fleur-au-curry',
 'Un gratin réconfortant de chou-fleur rôti nappé d''une béchamel légère au curry et fromage gratiné.',
 '[{"step":1,"text":"Couper 1 chou-fleur en bouquets. Assaisonner d''huile d''olive, sel, curcuma et cumin. Rôtir 20 min à 200°C jusqu''à légère caramélisation."},{"step":2,"text":"Préparer la béchamel au curry : faire un roux beurre-farine. Ajouter lait chaud progressivement. Incorporer 1 cuil. à soupe de curry en poudre, sel et poivre."},{"step":3,"text":"Disposer le chou-fleur rôti dans un plat à gratin."},{"step":4,"text":"Napper de béchamel au curry. Parsemer généreusement de gruyère râpé ou de parmesan."},{"step":5,"text":"Gratiner 20 min à 200°C jusqu''à dorure et bullage. Servir chaud avec du riz ou du pain."}]'::jsonb,
 4, 15, 40, 2, 'internationale', ARRAY['chou-fleur','végétarien','hiver','gratin','toute-saison','économique'], 0.85),

(gen_random_uuid(), 'curated', 'Soupe de lentilles au citron', 'soupe-lentilles-au-citron',
 'Une soupe vegan réconfortante de lentilles corail au cumin et citron frais : soyeuse, dorée et parfumée.',
 '[{"step":1,"text":"Faire suer 1 oignon et 3 gousses d''ail dans l''huile d''olive. Ajouter 1 cuil. à café de cumin et 1/2 cuil. à café de curcuma. Cuire 1 min."},{"step":2,"text":"Verser 300g de lentilles corail rincées et 1 L de bouillon de légumes. Porter à ébullition."},{"step":3,"text":"Mijoter 20 min à feu doux jusqu''à ce que les lentilles soient fondantes et la soupe épaisse."},{"step":4,"text":"Mixer finement. Incorporer le jus d''1 citron. Ajuster sel et consistance avec un peu d''eau si nécessaire."},{"step":5,"text":"Servir avec un filet d''huile d''olive, une pincée de paprika fumé et du pain pita chaud."}]'::jsonb,
 4, 10, 25, 1, 'libanaise', ARRAY['lentilles','vegan','végétarien','sans-gluten','sans-lactose','économique','hiver','rapide'], 0.88),

(gen_random_uuid(), 'curated', 'Burger végétalien aux betteraves', 'burger-vegetalien-aux-betteraves',
 'Un burger vegan gourmand : steak de betterave et noix noires grillé, avocat, salade et mayo végane.',
 '[{"step":1,"text":"Râper finement 300g de betteraves cuites. Mélanger avec 150g de noix noires mixées, 80g de flocons d''avoine, 2 cuil. à soupe de flaxseed + eau, oignon, ail, cumin et sel."},{"step":2,"text":"Former 4 steaks épais. Réfrigérer 30 min pour qu''ils tiennent bien."},{"step":3,"text":"Faire griller les steaks à la poêle huilée 4-5 min par côté jusqu''à croûte dorée. Ils restent tendres à l''intérieur."},{"step":4,"text":"Préparer la mayo végane : mixer noix de cajou trempées, jus de citron, ail et sel."},{"step":5,"text":"Assembler : pain burger toasté, feuilles de salade, steak betterave, avocat tranché, tomate, oignon rouge et mayo cajou."}]'::jsonb,
 4, 45, 15, 3, 'internationale', ARRAY['vegan','végétarien','betterave','sans-lactose','toute-saison','premium'], 0.84),

(gen_random_uuid(), 'curated', 'Risotto de petits pois à la menthe', 'risotto-petits-pois-menthe',
 'Un risotto printanier aux petits pois croquants et feuilles de menthe fraîche, mantecato au pecorino.',
 '[{"step":1,"text":"Chauffer 1 L de bouillon de légumes. Faire suer 1 échalote dans le beurre. Nacrer 320g de riz Arborio 2 min."},{"step":2,"text":"Déglacer avec 10 cl de vin blanc sec. Ajouter le bouillon louche par louche en remuant constamment."},{"step":3,"text":"Après 12 min, mixer 200g de petits pois cuits avec un peu de bouillon pour faire une purée lisse verte. Incorporer dans le risotto."},{"step":4,"text":"Ajouter 200g de petits pois cuits entiers pour la texture."},{"step":5,"text":"Mantecato hors du feu : beurre froid et pecorino râpé. Parsemer de menthe fraîche ciselée et zeste de citron. Servir immédiatement."}]'::jsonb,
 4, 15, 25, 3, 'italienne', ARRAY['végétarien','petits-pois','risotto','printemps','été','sans-gluten'], 0.88),

(gen_random_uuid(), 'curated', 'Tacos de chou-fleur rôti', 'tacos-chou-fleur-roti',
 'Des tacos vegan festifs : chou-fleur rôti aux épices fumées, crème de haricots noirs et salsa verde fraîche.',
 '[{"step":1,"text":"Couper 1 chou-fleur en petits bouquets. Assaisonner de chipotle fumé, cumin, paprika, huile d''olive et sel. Rôtir 25 min à 220°C."},{"step":2,"text":"Mixer 1 boîte de haricots noirs égouttés avec jus de citron, ail, cumin, sel et un peu d''eau : crème onctueuse."},{"step":3,"text":"Préparer la salsa verde : tomatilles (ou tomates vertes), coriandre, piment jalapeño, ail, jus de citron vert. Mixer grossièrement."},{"step":4,"text":"Chauffer les tortillas de maïs sur feu direct ou poêle sèche."},{"step":5,"text":"Garnir : crème de haricots noirs, chou-fleur rôti épicé, salsa verde, coriandre fraîche, avocat tranché et quartier de citron vert."}]'::jsonb,
 4, 20, 25, 2, 'mexicaine', ARRAY['vegan','végétarien','chou-fleur','sans-gluten','sans-lactose','toute-saison'], 0.87),

(gen_random_uuid(), 'curated', 'Velouté de butternut au gingembre', 'veloute-butternut-gingembre',
 'Un velouté de courge butternut soyeux et doré, parfumé au gingembre frais et lait de coco : chaud et réconfortant.',
 '[{"step":1,"text":"Éplucher et couper en dés 1 grosse butternut. Faire revenir à l''huile d''olive avec 1 oignon et 3 cm de gingembre frais râpé."},{"step":2,"text":"Ajouter 1 cuil. à café de curcuma et 1/2 cuil. à café de muscade. Cuire 2 min."},{"step":3,"text":"Couvrir de bouillon de légumes à hauteur. Cuire 20 min à feu moyen jusqu''à tendreté complète."},{"step":4,"text":"Mixer finement au mixeur plongeant. Incorporer 20 cl de lait de coco. Ajuster sel et consistance."},{"step":5,"text":"Servir dans des bols chauds, garnir d''une cuillère de crème de coco, graines de courge torréfiées et un filet d''huile de sésame."}]'::jsonb,
 4, 15, 25, 1, 'internationale', ARRAY['butternut','vegan','végétarien','sans-gluten','sans-lactose','hiver','économique'], 0.89),

-- ============================================================
-- DESSERTS (5)
-- ============================================================

(gen_random_uuid(), 'curated', 'Fondant au chocolat cœur coulant', 'fondant-chocolat-coeur-coulant',
 'Le fondant au chocolat parfait : croustillant dehors, cœur coulant chaud dedans. Prêt en 20 minutes.',
 '[{"step":1,"text":"Préchauffer le four à 200°C. Beurrer et fariner généreusement 6 ramequins individuels."},{"step":2,"text":"Faire fondre au bain-marie 200g de chocolat noir 70% avec 150g de beurre. Laisser tiédir."},{"step":3,"text":"Fouetter 4 œufs entiers + 2 jaunes avec 150g de sucre jusqu''à mélange mousseux."},{"step":4,"text":"Incorporer le chocolat fondu au mélange œuf-sucre. Ajouter 50g de farine tamisée en mélangeant délicatement."},{"step":5,"text":"Répartir dans les ramequins. CUIRE EXACTEMENT 10-11 MIN. Le centre doit être tremblant. Démouler immédiatement sur les assiettes. Servir avec glace vanille."}]'::jsonb,
 6, 10, 11, 2, 'française', ARRAY['dessert','chocolat','végétarien','toute-saison','rapide','premium'], 0.95),

(gen_random_uuid(), 'curated', 'Tarte au citron meringuée', 'tarte-citron-meringuee',
 'La tarte au citron meringuée : curd acidulé de citrons de Menton dans une pâte sablée, meringue italienne brûlée.',
 '[{"step":1,"text":"Préparer la pâte sablée : 200g farine + 100g beurre + 80g sucre glace + 1 œuf + 1 pincée de sel. Sabler, former une boule. Repos 30 min. Foncer et cuire à blanc 15 min à 180°C."},{"step":2,"text":"Préparer le curd citron : zeste + jus de 4 citrons jaunes, 150g sucre, 3 œufs, 100g beurre. Cuire à feu doux en remuant jusqu''à épaississement. Ne pas faire bouillir."},{"step":3,"text":"Verser le curd chaud dans le fond de tarte. Lisser. Réfrigérer 2h."},{"step":4,"text":"Préparer la meringue italienne : cuire 200g de sucre avec 70 ml d''eau à 121°C. Verser en filet sur 3 blancs montés en neige en battant constamment. Continuer jusqu''à refroidissement."},{"step":5,"text":"Napper la tarte de meringue et dorer au chalumeau. Déguster dans la journée."}]'::jsonb,
 8, 40, 30, 4, 'française', ARRAY['dessert','citron','végétarien','toute-saison','pâtisserie','premium'], 0.93),

(gen_random_uuid(), 'curated', 'Mousse au chocolat aérienne', 'mousse-chocolat-aerienne',
 'La mousse au chocolat de grand-mère : légère comme un nuage, chocolatée en profondeur, sans crème ajoutée.',
 '[{"step":1,"text":"Faire fondre 200g de chocolat noir 70% au bain-marie. Laisser tiédir à 45°C."},{"step":2,"text":"Séparer 6 œufs. Fouetter les jaunes avec 2 cuil. à soupe de sucre jusqu''à blanchiment."},{"step":3,"text":"Incorporer le chocolat fondu aux jaunes d''œuf sucrés. Bien mélanger."},{"step":4,"text":"Monter les blancs en neige ferme avec 1 pincée de sel. Ajouter 1 cuil. à soupe de sucre en fin de montage."},{"step":5,"text":"Incorporer 1/3 des blancs énergiquement pour détendre l''appareil. Puis incorporer le reste délicatement en soulevant. Verser dans des verrines. Réfrigérer 2h minimum."}]'::jsonb,
 6, 20, 10, 2, 'française', ARRAY['dessert','chocolat','végétarien','sans-gluten','toute-saison','classique','sans-lactose'], 0.91),

(gen_random_uuid(), 'curated', 'Clafoutis aux cerises', 'clafoutis-aux-cerises',
 'Le clafoutis limousin aux cerises entières non dénoyautées : flan fondant et parfumé, légèrement caramélisé.',
 '[{"step":1,"text":"Préchauffer le four à 180°C. Beurrer et sucrer un plat à gratin de 30 cm."},{"step":2,"text":"Laver et essuyer 500g de cerises. Les conserver entières avec les noyaux (le noyau parfume)."},{"step":3,"text":"Battre 3 œufs avec 100g de sucre jusqu''à blanchiment. Ajouter 60g de farine tamisée."},{"step":4,"text":"Incorporer 30 cl de lait entier et 1 cuil. à soupe de rhum ou de kirsch. Parfumer à la vanille."},{"step":5,"text":"Disposer les cerises dans le plat beurré. Verser l''appareil par-dessus. Enfourner 35-40 min jusqu''à prise et dorure. Saupoudrer de sucre glace tiède. Servir dans le plat."}]'::jsonb,
 6, 15, 40, 1, 'française', ARRAY['dessert','cerises','végétarien','été','classique','familial'], 0.88),

(gen_random_uuid(), 'curated', 'Banoffee pie au caramel', 'banoffee-pie-au-caramel',
 'Le banoffee pie anglais : base de biscuits, caramel toffee fondant, bananes fraîches et chantilly légère.',
 '[{"step":1,"text":"Mixer 200g de biscuits Digestive. Mélanger avec 100g de beurre fondu. Tasser dans un moule de 24 cm. Réfrigérer 30 min."},{"step":2,"text":"Préparer le caramel toffee : faire bouillir une boîte de lait concentré sucré à la casserole en remuant constamment jusqu''à coloration caramel dorée (15-20 min). Ou utiliser du dulce de leche."},{"step":3,"text":"Verser le caramel chaud sur la base biscuit. Réfrigérer 1h."},{"step":4,"text":"Trancher finement 3 bananes et les disposer sur le caramel refroidi."},{"step":5,"text":"Monter 30 cl de crème entière en chantilly avec 2 cuil. à soupe de sucre glace. Napper les bananes. Décorer de cacao en poudre et de copeaux de chocolat."}]'::jsonb,
 8, 30, 20, 2, 'anglaise', ARRAY['dessert','végétarien','caramel','banane','toute-saison','premium'], 0.87)

ON CONFLICT DO NOTHING;
