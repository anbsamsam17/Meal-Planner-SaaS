-- Estimation nutritionnelle locale (categories ingredients + mots-cles)
-- 338 recettes estimees
-- Genere par scripts/estimate_nutrition_local.py
--
-- Nutrition JSONB : calories, protein_g, carbs_g, fat_g, fiber_g
-- Tags de style : protéiné, léger, gourmand

BEGIN;

-- Aligot à l''ancienne
UPDATE recipes SET nutrition = '{"calories": 125, "protein_g": 4.8, "fat_g": 5.0, "carbs_g": 14.7, "fiber_g": 1.9}' WHERE id = 'c98079be-f537-44c3-9271-62b073165c18';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'c98079be-f537-44c3-9271-62b073165c18' AND NOT ('léger' = ANY(tags));

-- Anneaux d''encornets à la provençale
UPDATE recipes SET nutrition = '{"calories": 232, "protein_g": 9.1, "fat_g": 2.3, "carbs_g": 41.8, "fiber_g": 10.1}' WHERE id = 'ddee3d07-5847-4691-8963-01bfab34c82b';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'ddee3d07-5847-4691-8963-01bfab34c82b' AND NOT ('léger' = ANY(tags));

-- Appareil à quiche
UPDATE recipes SET nutrition = '{"calories": 241, "protein_g": 14.8, "fat_g": 16.7, "carbs_g": 7.4, "fiber_g": 0.0}' WHERE id = '8801b83b-c7a0-459d-88fb-637576881859';

-- Artichaut vinaigrette
UPDATE recipes SET nutrition = '{"calories": 116, "protein_g": 3.6, "fat_g": 1.3, "carbs_g": 21.7, "fiber_g": 4.5}' WHERE id = '3522e7d8-c8fa-4dd8-ae46-cb94368267cc';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '3522e7d8-c8fa-4dd8-ae46-cb94368267cc' AND NOT ('léger' = ANY(tags));

-- Aubergines au four
UPDATE recipes SET nutrition = '{"calories": 56, "protein_g": 2.8, "fat_g": 0.6, "carbs_g": 9.4, "fiber_g": 3.8}' WHERE id = '52f9e0af-f14d-4e32-ab8a-5c7e02be581f';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '52f9e0af-f14d-4e32-ab8a-5c7e02be581f' AND NOT ('léger' = ANY(tags));

-- Aubergines farcies au bœuf hâché
UPDATE recipes SET nutrition = '{"calories": 323, "protein_g": 33.2, "fat_g": 14.2, "carbs_g": 14.0, "fiber_g": 3.9}' WHERE id = '73d31175-3c28-4be7-be5b-efb351411e8d';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '73d31175-3c28-4be7-be5b-efb351411e8d' AND NOT ('protéiné' = ANY(tags));

-- Baguettes maison
UPDATE recipes SET nutrition = '{"calories": 608, "protein_g": 14.2, "fat_g": 6.1, "carbs_g": 121.5, "fiber_g": 6.1}' WHERE id = 'ce58e098-afdb-438f-9724-8e1cb38a15c5';

-- Bavarois Framboise Mangue aux Biscuits à la Cuillère Bonne Maman
UPDATE recipes SET nutrition = '{"calories": 224, "protein_g": 8.3, "fat_g": 8.6, "carbs_g": 27.3, "fiber_g": 2.5}' WHERE id = '63369447-d240-41d4-b08d-e26f038b5b58';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '63369447-d240-41d4-b08d-e26f038b5b58' AND NOT ('léger' = ANY(tags));

-- Bavarois framboise
UPDATE recipes SET nutrition = '{"calories": 3317, "protein_g": 135.2, "fat_g": 126.8, "carbs_g": 398.2, "fiber_g": 28.7}' WHERE id = '385aec86-2da1-40a4-86fd-739dd171a599';
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '385aec86-2da1-40a4-86fd-739dd171a599' AND NOT ('gourmand' = ANY(tags));

-- Bavarois framboise et pistache
UPDATE recipes SET nutrition = '{"calories": 234, "protein_g": 9.8, "fat_g": 9.5, "carbs_g": 26.6, "fiber_g": 2.0}' WHERE id = '663a8cf2-50ea-46ff-9e63-46780a5ce971';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '663a8cf2-50ea-46ff-9e63-46780a5ce971' AND NOT ('léger' = ANY(tags));

-- Beignets de carnaval ultra moelleux de ma grand-mère
UPDATE recipes SET nutrition = '{"calories": 438, "protein_g": 12.6, "fat_g": 8.1, "carbs_g": 77.1, "fiber_g": 3.8}' WHERE id = '41a6ae84-dd34-441f-808e-0459db5492f9';

-- Beignets de courgettes râpées faciles
UPDATE recipes SET nutrition = '{"calories": 374, "protein_g": 13.7, "fat_g": 10.5, "carbs_g": 54.7, "fiber_g": 3.9}' WHERE id = 'b3ae0807-0009-434a-9409-91b965a98a77';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'b3ae0807-0009-434a-9409-91b965a98a77' AND NOT ('léger' = ANY(tags));

-- Beignets de fleur de courgette par Laurent Mariotte
UPDATE recipes SET nutrition = '{"calories": 514, "protein_g": 15.9, "fat_g": 5.1, "carbs_g": 98.0, "fiber_g": 13.8}' WHERE id = '6d5f8d73-3b3f-4c6f-82f6-52c396073051';

-- Biscuits banane - coco
UPDATE recipes SET nutrition = '{"calories": 55, "protein_g": 1.2, "fat_g": 0.5, "carbs_g": 11.2, "fiber_g": 0.7}' WHERE id = 'fbda0384-8a4f-4064-a96d-6d98178de78a';

-- Biscuits sablés au beurre
UPDATE recipes SET nutrition = '{"calories": 28, "protein_g": 0.8, "fat_g": 0.6, "carbs_g": 4.7, "fiber_g": 0.2}' WHERE id = '25627761-7f2a-4155-9bc0-d1bbb962da2d';

-- Blanc de poulet au Air Fryer
UPDATE recipes SET nutrition = '{"calories": 364, "protein_g": 48.2, "fat_g": 18.0, "carbs_g": 0.6, "fiber_g": 0.2}' WHERE id = '0f702b3e-7a48-4246-a09f-66123fe09435';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '0f702b3e-7a48-4246-a09f-66123fe09435' AND NOT ('protéiné' = ANY(tags));

-- Blanquette de poulet au Cookeo
UPDATE recipes SET nutrition = '{"calories": 769, "protein_g": 60.2, "fat_g": 24.4, "carbs_g": 73.7, "fiber_g": 6.3}' WHERE id = '4f43245f-9696-4db9-bc50-092de01e5ea6';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '4f43245f-9696-4db9-bc50-092de01e5ea6' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '4f43245f-9696-4db9-bc50-092de01e5ea6' AND NOT ('gourmand' = ANY(tags));

-- Blanquette de veau : recette traditionnelle
UPDATE recipes SET nutrition = '{"calories": 1043, "protein_g": 86.0, "fat_g": 34.3, "carbs_g": 93.2, "fiber_g": 7.0}' WHERE id = 'f296b527-fea0-4957-9234-bf873a66b3a0';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'f296b527-fea0-4957-9234-bf873a66b3a0' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'f296b527-fea0-4957-9234-bf873a66b3a0' AND NOT ('gourmand' = ANY(tags));

-- Blanquette de veau facile au Cookeo
UPDATE recipes SET nutrition = '{"calories": 996, "protein_g": 85.9, "fat_g": 35.2, "carbs_g": 79.7, "fiber_g": 5.9}' WHERE id = '28078977-c56c-4809-beac-5c3af838affe';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '28078977-c56c-4809-beac-5c3af838affe' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '28078977-c56c-4809-beac-5c3af838affe' AND NOT ('gourmand' = ANY(tags));

-- Bobun au bœuf
UPDATE recipes SET nutrition = '{"calories": 471, "protein_g": 33.1, "fat_g": 12.9, "carbs_g": 53.1, "fiber_g": 6.0}' WHERE id = '6238fb7a-faa7-45f9-a664-0289b512ab7d';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '6238fb7a-faa7-45f9-a664-0289b512ab7d' AND NOT ('protéiné' = ANY(tags));

-- Boeuf Bourguignon rapide
UPDATE recipes SET nutrition = '{"calories": 720, "protein_g": 55.6, "fat_g": 21.6, "carbs_g": 72.6, "fiber_g": 4.5}' WHERE id = '3f5dcab6-82c9-4aaf-a02b-db0b410a690b';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '3f5dcab6-82c9-4aaf-a02b-db0b410a690b' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '3f5dcab6-82c9-4aaf-a02b-db0b410a690b' AND NOT ('gourmand' = ANY(tags));

-- Boeuf bourguignon : la vraie recette
UPDATE recipes SET nutrition = '{"calories": 273, "protein_g": 10.5, "fat_g": 6.9, "carbs_g": 40.0, "fiber_g": 7.5}' WHERE id = 'bd1d99a4-85f7-4687-b01c-85c2369079a3';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'bd1d99a4-85f7-4687-b01c-85c2369079a3' AND NOT ('léger' = ANY(tags));

-- Bokit guadeloupéen, le vrai
UPDATE recipes SET nutrition = '{"calories": 935, "protein_g": 22.2, "fat_g": 10.1, "carbs_g": 184.8, "fiber_g": 9.3}' WHERE id = '5f4398f1-2fc1-4401-91d7-ac6223631fe8';

-- Bouchée à la Reine au saumon fumé
UPDATE recipes SET nutrition = '{"calories": 236, "protein_g": 19.4, "fat_g": 12.2, "carbs_g": 11.6, "fiber_g": 1.7}' WHERE id = '3c50f41c-2980-4e7a-aa6f-ffc96f64c238';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '3c50f41c-2980-4e7a-aa6f-ffc96f64c238' AND NOT ('léger' = ANY(tags));

-- Boule auvergnate
UPDATE recipes SET nutrition = '{"calories": 414, "protein_g": 24.9, "fat_g": 17.1, "carbs_g": 38.6, "fiber_g": 1.8}' WHERE id = '7d18f729-a2e9-4757-85d2-2d749c070e44';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '7d18f729-a2e9-4757-85d2-2d749c070e44' AND NOT ('protéiné' = ANY(tags));

-- Bowl cake aux flocons d''avoine
UPDATE recipes SET nutrition = '{"calories": 642, "protein_g": 20.4, "fat_g": 15.2, "carbs_g": 103.2, "fiber_g": 5.0}' WHERE id = '1d8feddb-da93-47e0-9831-78b13782246c';

-- Brioche maison facile
UPDATE recipes SET nutrition = '{"calories": 355, "protein_g": 11.7, "fat_g": 8.9, "carbs_g": 55.8, "fiber_g": 2.7}' WHERE id = '35f5392d-f0fd-436c-9eb6-e39dafd9571f';

-- Brioche perdue salée et roulée au jambon
UPDATE recipes SET nutrition = '{"calories": 1004, "protein_g": 48.4, "fat_g": 30.9, "carbs_g": 128.8, "fiber_g": 11.3}' WHERE id = '0b988bc4-740a-4e43-9585-7952edacdb06';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '0b988bc4-740a-4e43-9585-7952edacdb06' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '0b988bc4-740a-4e43-9585-7952edacdb06' AND NOT ('gourmand' = ANY(tags));

-- Brownies
UPDATE recipes SET nutrition = '{"calories": 307, "protein_g": 9.9, "fat_g": 7.3, "carbs_g": 49.2, "fiber_g": 2.4}' WHERE id = '031f845f-ef35-4565-ba67-448c93fe47ef';

-- Bruschetta (Italie)
UPDATE recipes SET nutrition = '{"calories": 273, "protein_g": 8.8, "fat_g": 2.7, "carbs_g": 51.4, "fiber_g": 8.0}' WHERE id = 'da1c4fff-04a9-456d-ba33-d8b3d52706e1';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'da1c4fff-04a9-456d-ba33-d8b3d52706e1' AND NOT ('léger' = ANY(tags));

-- Bugnes
UPDATE recipes SET nutrition = '{"calories": 291, "protein_g": 9.4, "fat_g": 7.1, "carbs_g": 46.4, "fiber_g": 2.4}' WHERE id = 'e0a2f69c-399a-4ccd-9d73-db1e540d9031';

-- Burger végétarien aux lentilles
UPDATE recipes SET nutrition = '{"calories": 561, "protein_g": 58.5, "fat_g": 22.2, "carbs_g": 28.1, "fiber_g": 6.7}' WHERE id = '7c44d07a-97ac-4426-ac49-318c8313944b';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '7c44d07a-97ac-4426-ac49-318c8313944b' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '7c44d07a-97ac-4426-ac49-318c8313944b' AND NOT ('gourmand' = ANY(tags));

-- Bâtonnets croustillants de feta à la pâte filo et sauce au miel
UPDATE recipes SET nutrition = '{"calories": 91, "protein_g": 4.3, "fat_g": 4.1, "carbs_g": 8.8, "fiber_g": 0.6}' WHERE id = '7196e89c-faf6-457e-9a3a-c3746640d3d6';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '7196e89c-faf6-457e-9a3a-c3746640d3d6' AND NOT ('léger' = ANY(tags));

-- Bûche salée au saumon et aux épinards
UPDATE recipes SET nutrition = '{"calories": 312, "protein_g": 16.1, "fat_g": 8.8, "carbs_g": 41.3, "fiber_g": 2.4}' WHERE id = 'fdbb6349-7d99-4ad0-9e0e-988e3f60243e';

-- Bœuf Bourguignon au Cookeo
UPDATE recipes SET nutrition = '{"calories": 901, "protein_g": 80.2, "fat_g": 29.7, "carbs_g": 73.9, "fiber_g": 8.6}' WHERE id = '8158a0ff-597f-413f-a1fa-19fd43b1ecfa';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '8158a0ff-597f-413f-a1fa-19fd43b1ecfa' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '8158a0ff-597f-413f-a1fa-19fd43b1ecfa' AND NOT ('gourmand' = ANY(tags));

-- Cake pépites de chocolat
UPDATE recipes SET nutrition = '{"calories": 243, "protein_g": 11.1, "fat_g": 7.1, "carbs_g": 33.0, "fiber_g": 1.5}' WHERE id = 'e5d9b047-02d7-433a-b423-04d278439b5d';

-- Cake salé au jambon et aux olives
UPDATE recipes SET nutrition = '{"calories": 215, "protein_g": 12.0, "fat_g": 8.7, "carbs_g": 21.5, "fiber_g": 1.4}' WHERE id = '8ebc6dbd-1eaa-4827-8e11-947357df83b9';

-- Cake salé rapide et facile
UPDATE recipes SET nutrition = '{"calories": 381, "protein_g": 25.3, "fat_g": 13.2, "carbs_g": 38.9, "fiber_g": 3.4}' WHERE id = 'b089b455-820c-4580-b37c-9b0a3b71628e';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'b089b455-820c-4580-b37c-9b0a3b71628e' AND NOT ('protéiné' = ANY(tags));

-- Cake à la banane / banana bread (USA)
UPDATE recipes SET nutrition = '{"calories": 285, "protein_g": 8.4, "fat_g": 5.8, "carbs_g": 48.8, "fiber_g": 3.0}' WHERE id = '009331eb-8013-447b-84a3-48748a772d06';

-- Camembert Coeur de lion rôti au four
UPDATE recipes SET nutrition = '{"calories": 37, "protein_g": 1.9, "fat_g": 1.5, "carbs_g": 3.6, "fiber_g": 0.8}' WHERE id = '780fa792-0f5f-4228-a0a0-79bc4a1809cc';

-- Camembert rôti au barbecue
UPDATE recipes SET nutrition = '{"calories": 13, "protein_g": 0.8, "fat_g": 0.9, "carbs_g": 0.4, "fiber_g": 0.0}' WHERE id = 'cdde2f1a-f6d4-4478-b767-426aaf8525c6';

-- Cannelloni au boeuf
UPDATE recipes SET nutrition = '{"calories": 413, "protein_g": 46.9, "fat_g": 19.3, "carbs_g": 11.0, "fiber_g": 3.0}' WHERE id = '41ad246c-8c9b-4afa-ac3c-cb4e23c519fa';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '41ad246c-8c9b-4afa-ac3c-cb4e23c519fa' AND NOT ('protéiné' = ANY(tags));

-- Cannellonis ricotta et épinards à la sauce tomate
UPDATE recipes SET nutrition = '{"calories": 333, "protein_g": 18.4, "fat_g": 14.6, "carbs_g": 30.1, "fiber_g": 9.0}' WHERE id = 'fbe2dac6-9175-4eaf-89e2-bebe28506817';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'fbe2dac6-9175-4eaf-89e2-bebe28506817' AND NOT ('léger' = ANY(tags));

-- Carbonades flamandes traditionnelles
UPDATE recipes SET nutrition = '{"calories": 1363, "protein_g": 94.9, "fat_g": 37.1, "carbs_g": 156.5, "fiber_g": 9.7}' WHERE id = '51232d37-4fcb-4527-a08c-34cd35238289';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '51232d37-4fcb-4527-a08c-34cd35238289' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '51232d37-4fcb-4527-a08c-34cd35238289' AND NOT ('gourmand' = ANY(tags));

-- Carbonara traditionnelle
UPDATE recipes SET nutrition = '{"calories": 397, "protein_g": 39.4, "fat_g": 22.0, "carbs_g": 8.8, "fiber_g": 0.5}' WHERE id = '286cf99d-4296-4ca0-8d1b-61d6bd3a3d65';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '286cf99d-4296-4ca0-8d1b-61d6bd3a3d65' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '286cf99d-4296-4ca0-8d1b-61d6bd3a3d65' AND NOT ('gourmand' = ANY(tags));

-- Carottes vichy
UPDATE recipes SET nutrition = '{"calories": 238, "protein_g": 9.8, "fat_g": 3.3, "carbs_g": 40.2, "fiber_g": 9.9}' WHERE id = '0f65c04f-7faf-486c-ac92-a3ddfea27895';

-- Cassoulet traditionnel
UPDATE recipes SET nutrition = '{"calories": 440, "protein_g": 53.8, "fat_g": 21.0, "carbs_g": 6.8, "fiber_g": 1.4}' WHERE id = '29abcd2a-90c2-4af2-a9ae-8489d723e00b';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '29abcd2a-90c2-4af2-a9ae-8489d723e00b' AND NOT ('protéiné' = ANY(tags));

-- Chaussons de blettes par Laurent Mariotte
UPDATE recipes SET nutrition = '{"calories": 538, "protein_g": 16.7, "fat_g": 5.4, "carbs_g": 102.5, "fiber_g": 14.5}' WHERE id = '6b7fcdee-faea-4b6c-8ee3-142ad41ae6f5';

-- Cheese Naan
UPDATE recipes SET nutrition = '{"calories": 223, "protein_g": 5.7, "fat_g": 3.0, "carbs_g": 42.5, "fiber_g": 2.1}' WHERE id = '1d008203-38d5-49a8-a8db-53f00e2d413d';

-- Cheese-cake classique au fromage Philadelphia et aux spéculoos
UPDATE recipes SET nutrition = '{"calories": 215, "protein_g": 10.2, "fat_g": 10.8, "carbs_g": 18.4, "fiber_g": 1.1}' WHERE id = 'e7340746-11a3-4b6d-a7dc-ede9962df238';

-- Chili con carne Vénézuelien
UPDATE recipes SET nutrition = '{"calories": 978, "protein_g": 85.5, "fat_g": 26.8, "carbs_g": 91.0, "fiber_g": 24.5}' WHERE id = 'bafe6a61-cac2-4b1a-92db-a9c5680a3186';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'bafe6a61-cac2-4b1a-92db-a9c5680a3186' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'bafe6a61-cac2-4b1a-92db-a9c5680a3186' AND NOT ('gourmand' = ANY(tags));

-- Chili con carne facile
UPDATE recipes SET nutrition = '{"calories": 405, "protein_g": 50.4, "fat_g": 19.4, "carbs_g": 5.3, "fiber_g": 1.9}' WHERE id = '492c2d79-dd53-4812-a18e-c212c5c06ac0';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '492c2d79-dd53-4812-a18e-c212c5c06ac0' AND NOT ('protéiné' = ANY(tags));

-- Chou chinois au champignon et riz
UPDATE recipes SET nutrition = '{"calories": 255, "protein_g": 22.0, "fat_g": 8.0, "carbs_g": 22.5, "fiber_g": 3.8}' WHERE id = 'd8feb989-7439-4e65-80f5-f603a6762cf5';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'd8feb989-7439-4e65-80f5-f603a6762cf5' AND NOT ('protéiné' = ANY(tags));

-- Chou rouge aux pommes (de ma grand-mère)
UPDATE recipes SET nutrition = '{"calories": 132, "protein_g": 3.1, "fat_g": 1.5, "carbs_g": 25.9, "fiber_g": 2.9}' WHERE id = 'cee59dd9-db60-4f26-8e4c-b225833e1f86';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'cee59dd9-db60-4f26-8e4c-b225833e1f86' AND NOT ('léger' = ANY(tags));

-- Chou-fleur au Air Fryer
UPDATE recipes SET nutrition = '{"calories": 17, "protein_g": 0.8, "fat_g": 0.2, "carbs_g": 3.0, "fiber_g": 1.1}' WHERE id = '8eaccac2-5e84-4ea7-bd36-d4f3426c3020';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '8eaccac2-5e84-4ea7-bd36-d4f3426c3020' AND NOT ('léger' = ANY(tags));

-- Chou-fleur au Cookeo
UPDATE recipes SET nutrition = '{"calories": 199, "protein_g": 4.9, "fat_g": 2.0, "carbs_g": 39.4, "fiber_g": 2.6}' WHERE id = '7c0a0311-c1d2-4479-8a4e-5b93d0e797cd';

-- Choux (vert) braisé
UPDATE recipes SET nutrition = '{"calories": 120, "protein_g": 5.9, "fat_g": 2.1, "carbs_g": 18.8, "fiber_g": 2.2}' WHERE id = 'b700ae90-2246-4f89-a8e2-e2016d0e55e2';

-- Choux de Bruxelles au lard en cocotte
UPDATE recipes SET nutrition = '{"calories": 124, "protein_g": 5.9, "fat_g": 4.1, "carbs_g": 14.8, "fiber_g": 4.3}' WHERE id = '9a115cc0-8cd7-4858-a5b9-74ccfa6c9461';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '9a115cc0-8cd7-4858-a5b9-74ccfa6c9461' AND NOT ('léger' = ANY(tags));

-- Choux-Choux soja sésame !
UPDATE recipes SET nutrition = '{"calories": 108, "protein_g": 4.2, "fat_g": 0.9, "carbs_g": 19.9, "fiber_g": 3.0}' WHERE id = '533d5bf1-847c-4c50-a6f4-0ecf755a7bcc';

-- Civet de Sanglier à la bourguignonne
UPDATE recipes SET nutrition = '{"calories": 677, "protein_g": 21.6, "fat_g": 9.0, "carbs_g": 124.5, "fiber_g": 7.6}' WHERE id = 'c65e9148-7c07-49b7-9fdc-d26a95a973d4';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'c65e9148-7c07-49b7-9fdc-d26a95a973d4' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'c65e9148-7c07-49b7-9fdc-d26a95a973d4' AND NOT ('gourmand' = ANY(tags));

-- Compote de fraises
UPDATE recipes SET nutrition = '{"calories": 92, "protein_g": 1.7, "fat_g": 0.7, "carbs_g": 19.5, "fiber_g": 2.4}' WHERE id = 'b7b585a5-f7e2-4d0f-8c6f-544abac25978';

-- Compote de pommes classique
UPDATE recipes SET nutrition = '{"calories": 532, "protein_g": 13.3, "fat_g": 4.8, "carbs_g": 106.5, "fiber_g": 10.6}' WHERE id = '0ac10912-b19d-4a26-bcbc-383f57a961f0';

-- Compote de rhubarbe au Companion
UPDATE recipes SET nutrition = '{"calories": 222, "protein_g": 6.0, "fat_g": 6.0, "carbs_g": 34.5, "fiber_g": 2.2}' WHERE id = 'b63dab91-5342-4607-bb7a-42740a62a54b';

-- Compotée d''oignons rouges caramélisés
UPDATE recipes SET nutrition = '{"calories": 436, "protein_g": 11.5, "fat_g": 4.9, "carbs_g": 84.3, "fiber_g": 7.3}' WHERE id = '68082712-95f8-423f-9c3c-5321e0c2fac4';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '68082712-95f8-423f-9c3c-5321e0c2fac4' AND NOT ('léger' = ANY(tags));

-- Conchiglioni farcis à la ricotta, jambon et tomates séchées
UPDATE recipes SET nutrition = '{"calories": 4881, "protein_g": 136.8, "fat_g": 64.9, "carbs_g": 917.1, "fiber_g": 48.7}' WHERE id = '47c1eadb-3b2a-4e65-9d79-9d963439d6be';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '47c1eadb-3b2a-4e65-9d79-9d963439d6be' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '47c1eadb-3b2a-4e65-9d79-9d963439d6be' AND NOT ('gourmand' = ANY(tags));

-- Cookies au chocolat noir
UPDATE recipes SET nutrition = '{"calories": 62, "protein_g": 1.6, "fat_g": 0.9, "carbs_g": 11.4, "fiber_g": 0.6}' WHERE id = '47424098-400c-4134-92b9-c81d689fb13d';

-- Cookies maison
UPDATE recipes SET nutrition = '{"calories": 302, "protein_g": 8.9, "fat_g": 5.8, "carbs_g": 52.5, "fiber_g": 2.6}' WHERE id = '21b782cb-5ab4-4640-bfa0-56bc6edfa18e';

-- Courge spaghetti en gratin
UPDATE recipes SET nutrition = '{"calories": 287, "protein_g": 29.8, "fat_g": 12.4, "carbs_g": 12.5, "fiber_g": 4.5}' WHERE id = '1dcaee1a-d104-4fd0-802a-7b8c9fffb673';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '1dcaee1a-d104-4fd0-802a-7b8c9fffb673' AND NOT ('protéiné' = ANY(tags));

-- Courgettes au Air Fryer
UPDATE recipes SET nutrition = '{"calories": 49, "protein_g": 2.4, "fat_g": 0.5, "carbs_g": 8.1, "fiber_g": 3.2}' WHERE id = '2bb89581-4c2a-488c-844c-2ba73ce166e8';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '2bb89581-4c2a-488c-844c-2ba73ce166e8' AND NOT ('léger' = ANY(tags));

-- Courgettes rondes farcies au saumon fumé
UPDATE recipes SET nutrition = '{"calories": 87, "protein_g": 7.9, "fat_g": 5.2, "carbs_g": 2.0, "fiber_g": 0.0}' WHERE id = '095518e3-5f48-4005-b8aa-0efad44184bd';

-- Couscous Royal
UPDATE recipes SET nutrition = '{"calories": 1206, "protein_g": 112.6, "fat_g": 41.1, "carbs_g": 90.1, "fiber_g": 14.4}' WHERE id = '1d355978-04af-491f-902b-e6d8b86a9089';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '1d355978-04af-491f-902b-e6d8b86a9089' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '1d355978-04af-491f-902b-e6d8b86a9089' AND NOT ('gourmand' = ANY(tags));

-- Couscous poulet et merguez facile
UPDATE recipes SET nutrition = '{"calories": 1605, "protein_g": 191.9, "fat_g": 68.3, "carbs_g": 46.3, "fiber_g": 17.9}' WHERE id = 'd65928dd-b813-4a05-b3cf-7242070b5319';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'd65928dd-b813-4a05-b3cf-7242070b5319' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'd65928dd-b813-4a05-b3cf-7242070b5319' AND NOT ('gourmand' = ANY(tags));

-- Crevettes à l’ail et lait de coco façon curry
UPDATE recipes SET nutrition = '{"calories": 278, "protein_g": 33.2, "fat_g": 12.0, "carbs_g": 9.0, "fiber_g": 1.5}' WHERE id = '19d43ad5-a5e2-4cab-a666-1205305c98a6';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '19d43ad5-a5e2-4cab-a666-1205305c98a6' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '19d43ad5-a5e2-4cab-a666-1205305c98a6' AND NOT ('léger' = ANY(tags));

-- Croque croissant au jambon et au comté
UPDATE recipes SET nutrition = '{"calories": 341, "protein_g": 23.4, "fat_g": 18.6, "carbs_g": 18.4, "fiber_g": 3.9}' WHERE id = '78e768b0-2b82-41a8-879d-bf068a7dea45';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '78e768b0-2b82-41a8-879d-bf068a7dea45' AND NOT ('protéiné' = ANY(tags));

-- Croque-monsieur
UPDATE recipes SET nutrition = '{"calories": 332, "protein_g": 16.5, "fat_g": 10.4, "carbs_g": 41.7, "fiber_g": 2.1}' WHERE id = 'f264d254-237f-4aad-9f21-6d389306dc84';

-- Croquettes de courgettes aux herbes et aux épices
UPDATE recipes SET nutrition = '{"calories": 1144, "protein_g": 28.8, "fat_g": 13.2, "carbs_g": 222.7, "fiber_g": 13.1}' WHERE id = '2b9d5d1d-8736-48c8-a773-479da4876328';

-- Croziflette
UPDATE recipes SET nutrition = '{"calories": 223, "protein_g": 18.9, "fat_g": 12.0, "carbs_g": 9.0, "fiber_g": 1.1}' WHERE id = '16df2365-50c8-4c81-9dd0-89bc20ae9ed3';

-- Crumble aux myrtilles
UPDATE recipes SET nutrition = '{"calories": 310, "protein_g": 8.1, "fat_g": 4.9, "carbs_g": 57.1, "fiber_g": 4.2}' WHERE id = 'f95cc798-ae01-4433-a3b6-2e1ae45f3451';

-- Crumble aux pommes
UPDATE recipes SET nutrition = '{"calories": 233, "protein_g": 12.9, "fat_g": 4.0, "carbs_g": 35.5, "fiber_g": 4.1}' WHERE id = '3edd0fa6-6bb2-45de-8d6f-05c51c58a96e';

-- Crumble aux pommes de grand-mère
UPDATE recipes SET nutrition = '{"calories": 186, "protein_g": 4.6, "fat_g": 2.8, "carbs_g": 34.8, "fiber_g": 3.1}' WHERE id = 'e496be35-53f5-4161-9357-6d0c89b02f1c';

-- Crumble rapide aux framboises et speculoos
UPDATE recipes SET nutrition = '{"calories": 108, "protein_g": 3.2, "fat_g": 2.5, "carbs_g": 17.5, "fiber_g": 0.9}' WHERE id = 'd2cc2c06-0fe8-4b5d-b70e-9ccaf6461268';

-- Crumble à la banane
UPDATE recipes SET nutrition = '{"calories": 146, "protein_g": 3.7, "fat_g": 2.3, "carbs_g": 27.1, "fiber_g": 2.2}' WHERE id = 'eac5f620-1af7-4c6f-8bf2-ec85972c16fd';

-- Crème pâtissière
UPDATE recipes SET nutrition = '{"calories": 419, "protein_g": 20.0, "fat_g": 20.1, "carbs_g": 38.3, "fiber_g": 1.5}' WHERE id = '99c6daab-ce6b-458f-ba04-222e31ede681';
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '99c6daab-ce6b-458f-ba04-222e31ede681' AND NOT ('gourmand' = ANY(tags));

-- Crêpes au cidre
UPDATE recipes SET nutrition = '{"calories": 451, "protein_g": 17.5, "fat_g": 16.3, "carbs_g": 57.0, "fiber_g": 3.6}' WHERE id = '56628e71-a1c2-4510-b2c2-e22b08ed7781';

-- Crêpes pour famille nombreuse
UPDATE recipes SET nutrition = '{"calories": 873, "protein_g": 36.5, "fat_g": 33.8, "carbs_g": 103.0, "fiber_g": 4.5}' WHERE id = '6aa1f340-d3c9-4831-9a1a-189259bdafa9';
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '6aa1f340-d3c9-4831-9a1a-189259bdafa9' AND NOT ('gourmand' = ANY(tags));

-- Cuisse de dinde au four
UPDATE recipes SET nutrition = '{"calories": 743, "protein_g": 91.5, "fat_g": 34.2, "carbs_g": 14.2, "fiber_g": 2.9}' WHERE id = 'f58854d2-d468-4f08-886c-ff8d7655f231';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'f58854d2-d468-4f08-886c-ff8d7655f231' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'f58854d2-d468-4f08-886c-ff8d7655f231' AND NOT ('gourmand' = ANY(tags));

-- Cuisse de dinde façon couscous de chez Karpeth
UPDATE recipes SET nutrition = '{"calories": 688, "protein_g": 44.6, "fat_g": 11.4, "carbs_g": 95.9, "fiber_g": 26.1}' WHERE id = 'c68ce3c7-e156-430c-b13a-5031e6954046';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'c68ce3c7-e156-430c-b13a-5031e6954046' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'c68ce3c7-e156-430c-b13a-5031e6954046' AND NOT ('gourmand' = ANY(tags));

-- Cuisses de poulet au four
UPDATE recipes SET nutrition = '{"calories": 761, "protein_g": 58.0, "fat_g": 22.1, "carbs_g": 79.2, "fiber_g": 5.4}' WHERE id = 'f11805be-8065-434d-a60e-9e7809c7a519';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'f11805be-8065-434d-a60e-9e7809c7a519' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'f11805be-8065-434d-a60e-9e7809c7a519' AND NOT ('gourmand' = ANY(tags));

-- Cuisses de poulet et pomme de terre au four
UPDATE recipes SET nutrition = '{"calories": 844, "protein_g": 59.6, "fat_g": 22.4, "carbs_g": 96.8, "fiber_g": 13.4}' WHERE id = '91037ec4-e3c7-4ddb-8ade-db0b4f1c61ab';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '91037ec4-e3c7-4ddb-8ade-db0b4f1c61ab' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '91037ec4-e3c7-4ddb-8ade-db0b4f1c61ab' AND NOT ('gourmand' = ANY(tags));

-- Côtelettes de porc au Air Fryer
UPDATE recipes SET nutrition = '{"calories": 361, "protein_g": 48.1, "fat_g": 18.0, "carbs_g": 0.2, "fiber_g": 0.1}' WHERE id = 'a3024fe8-ccdc-406a-980c-bc3f220ec78c';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'a3024fe8-ccdc-406a-980c-bc3f220ec78c' AND NOT ('protéiné' = ANY(tags));

-- Dahl de lentilles corail
UPDATE recipes SET nutrition = '{"calories": 402, "protein_g": 12.9, "fat_g": 7.9, "carbs_g": 68.1, "fiber_g": 5.5}' WHERE id = '22c1d5de-04a4-4aa1-a2f3-09c0e8cd8bed';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '22c1d5de-04a4-4aa1-a2f3-09c0e8cd8bed' AND NOT ('léger' = ANY(tags));

-- Dakgangjeong, le poulet frit coréen
UPDATE recipes SET nutrition = '{"calories": 366, "protein_g": 28.8, "fat_g": 11.1, "carbs_g": 36.2, "fiber_g": 2.6}' WHERE id = '6699f398-785d-44a1-bf9c-003e8140b913';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '6699f398-785d-44a1-bf9c-003e8140b913' AND NOT ('protéiné' = ANY(tags));

-- Ebly au curry et au coco
UPDATE recipes SET nutrition = '{"calories": 400, "protein_g": 42.1, "fat_g": 16.9, "carbs_g": 17.5, "fiber_g": 5.6}' WHERE id = '55513504-7275-482a-9ff2-f28be4f03c0a';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '55513504-7275-482a-9ff2-f28be4f03c0a' AND NOT ('protéiné' = ANY(tags));

-- Encornets sautés à l''ail et au persil
UPDATE recipes SET nutrition = '{"calories": 64, "protein_g": 3.0, "fat_g": 0.9, "carbs_g": 10.3, "fiber_g": 3.9}' WHERE id = '3e889f9a-41a9-440d-a75a-59107cd59b6c';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '3e889f9a-41a9-440d-a75a-59107cd59b6c' AND NOT ('léger' = ANY(tags));

-- Endives au jambon
UPDATE recipes SET nutrition = '{"calories": 335, "protein_g": 26.3, "fat_g": 13.8, "carbs_g": 24.4, "fiber_g": 6.9}' WHERE id = 'f06043cc-7201-45cd-817c-daf4ede38a8e';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'f06043cc-7201-45cd-817c-daf4ede38a8e' AND NOT ('protéiné' = ANY(tags));

-- Epinards crémeux
UPDATE recipes SET nutrition = '{"calories": 93, "protein_g": 4.8, "fat_g": 2.0, "carbs_g": 13.1, "fiber_g": 5.0}' WHERE id = 'd8736bb8-3d5f-4481-bf57-24e4ad84929b';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'd8736bb8-3d5f-4481-bf57-24e4ad84929b' AND NOT ('léger' = ANY(tags));

-- Falafel (croquettes de pois chiches)
UPDATE recipes SET nutrition = '{"calories": 349, "protein_g": 19.0, "fat_g": 2.1, "carbs_g": 58.9, "fiber_g": 14.2}' WHERE id = '6a16021b-ec46-42e7-af59-2607dca85a5d';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '6a16021b-ec46-42e7-af59-2607dca85a5d' AND NOT ('léger' = ANY(tags));

-- Far breton aux pruneaux
UPDATE recipes SET nutrition = '{"calories": 878, "protein_g": 26.6, "fat_g": 20.4, "carbs_g": 143.6, "fiber_g": 12.9}' WHERE id = 'f181d71b-1586-45b4-bd61-45d375eba116';
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'f181d71b-1586-45b4-bd61-45d375eba116' AND NOT ('gourmand' = ANY(tags));

-- Filet mignon au Air Fryer
UPDATE recipes SET nutrition = '{"calories": 74, "protein_g": 9.2, "fat_g": 3.5, "carbs_g": 0.9, "fiber_g": 0.3}' WHERE id = '79a1c6b6-8a24-49cd-986f-c6bb06a99114';

-- Filet mignon de porc au four
UPDATE recipes SET nutrition = '{"calories": 160, "protein_g": 19.4, "fat_g": 7.8, "carbs_g": 2.4, "fiber_g": 0.8}' WHERE id = '504127aa-71d9-4cf5-831e-eb394d3df619';

-- Filet mignon de porc à la moutarde
UPDATE recipes SET nutrition = '{"calories": 718, "protein_g": 54.9, "fat_g": 27.8, "carbs_g": 59.2, "fiber_g": 3.4}' WHERE id = '91a4684f-c936-4bc2-8221-cbb1cd50ea35';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '91a4684f-c936-4bc2-8221-cbb1cd50ea35' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '91a4684f-c936-4bc2-8221-cbb1cd50ea35' AND NOT ('gourmand' = ANY(tags));

-- Filets de sardine grillés au four
UPDATE recipes SET nutrition = '{"calories": 148, "protein_g": 18.4, "fat_g": 4.0, "carbs_g": 9.0, "fiber_g": 3.1}' WHERE id = '7b2bc50b-82e3-4a8a-8cde-612df131f45b';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '7b2bc50b-82e3-4a8a-8cde-612df131f45b' AND NOT ('léger' = ANY(tags));

-- Financiers aux framboises et citron vert
UPDATE recipes SET nutrition = '{"calories": 294, "protein_g": 17.0, "fat_g": 9.8, "carbs_g": 33.5, "fiber_g": 3.3}' WHERE id = 'e7890f7f-5c65-4743-bba4-504d562f269d';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'e7890f7f-5c65-4743-bba4-504d562f269d' AND NOT ('léger' = ANY(tags));

-- Flamiche briochée au Maroilles
UPDATE recipes SET nutrition = '{"calories": 392, "protein_g": 12.3, "fat_g": 8.8, "carbs_g": 64.5, "fiber_g": 3.1}' WHERE id = '96a185cb-1096-4782-a9d1-7c0c117c8b0b';

-- Flan aux œufs maison
UPDATE recipes SET nutrition = '{"calories": 284, "protein_g": 19.2, "fat_g": 16.6, "carbs_g": 13.9, "fiber_g": 0.4}' WHERE id = 'b060f74d-a388-4731-9729-bc833de88248';

-- Flan de butternut au fromage
UPDATE recipes SET nutrition = '{"calories": 398, "protein_g": 22.4, "fat_g": 24.3, "carbs_g": 21.6, "fiber_g": 0.6}' WHERE id = 'e1066926-6f36-4e97-bbaa-146e7541c57f';
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'e1066926-6f36-4e97-bbaa-146e7541c57f' AND NOT ('gourmand' = ANY(tags));

-- Flan de courgettes
UPDATE recipes SET nutrition = '{"calories": 254, "protein_g": 15.0, "fat_g": 14.6, "carbs_g": 14.6, "fiber_g": 3.3}' WHERE id = 'e8f63145-9784-46ff-964c-e13712a0c1de';

-- Flan pâtissier traditionnel
UPDATE recipes SET nutrition = '{"calories": 329, "protein_g": 15.4, "fat_g": 15.2, "carbs_g": 31.7, "fiber_g": 1.3}' WHERE id = '14422408-e8cb-42dc-a5ec-20eaf8dc96fd';

-- Foccacia au saumon fumé
UPDATE recipes SET nutrition = '{"calories": 494, "protein_g": 16.5, "fat_g": 7.0, "carbs_g": 89.3, "fiber_g": 4.7}' WHERE id = 'e82bd4a6-0595-4c2e-8432-ce2f6aa8bc22';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'e82bd4a6-0595-4c2e-8432-ce2f6aa8bc22' AND NOT ('léger' = ANY(tags));

-- Fondue Savoyarde
UPDATE recipes SET nutrition = '{"calories": 512, "protein_g": 17.5, "fat_g": 14.1, "carbs_g": 76.9, "fiber_g": 3.7}' WHERE id = 'e9a60690-f10b-4bc5-84ed-b659774386b3';

-- Fondue aux poireaux
UPDATE recipes SET nutrition = '{"calories": 108, "protein_g": 2.5, "fat_g": 1.9, "carbs_g": 19.8, "fiber_g": 3.2}' WHERE id = 'a85586bc-f347-4e06-82f1-87e74991cfeb';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'a85586bc-f347-4e06-82f1-87e74991cfeb' AND NOT ('léger' = ANY(tags));

-- Fondue de poireaux
UPDATE recipes SET nutrition = '{"calories": 172, "protein_g": 4.1, "fat_g": 3.1, "carbs_g": 31.1, "fiber_g": 5.0}' WHERE id = '336ca473-350e-465e-b53b-9b9c57c6b208';

-- Frites de patate douce sans friture !
UPDATE recipes SET nutrition = '{"calories": 135, "protein_g": 5.6, "fat_g": 1.4, "carbs_g": 24.0, "fiber_g": 6.5}' WHERE id = '91ffd0c9-21c4-4bfe-839f-15deb426b46c';

-- Galette de pomme de terre & carotte
UPDATE recipes SET nutrition = '{"calories": 85, "protein_g": 3.2, "fat_g": 2.6, "carbs_g": 11.9, "fiber_g": 2.3}' WHERE id = 'e57f2c52-1698-4532-8c25-c12ce668dad9';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'e57f2c52-1698-4532-8c25-c12ce668dad9' AND NOT ('léger' = ANY(tags));

-- Galette des rois à la frangipane
UPDATE recipes SET nutrition = '{"calories": 275, "protein_g": 8.5, "fat_g": 6.0, "carbs_g": 45.7, "fiber_g": 2.2}' WHERE id = '27995f0d-e86e-4111-81b0-7fb44bd6770b';

-- Galettes de chou-fleur (rösti)
UPDATE recipes SET nutrition = '{"calories": 141, "protein_g": 8.2, "fat_g": 5.7, "carbs_g": 13.6, "fiber_g": 1.6}' WHERE id = '6d7e06c9-c14c-483f-b894-413f0de405fa';

-- Galettes de pommes de terre au four
UPDATE recipes SET nutrition = '{"calories": 37, "protein_g": 0.9, "fat_g": 0.6, "carbs_g": 6.8, "fiber_g": 1.1}' WHERE id = '7c99bf00-75c8-4927-9b86-8f5b310f47be';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '7c99bf00-75c8-4927-9b86-8f5b310f47be' AND NOT ('léger' = ANY(tags));

-- Gaspacho au chou-fleur
UPDATE recipes SET nutrition = '{"calories": 691, "protein_g": 21.5, "fat_g": 11.7, "carbs_g": 121.6, "fiber_g": 10.9}' WHERE id = '750c67e4-97b0-4c8f-9d89-8fd144b9221f';

-- Gaufres de patate douce
UPDATE recipes SET nutrition = '{"calories": 200, "protein_g": 8.1, "fat_g": 6.0, "carbs_g": 27.4, "fiber_g": 3.0}' WHERE id = 'b3d058cc-0694-49e0-9931-7b574943d800';

-- Gaufres faciles et légères
UPDATE recipes SET nutrition = '{"calories": 85, "protein_g": 3.5, "fat_g": 3.2, "carbs_g": 10.4, "fiber_g": 0.5}' WHERE id = '83bcc592-f3c3-480f-ad54-d0b05ca60e7c';

-- Gaufres salées fourrées aux fromages
UPDATE recipes SET nutrition = '{"calories": 437, "protein_g": 18.0, "fat_g": 16.5, "carbs_g": 52.8, "fiber_g": 2.3}' WHERE id = '70bd07cb-a99e-432f-ae1a-747762da8269';

-- Gigot d''agneau : la recette traditionnelle
UPDATE recipes SET nutrition = '{"calories": 9, "protein_g": 0.5, "fat_g": 0.1, "carbs_g": 1.4, "fiber_g": 0.5}' WHERE id = 'f0033875-452f-4ac7-a497-33fc4e9416ff';

-- Gingembre confit
UPDATE recipes SET nutrition = '{"calories": 55, "protein_g": 1.4, "fat_g": 0.5, "carbs_g": 10.8, "fiber_g": 0.8}' WHERE id = '05383556-53bf-4374-8db2-96c0fe77feae';

-- Glaçage meringué pour les cupcakes
UPDATE recipes SET nutrition = '{"calories": 176, "protein_g": 5.1, "fat_g": 3.3, "carbs_g": 30.8, "fiber_g": 1.5}' WHERE id = 'db4bd3de-36c8-4840-a388-1d0c4e38f0a6';

-- Gnocchis au chorizo
UPDATE recipes SET nutrition = '{"calories": 548, "protein_g": 19.1, "fat_g": 7.3, "carbs_g": 98.8, "fiber_g": 8.0}' WHERE id = '09751a0b-c504-40e6-9ca2-ca291bfa6dfc';

-- Gratin dauphinois de patate douce
UPDATE recipes SET nutrition = '{"calories": 379, "protein_g": 22.4, "fat_g": 21.8, "carbs_g": 21.9, "fiber_g": 5.0}' WHERE id = '4dac4627-f3b0-4edc-b65d-e91ddf0d696f';
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '4dac4627-f3b0-4edc-b65d-e91ddf0d696f' AND NOT ('gourmand' = ANY(tags));

-- Gratin de brocolis facile
UPDATE recipes SET nutrition = '{"calories": 442, "protein_g": 21.6, "fat_g": 15.4, "carbs_g": 52.6, "fiber_g": 5.1}' WHERE id = 'd952fe1b-9dc2-42fb-ae64-c4f9e086efcb';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'd952fe1b-9dc2-42fb-ae64-c4f9e086efcb' AND NOT ('protéiné' = ANY(tags));

-- Gratin de chou-fleur
UPDATE recipes SET nutrition = '{"calories": 788, "protein_g": 58.0, "fat_g": 36.9, "carbs_g": 52.9, "fiber_g": 6.5}' WHERE id = '1872a734-34e4-4acb-9a85-2b07ea0ca81a';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '1872a734-34e4-4acb-9a85-2b07ea0ca81a' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '1872a734-34e4-4acb-9a85-2b07ea0ca81a' AND NOT ('gourmand' = ANY(tags));

-- Gratin de chou-fleur léger
UPDATE recipes SET nutrition = '{"calories": 386, "protein_g": 11.2, "fat_g": 6.3, "carbs_g": 69.5, "fiber_g": 4.7}' WHERE id = 'eed5cccc-ff27-4a6d-ba78-5d08c7b93cb6';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'eed5cccc-ff27-4a6d-ba78-5d08c7b93cb6' AND NOT ('léger' = ANY(tags));

-- Gratin de courge butternut
UPDATE recipes SET nutrition = '{"calories": 88, "protein_g": 4.5, "fat_g": 5.2, "carbs_g": 5.3, "fiber_g": 0.3}' WHERE id = '1274ab8c-14f9-4832-9fe4-906a0db8a1f5';

-- Gratin de courgettes rapide
UPDATE recipes SET nutrition = '{"calories": 176, "protein_g": 9.9, "fat_g": 7.5, "carbs_g": 16.1, "fiber_g": 5.3}' WHERE id = '37ff5150-ab7d-4c81-b619-0fea5c0581fc';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '37ff5150-ab7d-4c81-b619-0fea5c0581fc' AND NOT ('léger' = ANY(tags));

-- Gratin de crozets savoyard
UPDATE recipes SET nutrition = '{"calories": 252, "protein_g": 11.9, "fat_g": 6.3, "carbs_g": 35.8, "fiber_g": 2.3}' WHERE id = 'f6b5bcd9-c683-45b2-b119-9be8664556c9';

-- Gratin de poireaux
UPDATE recipes SET nutrition = '{"calories": 282, "protein_g": 10.5, "fat_g": 10.1, "carbs_g": 36.4, "fiber_g": 5.1}' WHERE id = '66bf379b-a8ea-4200-92ef-75fc05aef17d';

-- Gratin de poissons aux légumes
UPDATE recipes SET nutrition = '{"calories": 379, "protein_g": 28.4, "fat_g": 12.1, "carbs_g": 37.4, "fiber_g": 7.1}' WHERE id = '52d6a01a-b678-48ca-8d65-a937539c19be';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '52d6a01a-b678-48ca-8d65-a937539c19be' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '52d6a01a-b678-48ca-8d65-a937539c19be' AND NOT ('léger' = ANY(tags));

-- Gratin de pommes de terre fondant
UPDATE recipes SET nutrition = '{"calories": 248, "protein_g": 8.8, "fat_g": 8.4, "carbs_g": 33.5, "fiber_g": 5.0}' WHERE id = '8b09606e-6cd0-4899-a87c-f5c9fd7e70e1';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '8b09606e-6cd0-4899-a87c-f5c9fd7e70e1' AND NOT ('léger' = ANY(tags));

-- Gratin de potimarron
UPDATE recipes SET nutrition = '{"calories": 84, "protein_g": 5.0, "fat_g": 5.7, "carbs_g": 3.2, "fiber_g": 0.1}' WHERE id = '5ab0156f-d488-4b10-823b-c05f4a1f82c0';

-- Gratin de ravioles du Dauphiné au comté
UPDATE recipes SET nutrition = '{"calories": 304, "protein_g": 16.8, "fat_g": 19.3, "carbs_g": 14.7, "fiber_g": 0.6}' WHERE id = '4c6388bd-7186-47f8-b35c-6b1fb6e0836f';

-- Gâteau au chocolat fondant rapide
UPDATE recipes SET nutrition = '{"calories": 234, "protein_g": 10.0, "fat_g": 5.1, "carbs_g": 36.2, "fiber_g": 1.8}' WHERE id = 'c8411dd1-2f75-4562-b5d6-f2453197eaf7';

-- Gâteau au yaourt
UPDATE recipes SET nutrition = '{"calories": 317, "protein_g": 14.0, "fat_g": 7.1, "carbs_g": 48.2, "fiber_g": 2.5}' WHERE id = 'd5c1aefc-cbba-457d-aa54-c3e33ad1361b';

-- Gâteau au yaourt fait maison
UPDATE recipes SET nutrition = '{"calories": 119, "protein_g": 7.0, "fat_g": 7.8, "carbs_g": 4.9, "fiber_g": 0.1}' WHERE id = '8b45212f-0f64-4c0c-8bc3-e8c92f8d729d';

-- Gâteau aux pommes facile
UPDATE recipes SET nutrition = '{"calories": 399, "protein_g": 14.1, "fat_g": 6.7, "carbs_g": 69.0, "fiber_g": 4.3}' WHERE id = '0a538994-0b4c-418a-89dc-cf839bed0418';

-- Gâteau d''anniversaire
UPDATE recipes SET nutrition = '{"calories": 447, "protein_g": 12.6, "fat_g": 7.9, "carbs_g": 79.8, "fiber_g": 3.9}' WHERE id = 'dcc93742-5954-49d1-acea-677dca57c621';

-- Gâteau à la banane et au chocolat
UPDATE recipes SET nutrition = '{"calories": 384, "protein_g": 11.9, "fat_g": 8.7, "carbs_g": 63.0, "fiber_g": 4.1}' WHERE id = 'd58ebde7-1050-4354-b9d1-1f3204957e1f';

-- Hachis Parmentier
UPDATE recipes SET nutrition = '{"calories": 330, "protein_g": 31.1, "fat_g": 14.9, "carbs_g": 16.1, "fiber_g": 3.5}' WHERE id = 'ffab0ca4-4be3-4361-b0cd-ac1e94ff3b1d';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'ffab0ca4-4be3-4361-b0cd-ac1e94ff3b1d' AND NOT ('protéiné' = ANY(tags));

-- La croziflette traditionnelle
UPDATE recipes SET nutrition = '{"calories": 243, "protein_g": 20.1, "fat_g": 13.3, "carbs_g": 9.6, "fiber_g": 1.1}' WHERE id = '09f7a2cd-4914-4b00-a9a5-cf8d85426237';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '09f7a2cd-4914-4b00-a9a5-cf8d85426237' AND NOT ('protéiné' = ANY(tags));

-- La faluche
UPDATE recipes SET nutrition = '{"calories": 226, "protein_g": 6.0, "fat_g": 3.4, "carbs_g": 41.9, "fiber_g": 2.1}' WHERE id = 'b7395586-806a-47af-b87f-57710b604b42';

-- La meilleure recette de pâte à crêpes
UPDATE recipes SET nutrition = '{"calories": 149, "protein_g": 6.2, "fat_g": 5.8, "carbs_g": 17.4, "fiber_g": 0.8}' WHERE id = 'afd6d5cd-e58c-4ad1-a759-c1b92651cce0';

-- La traditionnelle paëlla espagnole
UPDATE recipes SET nutrition = '{"calories": 1543, "protein_g": 141.0, "fat_g": 36.7, "carbs_g": 157.2, "fiber_g": 13.9}' WHERE id = '46b97f2c-e872-4832-82f5-67f8d382cf24';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '46b97f2c-e872-4832-82f5-67f8d382cf24' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '46b97f2c-e872-4832-82f5-67f8d382cf24' AND NOT ('gourmand' = ANY(tags));

-- Lasagnes à la bolognaise
UPDATE recipes SET nutrition = '{"calories": 671, "protein_g": 40.3, "fat_g": 24.8, "carbs_g": 68.9, "fiber_g": 6.5}' WHERE id = 'adccebac-4019-43bd-bfd7-e71f1c2d8ec5';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'adccebac-4019-43bd-bfd7-e71f1c2d8ec5' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'adccebac-4019-43bd-bfd7-e71f1c2d8ec5' AND NOT ('gourmand' = ANY(tags));

-- Le VRAI croque-monsieur
UPDATE recipes SET nutrition = '{"calories": 432, "protein_g": 25.3, "fat_g": 16.2, "carbs_g": 44.8, "fiber_g": 2.0}' WHERE id = 'b8655f85-fa3b-47e6-86ff-603df226961f';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'b8655f85-fa3b-47e6-86ff-603df226961f' AND NOT ('protéiné' = ANY(tags));

-- Le vrai houmous
UPDATE recipes SET nutrition = '{"calories": 297, "protein_g": 14.5, "fat_g": 2.5, "carbs_g": 50.4, "fiber_g": 10.2}' WHERE id = '93499c7d-6588-483c-b712-52d75b108c4f';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '93499c7d-6588-483c-b712-52d75b108c4f' AND NOT ('léger' = ANY(tags));

-- Lentilles Vertes du Puy
UPDATE recipes SET nutrition = '{"calories": 231, "protein_g": 9.7, "fat_g": 5.6, "carbs_g": 32.7, "fiber_g": 6.9}' WHERE id = '16af8358-886c-4728-a41b-69a0db18d3be';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '16af8358-886c-4728-a41b-69a0db18d3be' AND NOT ('léger' = ANY(tags));

-- Les meringues maison
UPDATE recipes SET nutrition = '{"calories": 177, "protein_g": 6.1, "fat_g": 4.8, "carbs_g": 26.6, "fiber_g": 1.2}' WHERE id = '71eefce8-c74c-4a10-922f-8f0f41ee16ec';

-- Les nems de ma grand mère (recette originale)
UPDATE recipes SET nutrition = '{"calories": 155, "protein_g": 18.6, "fat_g": 7.5, "carbs_g": 2.6, "fiber_g": 0.5}' WHERE id = 'd10675f4-ca93-4fd8-8ede-b2c548a982f0';

-- Légère panna cotta et son coulis
UPDATE recipes SET nutrition = '{"calories": 198, "protein_g": 13.4, "fat_g": 12.0, "carbs_g": 8.8, "fiber_g": 0.6}' WHERE id = 'c173c706-bde1-4f3e-8b54-96b5b220ff15';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'c173c706-bde1-4f3e-8b54-96b5b220ff15' AND NOT ('léger' = ANY(tags));

-- Macarons à la fraise classiques
UPDATE recipes SET nutrition = '{"calories": 421, "protein_g": 18.2, "fat_g": 8.9, "carbs_g": 65.5, "fiber_g": 3.6}' WHERE id = 'af6eb9c8-9d8f-40b3-92d5-6db692ffbafe';

-- Madeleines faciles
UPDATE recipes SET nutrition = '{"calories": 47, "protein_g": 1.6, "fat_g": 1.3, "carbs_g": 7.2, "fiber_g": 0.4}' WHERE id = '06f9dba4-10d8-4e54-9300-c1516e8583dc';

-- Millefeuilles de pommes de terre croustillantes au parmesan
UPDATE recipes SET nutrition = '{"calories": 145, "protein_g": 3.8, "fat_g": 2.9, "carbs_g": 25.1, "fiber_g": 4.2}' WHERE id = 'c7c802e0-7223-41cb-af2c-b7b732661977';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'c7c802e0-7223-41cb-af2c-b7b732661977' AND NOT ('léger' = ANY(tags));

-- Miso Shiru (soupe miso)
UPDATE recipes SET nutrition = '{"calories": 131, "protein_g": 3.8, "fat_g": 2.9, "carbs_g": 21.8, "fiber_g": 1.6}' WHERE id = '9f7eaf07-478c-4987-a263-2d0adc490fda';

-- Mochi au spéculoos
UPDATE recipes SET nutrition = '{"calories": 87, "protein_g": 2.0, "fat_g": 1.0, "carbs_g": 17.2, "fiber_g": 1.1}' WHERE id = '38dbacd9-bd56-4cb0-93fa-a58f08680f30';

-- Mont d''or au four classique
UPDATE recipes SET nutrition = '{"calories": 138, "protein_g": 3.7, "fat_g": 3.3, "carbs_g": 22.6, "fiber_g": 1.4}' WHERE id = '40130ca5-cc7b-402c-947a-aac91566321a';

-- Morue au four à la portugaise
UPDATE recipes SET nutrition = '{"calories": 163, "protein_g": 5.4, "fat_g": 1.7, "carbs_g": 30.3, "fiber_g": 5.7}' WHERE id = '13475540-574e-43fc-b1e6-0dbad6604cfe';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '13475540-574e-43fc-b1e6-0dbad6604cfe' AND NOT ('léger' = ANY(tags));

-- Moules marinières
UPDATE recipes SET nutrition = '{"calories": 1349, "protein_g": 214.4, "fat_g": 42.1, "carbs_g": 27.3, "fiber_g": 2.7}' WHERE id = '5904955a-e4d3-4fa7-b1e5-7717efbc393d';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '5904955a-e4d3-4fa7-b1e5-7717efbc393d' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '5904955a-e4d3-4fa7-b1e5-7717efbc393d' AND NOT ('gourmand' = ANY(tags));

-- Mousse au chocolat facile
UPDATE recipes SET nutrition = '{"calories": 134, "protein_g": 5.4, "fat_g": 4.8, "carbs_g": 16.8, "fiber_g": 0.8}' WHERE id = '4fe5723d-3ee0-47f0-83fb-584094386475';

-- Mousse au chocolat sans beurre et sans œuf
UPDATE recipes SET nutrition = '{"calories": 223, "protein_g": 9.3, "fat_g": 8.7, "carbs_g": 26.3, "fiber_g": 1.2}' WHERE id = '66e3dabc-b411-415e-9e98-7a8cad258e8b';

-- Muffins au chocolat
UPDATE recipes SET nutrition = '{"calories": 181, "protein_g": 6.1, "fat_g": 4.6, "carbs_g": 28.2, "fiber_g": 1.3}' WHERE id = '4f433ea8-851e-4ea0-b06a-58cdcaa3ef8a';

-- Muffins chocolat noir Bio Nestlé Dessert®, huile d''olive & framboise
UPDATE recipes SET nutrition = '{"calories": 207, "protein_g": 6.6, "fat_g": 4.8, "carbs_g": 33.7, "fiber_g": 2.1}' WHERE id = '0abfdad2-8c26-4fec-95e4-4fb7968f3e2e';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '0abfdad2-8c26-4fec-95e4-4fb7968f3e2e' AND NOT ('léger' = ANY(tags));

-- Mug Cake rapide au chocolat
UPDATE recipes SET nutrition = '{"calories": 357, "protein_g": 12.8, "fat_g": 10.5, "carbs_g": 51.6, "fiber_g": 2.4}' WHERE id = '41838439-d478-4372-9e14-ddfb0b1cd707';

-- Naans indiens
UPDATE recipes SET nutrition = '{"calories": 394, "protein_g": 12.0, "fat_g": 8.3, "carbs_g": 66.4, "fiber_g": 3.2}' WHERE id = '5969fa52-29d5-496e-9e8a-146c52b0046a';

-- Nappage nature facile pour tartes sucrées
UPDATE recipes SET nutrition = '{"calories": 80, "protein_g": 1.9, "fat_g": 0.8, "carbs_g": 16.0, "fiber_g": 0.8}' WHERE id = 'b653f232-581f-4ae4-aac7-5d2c26f3005e';

-- Navarin d''agneau
UPDATE recipes SET nutrition = '{"calories": 1343, "protein_g": 88.0, "fat_g": 30.6, "carbs_g": 170.8, "fiber_g": 32.2}' WHERE id = '89cabf4f-8f75-41b4-95d7-2f90eedfcfc5';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '89cabf4f-8f75-41b4-95d7-2f90eedfcfc5' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '89cabf4f-8f75-41b4-95d7-2f90eedfcfc5' AND NOT ('gourmand' = ANY(tags));

-- Noix de St Jacques à la crème
UPDATE recipes SET nutrition = '{"calories": 174, "protein_g": 6.8, "fat_g": 8.4, "carbs_g": 16.5, "fiber_g": 1.3}' WHERE id = '25ed9aa3-32ce-4576-827d-512c8f5cd839';

-- Nuggets de chou-fleur par Laurent Mariotte
UPDATE recipes SET nutrition = '{"calories": 189, "protein_g": 7.3, "fat_g": 6.3, "carbs_g": 25.1, "fiber_g": 3.0}' WHERE id = '5d72a79b-306a-48d6-8a2b-8a8746bd4a61';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '5d72a79b-306a-48d6-8a2b-8a8746bd4a61' AND NOT ('léger' = ANY(tags));

-- Oeufs brouillés nature
UPDATE recipes SET nutrition = '{"calories": 283, "protein_g": 17.4, "fat_g": 19.6, "carbs_g": 8.7, "fiber_g": 0.0}' WHERE id = '4237f01b-8ec8-4a48-b7bb-602329783c30';

-- Oeufs cocottes
UPDATE recipes SET nutrition = '{"calories": 211, "protein_g": 16.8, "fat_g": 13.5, "carbs_g": 4.9, "fiber_g": 0.0}' WHERE id = 'a807430c-16b8-4c6c-852e-df9021368de1';

-- Oeufs en Meurette de ma Maman
UPDATE recipes SET nutrition = '{"calories": 677, "protein_g": 27.5, "fat_g": 12.7, "carbs_g": 110.4, "fiber_g": 6.2}' WHERE id = 'e2ac07dd-a874-4609-a03c-5c9276d24479';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'e2ac07dd-a874-4609-a03c-5c9276d24479' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'e2ac07dd-a874-4609-a03c-5c9276d24479' AND NOT ('gourmand' = ANY(tags));

-- Oeufs mimosa
UPDATE recipes SET nutrition = '{"calories": 454, "protein_g": 20.5, "fat_g": 20.0, "carbs_g": 46.5, "fiber_g": 2.0}' WHERE id = '6556547f-672d-4353-8abe-4acefea0a664';
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '6556547f-672d-4353-8abe-4acefea0a664' AND NOT ('gourmand' = ANY(tags));

-- Oeufs mollets de ma grand-mère
UPDATE recipes SET nutrition = '{"calories": 456, "protein_g": 16.6, "fat_g": 13.8, "carbs_g": 64.8, "fiber_g": 3.0}' WHERE id = '79253691-e945-4849-9104-03f56368beca';

-- Oignons doux des Cévennes farcis par Laurent Mariotte
UPDATE recipes SET nutrition = '{"calories": 226, "protein_g": 20.9, "fat_g": 7.7, "carbs_g": 16.8, "fiber_g": 5.2}' WHERE id = 'ed352c22-3b53-4fab-8a61-6ec36ae87187';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'ed352c22-3b53-4fab-8a61-6ec36ae87187' AND NOT ('protéiné' = ANY(tags));

-- Omelette nature
UPDATE recipes SET nutrition = '{"calories": 153, "protein_g": 9.4, "fat_g": 10.6, "carbs_g": 4.7, "fiber_g": 0.0}' WHERE id = '5eaf90cf-baa2-4e9b-9449-7766cea8c1d3';

-- Pain Matlouh
UPDATE recipes SET nutrition = '{"calories": 297, "protein_g": 17.7, "fat_g": 4.8, "carbs_g": 44.7, "fiber_g": 2.3}' WHERE id = 'ec9d0977-bbed-4aba-8eb1-c91dfcdbaa88';

-- Pain blanc à la cocotte
UPDATE recipes SET nutrition = '{"calories": 613, "protein_g": 14.3, "fat_g": 6.1, "carbs_g": 122.5, "fiber_g": 6.2}' WHERE id = 'c66017a5-4655-4fb2-8cda-b8accc996d3d';

-- Pain brioché
UPDATE recipes SET nutrition = '{"calories": 670, "protein_g": 17.1, "fat_g": 9.0, "carbs_g": 127.3, "fiber_g": 6.3}' WHERE id = '7f2c41e9-57ad-49eb-9a2c-2bd00869b254';

-- Pain d''épices
UPDATE recipes SET nutrition = '{"calories": 358, "protein_g": 10.2, "fat_g": 6.4, "carbs_g": 63.5, "fiber_g": 3.1}' WHERE id = 'ff959fe8-4354-4ae1-b611-aded051c7430';

-- Pain de campagne maison
UPDATE recipes SET nutrition = '{"calories": 608, "protein_g": 14.2, "fat_g": 6.1, "carbs_g": 121.5, "fiber_g": 6.1}' WHERE id = 'bb51dd46-1269-475a-87c3-af8212396cc1';

-- Pain escargot
UPDATE recipes SET nutrition = '{"calories": 444, "protein_g": 11.4, "fat_g": 6.0, "carbs_g": 84.4, "fiber_g": 4.2}' WHERE id = '2fe3d999-8e08-4911-bdd9-6f34b9621040';

-- Pain farci roulé jambon fromage
UPDATE recipes SET nutrition = '{"calories": 595, "protein_g": 75.2, "fat_g": 30.6, "carbs_g": 2.2, "fiber_g": 0.1}' WHERE id = '63abfcb2-3f76-479c-976d-e4d74075bdfb';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '63abfcb2-3f76-479c-976d-e4d74075bdfb' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '63abfcb2-3f76-479c-976d-e4d74075bdfb' AND NOT ('gourmand' = ANY(tags));

-- Pain frit
UPDATE recipes SET nutrition = '{"calories": 233, "protein_g": 5.4, "fat_g": 2.3, "carbs_g": 46.5, "fiber_g": 2.3}' WHERE id = 'ccf5ee3b-c851-4a33-8e9a-f6cb93b64d4d';

-- Pain perdu
UPDATE recipes SET nutrition = '{"calories": 331, "protein_g": 13.1, "fat_g": 11.6, "carbs_g": 42.5, "fiber_g": 1.9}' WHERE id = '5c23118f-32d2-458b-bcd3-421235ff380d';

-- Pain pitas Libanais
UPDATE recipes SET nutrition = '{"calories": 235, "protein_g": 5.9, "fat_g": 3.0, "carbs_g": 45.1, "fiber_g": 2.3}' WHERE id = '3ec7b11a-ebf1-4872-9cd4-a5d290714ef7';

-- Pain roulé aux noisettes
UPDATE recipes SET nutrition = '{"calories": 825, "protein_g": 19.3, "fat_g": 8.3, "carbs_g": 165.0, "fiber_g": 8.3}' WHERE id = '2f1b753f-fc28-49e3-a99e-b42e0a11cc3f';

-- Pains sandwichs utltra moelleux
UPDATE recipes SET nutrition = '{"calories": 430, "protein_g": 12.3, "fat_g": 7.8, "carbs_g": 76.1, "fiber_g": 3.7}' WHERE id = '4a004c73-d644-4de5-ba78-790368b9e8e0';

-- Palmiers apéro aux tomates séchées
UPDATE recipes SET nutrition = '{"calories": 24, "protein_g": 0.7, "fat_g": 0.4, "carbs_g": 4.3, "fiber_g": 0.3}' WHERE id = '2aa1d609-ca64-442c-b2b5-162d5fd51eb9';

-- Pampushky sauce à l''ail et aneth
UPDATE recipes SET nutrition = '{"calories": 361, "protein_g": 11.0, "fat_g": 7.6, "carbs_g": 60.7, "fiber_g": 3.0}' WHERE id = '876e2906-1fa9-4352-aae8-c303d5e8a17f';

-- Pancakes faciles et rapides
UPDATE recipes SET nutrition = '{"calories": 576, "protein_g": 20.3, "fat_g": 16.4, "carbs_g": 85.0, "fiber_g": 4.0}' WHERE id = '3465462a-9294-4dec-b4ac-050c90e883c0';

-- Panisses au four
UPDATE recipes SET nutrition = '{"calories": 834, "protein_g": 23.3, "fat_g": 7.8, "carbs_g": 162.9, "fiber_g": 12.0}' WHERE id = '7390d771-402f-47b3-affd-6b9d482ffee5';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '7390d771-402f-47b3-affd-6b9d482ffee5' AND NOT ('protéiné' = ANY(tags));

-- Paris-Brest généreux
UPDATE recipes SET nutrition = '{"calories": 325, "protein_g": 14.7, "fat_g": 14.5, "carbs_g": 32.9, "fiber_g": 1.4}' WHERE id = '78d13693-094b-4dc4-ae0d-18faaebf12b0';

-- Paupiettes de porc au Cookeo
UPDATE recipes SET nutrition = '{"calories": 473, "protein_g": 57.8, "fat_g": 24.2, "carbs_g": 4.0, "fiber_g": 0.8}' WHERE id = 'd06e20ee-b0ea-4239-a78a-b9ec724162cb';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'd06e20ee-b0ea-4239-a78a-b9ec724162cb' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'd06e20ee-b0ea-4239-a78a-b9ec724162cb' AND NOT ('gourmand' = ANY(tags));

-- Paupiettes de veau
UPDATE recipes SET nutrition = '{"calories": 1134, "protein_g": 108.6, "fat_g": 41.6, "carbs_g": 76.6, "fiber_g": 4.0}' WHERE id = '296ec8cd-b02f-402a-93e6-b674a0278e74';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '296ec8cd-b02f-402a-93e6-b674a0278e74' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '296ec8cd-b02f-402a-93e6-b674a0278e74' AND NOT ('gourmand' = ANY(tags));

-- Pavés de saumon au Air Fryer
UPDATE recipes SET nutrition = '{"calories": 181, "protein_g": 31.6, "fat_g": 6.0, "carbs_g": 0.2, "fiber_g": 0.1}' WHERE id = '4d2fb214-577c-4c9e-9c61-93fab6c0242b';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '4d2fb214-577c-4c9e-9c61-93fab6c0242b' AND NOT ('protéiné' = ANY(tags));

-- Pavés de saumon au four facile
UPDATE recipes SET nutrition = '{"calories": 673, "protein_g": 46.9, "fat_g": 10.8, "carbs_g": 94.1, "fiber_g": 14.8}' WHERE id = 'eb21d172-32cd-4bd5-a69c-4be539c8130a';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'eb21d172-32cd-4bd5-a69c-4be539c8130a' AND NOT ('protéiné' = ANY(tags));

-- Petites bouchées à la noix de coco
UPDATE recipes SET nutrition = '{"calories": 138, "protein_g": 4.2, "fat_g": 2.9, "carbs_g": 23.3, "fiber_g": 1.1}' WHERE id = '35c3539d-d388-4e06-80c2-cada1a494e81';

-- Petits pois à l''ancienne
UPDATE recipes SET nutrition = '{"calories": 266, "protein_g": 22.0, "fat_g": 8.9, "carbs_g": 22.8, "fiber_g": 6.1}' WHERE id = '3df3d317-65d1-409a-9db5-68bb511228c4';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '3df3d317-65d1-409a-9db5-68bb511228c4' AND NOT ('protéiné' = ANY(tags));

-- Petits soufflés légers au chou-fleur
UPDATE recipes SET nutrition = '{"calories": 180, "protein_g": 10.7, "fat_g": 10.7, "carbs_g": 9.6, "fiber_g": 2.0}' WHERE id = '19af7996-5054-4a1f-8aa6-2c2cf13d1403';

-- Pizza de pastèque par Laurent Mariotte
UPDATE recipes SET nutrition = '{"calories": 25, "protein_g": 1.3, "fat_g": 1.1, "carbs_g": 2.5, "fiber_g": 0.6}' WHERE id = '17723ed7-44aa-4251-ace1-d73f98608a5d';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '17723ed7-44aa-4251-ace1-d73f98608a5d' AND NOT ('léger' = ANY(tags));

-- Pizza maison
UPDATE recipes SET nutrition = '{"calories": 560, "protein_g": 24.8, "fat_g": 10.2, "carbs_g": 89.0, "fiber_g": 13.6}' WHERE id = 'bbf20688-e550-4213-8804-72f1fcbdabf8';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'bbf20688-e550-4213-8804-72f1fcbdabf8' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'bbf20688-e550-4213-8804-72f1fcbdabf8' AND NOT ('gourmand' = ANY(tags));

-- Pizza margherita
UPDATE recipes SET nutrition = '{"calories": 201, "protein_g": 8.2, "fat_g": 5.9, "carbs_g": 27.8, "fiber_g": 3.3}' WHERE id = 'ad440bfe-0145-4a4d-b674-d8951de78654';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'ad440bfe-0145-4a4d-b674-d8951de78654' AND NOT ('léger' = ANY(tags));

-- Poireaux à la vinaigrette
UPDATE recipes SET nutrition = '{"calories": 205, "protein_g": 6.2, "fat_g": 4.2, "carbs_g": 34.6, "fiber_g": 4.8}' WHERE id = '7bfc8a81-5ed0-403d-a515-e903ad1ef5e8';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '7bfc8a81-5ed0-403d-a515-e903ad1ef5e8' AND NOT ('léger' = ANY(tags));

-- Poires rôties au miel, yaourt grec à la vanille et semoule grillée
UPDATE recipes SET nutrition = '{"calories": 4955, "protein_g": 302.2, "fat_g": 338.6, "carbs_g": 165.0, "fiber_g": 2.1}' WHERE id = '3034d22f-a18b-43e4-9e5c-ab569700f1d6';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '3034d22f-a18b-43e4-9e5c-ab569700f1d6' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '3034d22f-a18b-43e4-9e5c-ab569700f1d6' AND NOT ('gourmand' = ANY(tags));

-- Poivrons au Air Fryer
UPDATE recipes SET nutrition = '{"calories": 50, "protein_g": 2.4, "fat_g": 0.6, "carbs_g": 8.2, "fiber_g": 3.2}' WHERE id = 'f0df0a2e-0e72-4afe-81a1-5b1606659599';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'f0df0a2e-0e72-4afe-81a1-5b1606659599' AND NOT ('léger' = ANY(tags));

-- Polenta au four
UPDATE recipes SET nutrition = '{"calories": 667, "protein_g": 17.0, "fat_g": 8.0, "carbs_g": 129.1, "fiber_g": 7.6}' WHERE id = '64e7a129-72f1-4e15-b051-0c778643039e';

-- Polenta au thermomix
UPDATE recipes SET nutrition = '{"calories": 933, "protein_g": 27.3, "fat_g": 17.9, "carbs_g": 162.1, "fiber_g": 8.0}' WHERE id = '006956b9-749d-42b7-86f0-1b24c0ceb583';

-- Polenta aux reblochon et Diot de Savoie
UPDATE recipes SET nutrition = '{"calories": 1405, "protein_g": 36.5, "fat_g": 16.5, "carbs_g": 271.0, "fiber_g": 18.9}' WHERE id = 'fa20086c-d6ea-40e9-aaa2-972eecf1b77d';

-- Polenta crémeuse
UPDATE recipes SET nutrition = '{"calories": 519, "protein_g": 13.6, "fat_g": 7.5, "carbs_g": 97.2, "fiber_g": 4.8}' WHERE id = '8c40310c-6668-40f5-bdd0-d46de635d30b';

-- Pomme de terre au barbecue avec aluminium
UPDATE recipes SET nutrition = '{"calories": 99, "protein_g": 2.6, "fat_g": 1.6, "carbs_g": 18.0, "fiber_g": 3.4}' WHERE id = '36e50404-d2e3-4455-bf4e-79845e1ba960';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '36e50404-d2e3-4455-bf4e-79845e1ba960' AND NOT ('léger' = ANY(tags));

-- Pommes de terres sautées
UPDATE recipes SET nutrition = '{"calories": 141, "protein_g": 2.4, "fat_g": 0.9, "carbs_g": 30.2, "fiber_g": 4.2}' WHERE id = '5e75066f-ece9-4491-b9bf-1503e92dce23';

-- Porridge
UPDATE recipes SET nutrition = '{"calories": 520, "protein_g": 24.6, "fat_g": 24.4, "carbs_g": 49.0, "fiber_g": 2.0}' WHERE id = '9bec3cff-73be-490d-b7e4-45e9a642b9e4';

-- Pot-au-feu facile
UPDATE recipes SET nutrition = '{"calories": 422, "protein_g": 45.1, "fat_g": 16.3, "carbs_g": 21.2, "fiber_g": 7.0}' WHERE id = 'bf4716a5-6e87-421d-b424-1a3e5be39341';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'bf4716a5-6e87-421d-b424-1a3e5be39341' AND NOT ('protéiné' = ANY(tags));

-- Potatoes au Air Fryer
UPDATE recipes SET nutrition = '{"calories": 114, "protein_g": 1.8, "fat_g": 0.7, "carbs_g": 24.6, "fiber_g": 4.2}' WHERE id = '792cd5ac-7869-4aaf-a601-d4b9dcff244c';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '792cd5ac-7869-4aaf-a601-d4b9dcff244c' AND NOT ('léger' = ANY(tags));

-- Potimarrons farcis aux lardons, Saint-nectaire et châtaignes
UPDATE recipes SET nutrition = '{"calories": 236, "protein_g": 16.2, "fat_g": 11.8, "carbs_g": 14.8, "fiber_g": 3.3}' WHERE id = 'bfc3b3a6-5202-4ecc-b657-454e083d27e9';

-- Poulet au four simple et savoureux
UPDATE recipes SET nutrition = '{"calories": 65, "protein_g": 6.9, "fat_g": 2.4, "carbs_g": 3.4, "fiber_g": 1.2}' WHERE id = '2e4ebdfd-7c89-4a30-b35c-d4bffe9a9ff7';

-- Poulet maison façon KFC
UPDATE recipes SET nutrition = '{"calories": 479, "protein_g": 42.0, "fat_g": 18.1, "carbs_g": 35.0, "fiber_g": 1.9}' WHERE id = 'ee274549-7179-4020-897f-5301dd42e19d';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'ee274549-7179-4020-897f-5301dd42e19d' AND NOT ('protéiné' = ANY(tags));

-- Poêlée de champignons et d''oignons
UPDATE recipes SET nutrition = '{"calories": 338, "protein_g": 41.9, "fat_g": 15.4, "carbs_g": 6.3, "fiber_g": 2.5}' WHERE id = '02d20a88-fcb9-40bd-b0ab-0d31495df8c1';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '02d20a88-fcb9-40bd-b0ab-0d31495df8c1' AND NOT ('protéiné' = ANY(tags));

-- Punch aux fruits
UPDATE recipes SET nutrition = '{"calories": 119, "protein_g": 2.5, "fat_g": 2.1, "carbs_g": 21.7, "fiber_g": 2.8}' WHERE id = 'c30598dc-2d54-4472-97ba-74f714ca8c84';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'c30598dc-2d54-4472-97ba-74f714ca8c84' AND NOT ('léger' = ANY(tags));

-- Purée de courge butternut
UPDATE recipes SET nutrition = '{"calories": 132, "protein_g": 3.9, "fat_g": 3.4, "carbs_g": 20.8, "fiber_g": 3.3}' WHERE id = 'c65c920d-238c-494a-9ac2-8e8cfde97f4c';

-- Purée de panais et carottes au Thermomix
UPDATE recipes SET nutrition = '{"calories": 240, "protein_g": 6.6, "fat_g": 3.3, "carbs_g": 45.0, "fiber_g": 3.8}' WHERE id = '26966437-2bb5-4414-b369-5abfafcdc6d9';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '26966437-2bb5-4414-b369-5abfafcdc6d9' AND NOT ('léger' = ANY(tags));

-- Purée de patates douces
UPDATE recipes SET nutrition = '{"calories": 107, "protein_g": 5.8, "fat_g": 4.1, "carbs_g": 11.1, "fiber_g": 3.5}' WHERE id = 'c33c06bc-9619-4e6a-8abb-1e214f8e6d5c';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'c33c06bc-9619-4e6a-8abb-1e214f8e6d5c' AND NOT ('léger' = ANY(tags));

-- Purée de pommes de terre et de carottes
UPDATE recipes SET nutrition = '{"calories": 209, "protein_g": 7.0, "fat_g": 3.6, "carbs_g": 35.7, "fiber_g": 8.4}' WHERE id = 'ae8a8235-f5ea-42eb-8302-90923ca648fd';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'ae8a8235-f5ea-42eb-8302-90923ca648fd' AND NOT ('léger' = ANY(tags));

-- Purée de pommes de terre maison
UPDATE recipes SET nutrition = '{"calories": 222, "protein_g": 7.2, "fat_g": 6.6, "carbs_g": 32.6, "fiber_g": 5.0}' WHERE id = '0d42242c-3f40-4baa-8508-91d82b598405';

-- Purée de pommes de terre à ma façon
UPDATE recipes SET nutrition = '{"calories": 256, "protein_g": 9.2, "fat_g": 8.3, "carbs_g": 35.2, "fiber_g": 5.8}' WHERE id = 'f5b60779-73e2-4042-8ed4-57c18f80e563';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'f5b60779-73e2-4042-8ed4-57c18f80e563' AND NOT ('léger' = ANY(tags));

-- Purée gourmande au chou-fleur
UPDATE recipes SET nutrition = '{"calories": 97, "protein_g": 4.1, "fat_g": 3.5, "carbs_g": 11.7, "fiber_g": 2.3}' WHERE id = '34a6f2af-c338-4eb8-a1de-7d2d81a5d3d3';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '34a6f2af-c338-4eb8-a1de-7d2d81a5d3d3' AND NOT ('léger' = ANY(tags));

-- Purée pommes de terre et petits pois
UPDATE recipes SET nutrition = '{"calories": 132, "protein_g": 4.8, "fat_g": 4.1, "carbs_g": 18.5, "fiber_g": 3.3}' WHERE id = '550f19ad-c724-4551-b62c-5652af8f6846';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '550f19ad-c724-4551-b62c-5652af8f6846' AND NOT ('léger' = ANY(tags));

-- Purée à ma façon
UPDATE recipes SET nutrition = '{"calories": 172, "protein_g": 6.9, "fat_g": 3.3, "carbs_g": 27.8, "fiber_g": 5.4}' WHERE id = '913ec28d-e31c-44df-acc6-f5b4fe8477f6';

-- Pâte à crêpes : la meilleure recette facile et rapide
UPDATE recipes SET nutrition = '{"calories": 316, "protein_g": 13.7, "fat_g": 13.0, "carbs_g": 35.1, "fiber_g": 1.5}' WHERE id = '0169159d-4c78-4981-94af-13ce87472215';

-- Pâte à gaufres moelleuse
UPDATE recipes SET nutrition = '{"calories": 520, "protein_g": 25.9, "fat_g": 20.2, "carbs_g": 57.0, "fiber_g": 2.5}' WHERE id = '3787f7dd-225d-4b18-805c-daa9d3e36429';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '3787f7dd-225d-4b18-805c-daa9d3e36429' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '3787f7dd-225d-4b18-805c-daa9d3e36429' AND NOT ('gourmand' = ANY(tags));

-- Pâte à panini à la machine à pain
UPDATE recipes SET nutrition = '{"calories": 393, "protein_g": 10.4, "fat_g": 5.9, "carbs_g": 73.0, "fiber_g": 3.6}' WHERE id = '565c45ea-9daa-411d-b640-cd18082c3ca2';

-- Pâtes aux quatre fromages
UPDATE recipes SET nutrition = '{"calories": 433, "protein_g": 14.8, "fat_g": 11.8, "carbs_g": 65.3, "fiber_g": 3.2}' WHERE id = '3be767e8-e905-4e41-8e60-8aa740bd9f56';

-- Pâtes aux œufs brouillés
UPDATE recipes SET nutrition = '{"calories": 375, "protein_g": 13.4, "fat_g": 10.7, "carbs_g": 54.9, "fiber_g": 3.0}' WHERE id = 'd792332d-2fe2-4863-b515-774f78073133';

-- Pâtes linguine aux crevettes, sauce crémeuse à l''ail, paprika fumé et citron
UPDATE recipes SET nutrition = '{"calories": 928, "protein_g": 133.5, "fat_g": 29.8, "carbs_g": 30.4, "fiber_g": 2.6}' WHERE id = '9570e18f-05bb-4d43-ab3b-3759748cd360';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '9570e18f-05bb-4d43-ab3b-3759748cd360' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '9570e18f-05bb-4d43-ab3b-3759748cd360' AND NOT ('gourmand' = ANY(tags));

-- Pâtes à la Norma
UPDATE recipes SET nutrition = '{"calories": 470, "protein_g": 13.9, "fat_g": 8.1, "carbs_g": 82.8, "fiber_g": 7.2}' WHERE id = 'b5f77bba-8722-437a-9a68-f8b6d3f0cd0a';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'b5f77bba-8722-437a-9a68-f8b6d3f0cd0a' AND NOT ('léger' = ANY(tags));

-- Quesadillas à la viande hachée
UPDATE recipes SET nutrition = '{"calories": 497, "protein_g": 26.7, "fat_g": 12.4, "carbs_g": 67.3, "fiber_g": 5.2}' WHERE id = '1e59a215-07dd-4228-9d69-636002bbf393';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '1e59a215-07dd-4228-9d69-636002bbf393' AND NOT ('protéiné' = ANY(tags));

-- Quiche au poireau et saumon fumé
UPDATE recipes SET nutrition = '{"calories": 167, "protein_g": 10.0, "fat_g": 6.2, "carbs_g": 17.3, "fiber_g": 1.4}' WHERE id = 'cf72015e-1049-4fb8-8547-ed2f2c1a7a3a';

-- Quiche aux poireaux et lardons
UPDATE recipes SET nutrition = '{"calories": 224, "protein_g": 12.3, "fat_g": 10.6, "carbs_g": 19.3, "fiber_g": 1.7}' WHERE id = 'd5590edd-4114-418a-8bf9-7aefb4954c38';

-- Quiche aux poireaux sans pâte
UPDATE recipes SET nutrition = '{"calories": 525, "protein_g": 41.2, "fat_g": 25.5, "carbs_g": 31.4, "fiber_g": 2.0}' WHERE id = '4a3c6a82-57a8-481e-a956-37842957eaee';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '4a3c6a82-57a8-481e-a956-37842957eaee' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '4a3c6a82-57a8-481e-a956-37842957eaee' AND NOT ('gourmand' = ANY(tags));

-- Quiche jambon, fromage, tomate, olives
UPDATE recipes SET nutrition = '{"calories": 303, "protein_g": 18.1, "fat_g": 12.3, "carbs_g": 28.6, "fiber_g": 6.0}' WHERE id = 'ad0b9c2b-0abe-4030-9a8a-a573557200bd';

-- Quinoa au poulet et légumes du soleil
UPDATE recipes SET nutrition = '{"calories": 463, "protein_g": 52.5, "fat_g": 20.0, "carbs_g": 15.7, "fiber_g": 5.1}' WHERE id = '84ee6438-98bd-49a8-a4a5-4f686deff3a3';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '84ee6438-98bd-49a8-a4a5-4f686deff3a3' AND NOT ('protéiné' = ANY(tags));

-- Ratatouille confite au four
UPDATE recipes SET nutrition = '{"calories": 173, "protein_g": 8.4, "fat_g": 1.7, "carbs_g": 29.2, "fiber_g": 10.9}' WHERE id = 'f0aaf593-b092-4e29-a079-ae76421034a2';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'f0aaf593-b092-4e29-a079-ae76421034a2' AND NOT ('léger' = ANY(tags));

-- Recette de caramel au beurre salé maison
UPDATE recipes SET nutrition = '{"calories": 83, "protein_g": 9.7, "fat_g": 4.3, "carbs_g": 1.3, "fiber_g": 0.0}' WHERE id = 'aab37f11-ef3e-4776-b06f-9a20aa93ec53';

-- Risotto au chorizo avec le Cookeo
UPDATE recipes SET nutrition = '{"calories": 764, "protein_g": 24.3, "fat_g": 11.4, "carbs_g": 137.9, "fiber_g": 7.5}' WHERE id = '536a2ec7-4dbe-436d-9260-dcb89cff84ed';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '536a2ec7-4dbe-436d-9260-dcb89cff84ed' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '536a2ec7-4dbe-436d-9260-dcb89cff84ed' AND NOT ('gourmand' = ANY(tags));

-- Risotto aux asperges vertes et parmesan
UPDATE recipes SET nutrition = '{"calories": 1612, "protein_g": 40.1, "fat_g": 18.3, "carbs_g": 314.9, "fiber_g": 17.9}' WHERE id = '5e8f5c7b-03dc-4bbe-bfdd-c4cd2bd873e3';

-- Risotto aux champignons : la vraie recette
UPDATE recipes SET nutrition = '{"calories": 1086, "protein_g": 53.5, "fat_g": 22.4, "carbs_g": 162.7, "fiber_g": 12.1}' WHERE id = 'b29ccdac-951b-422a-911e-55be2d766343';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'b29ccdac-951b-422a-911e-55be2d766343' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'b29ccdac-951b-422a-911e-55be2d766343' AND NOT ('gourmand' = ANY(tags));

-- Risotto aux champignons facile
UPDATE recipes SET nutrition = '{"calories": 947, "protein_g": 33.1, "fat_g": 14.3, "carbs_g": 167.5, "fiber_g": 9.0}' WHERE id = '1df9c834-0896-429d-9f3b-6d5a17077109';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '1df9c834-0896-429d-9f3b-6d5a17077109' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '1df9c834-0896-429d-9f3b-6d5a17077109' AND NOT ('gourmand' = ANY(tags));

-- Riz au Cookeo
UPDATE recipes SET nutrition = '{"calories": 563, "protein_g": 13.1, "fat_g": 5.6, "carbs_g": 112.5, "fiber_g": 5.6}' WHERE id = '4899e1d4-84db-4eb7-987c-34839d815949';

-- Riz au lait au chocolat - Thermomix
UPDATE recipes SET nutrition = '{"calories": 587, "protein_g": 30.7, "fat_g": 27.1, "carbs_g": 53.5, "fiber_g": 2.1}' WHERE id = 'ad7b04e3-e9ed-4dcb-88c9-6e00b734a717';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'ad7b04e3-e9ed-4dcb-88c9-6e00b734a717' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'ad7b04e3-e9ed-4dcb-88c9-6e00b734a717' AND NOT ('gourmand' = ANY(tags));

-- Riz au lait concentré vanille
UPDATE recipes SET nutrition = '{"calories": 480, "protein_g": 15.7, "fat_g": 11.7, "carbs_g": 76.2, "fiber_g": 3.6}' WHERE id = '87e67386-fe0a-4170-87c5-fbebde2a4716';

-- Riz au lait crémeux à la vanille
UPDATE recipes SET nutrition = '{"calories": 291, "protein_g": 17.2, "fat_g": 16.1, "carbs_g": 18.7, "fiber_g": 0.6}' WHERE id = 'b1ffd525-9b4a-47b4-a0c3-6f39b7cc17b7';

-- Riz cantonais facile
UPDATE recipes SET nutrition = '{"calories": 286, "protein_g": 14.8, "fat_g": 6.9, "carbs_g": 40.0, "fiber_g": 3.5}' WHERE id = 'fd4efa5a-3e0f-4dd2-952d-dd1292cd49e9';

-- Riz pilaf traditionnel
UPDATE recipes SET nutrition = '{"calories": 741, "protein_g": 38.1, "fat_g": 14.6, "carbs_g": 110.9, "fiber_g": 7.6}' WHERE id = 'eada82de-2d92-4abf-8d3d-17ab3a519a0c';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'eada82de-2d92-4abf-8d3d-17ab3a519a0c' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'eada82de-2d92-4abf-8d3d-17ab3a519a0c' AND NOT ('gourmand' = ANY(tags));

-- Riz pour sushis
UPDATE recipes SET nutrition = '{"calories": 1172, "protein_g": 27.3, "fat_g": 12.2, "carbs_g": 233.4, "fiber_g": 11.7}' WHERE id = '814cd3e4-e0bb-4b13-9c9b-f3f1b0789c23';

-- Rougail saucisse
UPDATE recipes SET nutrition = '{"calories": 769, "protein_g": 80.9, "fat_g": 33.0, "carbs_g": 32.3, "fiber_g": 8.2}' WHERE id = 'bdee75f7-b995-40cb-92f9-1cdd7e1313b8';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'bdee75f7-b995-40cb-92f9-1cdd7e1313b8' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'bdee75f7-b995-40cb-92f9-1cdd7e1313b8' AND NOT ('gourmand' = ANY(tags));

-- Rougail saucisse au Cookeo
UPDATE recipes SET nutrition = '{"calories": 491, "protein_g": 42.7, "fat_g": 15.7, "carbs_g": 42.3, "fiber_g": 5.4}' WHERE id = 'c9ad457c-b5df-4a6e-bf30-45e4ebdafbe6';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'c9ad457c-b5df-4a6e-bf30-45e4ebdafbe6' AND NOT ('protéiné' = ANY(tags));

-- Rouleaux de printemps simplifiés
UPDATE recipes SET nutrition = '{"calories": 346, "protein_g": 42.2, "fat_g": 8.5, "carbs_g": 23.4, "fiber_g": 5.8}' WHERE id = '43e2c4d1-ba95-4a40-a25e-25b2c9ae2e6d';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '43e2c4d1-ba95-4a40-a25e-25b2c9ae2e6d' AND NOT ('protéiné' = ANY(tags));

-- Roulés de jambon blanc au Reblochon AOP panure pistaches
UPDATE recipes SET nutrition = '{"calories": 386, "protein_g": 23.9, "fat_g": 12.8, "carbs_g": 42.4, "fiber_g": 2.0}' WHERE id = '719abfe7-6354-4db5-8624-a1e33663dc0a';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '719abfe7-6354-4db5-8624-a1e33663dc0a' AND NOT ('protéiné' = ANY(tags));

-- Roulés feuilletés à la saucisse
UPDATE recipes SET nutrition = '{"calories": 91, "protein_g": 3.3, "fat_g": 3.3, "carbs_g": 11.5, "fiber_g": 0.6}' WHERE id = '4d13fc0f-c01d-4b99-bf06-a7646319a7cf';

-- Rôti de boeuf au four tout simple
UPDATE recipes SET nutrition = '{"calories": 545, "protein_g": 52.5, "fat_g": 19.9, "carbs_g": 36.9, "fiber_g": 2.2}' WHERE id = '8557d11c-f8fc-4c67-bf1e-e9f544697a33';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '8557d11c-f8fc-4c67-bf1e-e9f544697a33' AND NOT ('protéiné' = ANY(tags));

-- Rôti de porc tout simple
UPDATE recipes SET nutrition = '{"calories": 147, "protein_g": 14.0, "fat_g": 5.6, "carbs_g": 9.7, "fiber_g": 1.2}' WHERE id = 'a0a7fc0d-0b28-454c-bf82-ced021d97521';

-- Rôti de veau au four
UPDATE recipes SET nutrition = '{"calories": 231, "protein_g": 25.2, "fat_g": 9.5, "carbs_g": 10.2, "fiber_g": 0.6}' WHERE id = 'c5e6798d-74b3-45fe-afd1-c4d8a9490155';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'c5e6798d-74b3-45fe-afd1-c4d8a9490155' AND NOT ('protéiné' = ANY(tags));

-- Salade César
UPDATE recipes SET nutrition = '{"calories": 209, "protein_g": 7.6, "fat_g": 6.5, "carbs_g": 29.2, "fiber_g": 1.9}' WHERE id = '085f1ffa-7572-4889-8a2c-efb7b19bb546';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '085f1ffa-7572-4889-8a2c-efb7b19bb546' AND NOT ('léger' = ANY(tags));

-- Salade de fruits hivernale
UPDATE recipes SET nutrition = '{"calories": 207, "protein_g": 3.6, "fat_g": 2.4, "carbs_g": 41.6, "fiber_g": 6.5}' WHERE id = 'a180bd31-f8af-42cd-826d-e3be5572f150';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'a180bd31-f8af-42cd-826d-e3be5572f150' AND NOT ('léger' = ANY(tags));

-- Salade de fruits kiwis, bananes, fraises, ananas
UPDATE recipes SET nutrition = '{"calories": 176, "protein_g": 2.7, "fat_g": 1.0, "carbs_g": 38.2, "fiber_g": 6.0}' WHERE id = '3ebc4510-59c8-4751-8560-5a7400e1324a';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '3ebc4510-59c8-4751-8560-5a7400e1324a' AND NOT ('léger' = ANY(tags));

-- Samoussa rapide au boeuf
UPDATE recipes SET nutrition = '{"calories": 107, "protein_g": 8.6, "fat_g": 3.3, "carbs_g": 10.1, "fiber_g": 1.7}' WHERE id = 'd859a50b-e149-404b-8545-26573be5f878';

-- Sandwich au poulet
UPDATE recipes SET nutrition = '{"calories": 61, "protein_g": 4.8, "fat_g": 1.9, "carbs_g": 5.7, "fiber_g": 1.5}' WHERE id = 'df3f35ea-889d-41e8-b3e6-d8610b48c73a';

-- Sandwich japonais au porc pané (Katsu Sando)
UPDATE recipes SET nutrition = '{"calories": 788, "protein_g": 50.5, "fat_g": 23.1, "carbs_g": 91.1, "fiber_g": 5.1}' WHERE id = '40a68d46-f5bd-460c-80a6-e6464da7a704';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '40a68d46-f5bd-460c-80a6-e6464da7a704' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '40a68d46-f5bd-460c-80a6-e6464da7a704' AND NOT ('gourmand' = ANY(tags));

-- Sardines au barbecue
UPDATE recipes SET nutrition = '{"calories": 640, "protein_g": 105.7, "fat_g": 20.2, "carbs_g": 8.6, "fiber_g": 1.6}' WHERE id = '24ce4b8c-70e5-42b7-8d60-df2be0fcb190';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '24ce4b8c-70e5-42b7-8d60-df2be0fcb190' AND NOT ('protéiné' = ANY(tags));

-- Saumon Gravlax : recette facile
UPDATE recipes SET nutrition = '{"calories": 231, "protein_g": 35.8, "fat_g": 7.0, "carbs_g": 6.1, "fiber_g": 0.4}' WHERE id = 'fc013b98-f0fd-421b-b51b-e13655646c95';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'fc013b98-f0fd-421b-b51b-e13655646c95' AND NOT ('protéiné' = ANY(tags));

-- Sauté de porc à la crème de moutarde
UPDATE recipes SET nutrition = '{"calories": 985, "protein_g": 76.9, "fat_g": 32.5, "carbs_g": 92.1, "fiber_g": 7.9}' WHERE id = 'e91d1865-edfb-469d-9807-20f5079e26d3';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'e91d1865-edfb-469d-9807-20f5079e26d3' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'e91d1865-edfb-469d-9807-20f5079e26d3' AND NOT ('gourmand' = ANY(tags));

-- Scones faciles
UPDATE recipes SET nutrition = '{"calories": 292, "protein_g": 10.1, "fat_g": 8.0, "carbs_g": 43.9, "fiber_g": 2.1}' WHERE id = 'bf47bddb-e4ac-4d8c-a88b-f7d9056378c4';

-- Selle d''agneau moutardée et sa purée
UPDATE recipes SET nutrition = '{"calories": 84, "protein_g": 2.4, "fat_g": 2.0, "carbs_g": 13.8, "fiber_g": 1.0}' WHERE id = 'd2a5b7e4-a48d-4643-9ac2-47fe1b502642';

-- Semoule au lait et à la vanille
UPDATE recipes SET nutrition = '{"calories": 326, "protein_g": 21.2, "fat_g": 19.2, "carbs_g": 16.4, "fiber_g": 0.4}' WHERE id = '500fcb38-6175-41f6-80b5-a3212fcc4a67';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '500fcb38-6175-41f6-80b5-a3212fcc4a67' AND NOT ('protéiné' = ANY(tags));

-- Semoule aux épices
UPDATE recipes SET nutrition = '{"calories": 303, "protein_g": 29.9, "fat_g": 6.5, "carbs_g": 30.5, "fiber_g": 1.7}' WHERE id = '2b2fdc1d-0f6e-423f-9955-67684c4844ce';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '2b2fdc1d-0f6e-423f-9955-67684c4844ce' AND NOT ('protéiné' = ANY(tags));

-- Sirop de fraises gourmand pour brochettes de Fraises du Périgord IGP
UPDATE recipes SET nutrition = '{"calories": 242, "protein_g": 5.4, "fat_g": 2.9, "carbs_g": 47.4, "fiber_g": 3.3}' WHERE id = '789d1a0d-0348-475f-aecb-1b44f82c6919';

-- Smoothie fruits rouges/banane
UPDATE recipes SET nutrition = '{"calories": 263, "protein_g": 12.1, "fat_g": 13.0, "carbs_g": 23.5, "fiber_g": 2.8}' WHERE id = '13c4c4eb-551b-4e8a-b4d3-81faaaffa7a9';

-- Sorbet express à la framboise
UPDATE recipes SET nutrition = '{"calories": 166, "protein_g": 3.9, "fat_g": 2.4, "carbs_g": 31.5, "fiber_g": 3.8}' WHERE id = '6453f53b-d92d-4ee9-81d2-ecca22e10649';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '6453f53b-d92d-4ee9-81d2-ecca22e10649' AND NOT ('léger' = ANY(tags));

-- Soufflé au fromage
UPDATE recipes SET nutrition = '{"calories": 321, "protein_g": 18.1, "fat_g": 19.6, "carbs_g": 17.5, "fiber_g": 0.5}' WHERE id = 'e89803d0-5fa1-4edb-b64d-83a736049043';

-- Soupe au chou vert
UPDATE recipes SET nutrition = '{"calories": 475, "protein_g": 32.3, "fat_g": 14.2, "carbs_g": 51.8, "fiber_g": 7.5}' WHERE id = 'b78ad73e-f726-4955-bdeb-8a7d9b22ae11';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'b78ad73e-f726-4955-bdeb-8a7d9b22ae11' AND NOT ('protéiné' = ANY(tags));

-- Soupe aux 7 légumes
UPDATE recipes SET nutrition = '{"calories": 210, "protein_g": 8.3, "fat_g": 4.0, "carbs_g": 33.9, "fiber_g": 7.8}' WHERE id = '97ce3e09-a2e9-40ea-aaea-dba68e464a1e';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '97ce3e09-a2e9-40ea-aaea-dba68e464a1e' AND NOT ('léger' = ANY(tags));

-- Soupe de cresson
UPDATE recipes SET nutrition = '{"calories": 165, "protein_g": 4.5, "fat_g": 1.8, "carbs_g": 31.2, "fiber_g": 4.5}' WHERE id = 'fd4fd973-edf5-4508-a10e-e8111e984760';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'fd4fd973-edf5-4508-a10e-e8111e984760' AND NOT ('léger' = ANY(tags));

-- Soupe de lentille corail aux carottes et lait de coco
UPDATE recipes SET nutrition = '{"calories": 808, "protein_g": 20.4, "fat_g": 8.1, "carbs_g": 159.4, "fiber_g": 11.3}' WHERE id = '1a955205-72d5-4d16-bad9-c5d4cd79ea9d';

-- Soupe de potiron à la Juju
UPDATE recipes SET nutrition = '{"calories": 107, "protein_g": 4.2, "fat_g": 2.3, "carbs_g": 16.7, "fiber_g": 4.4}' WHERE id = '461ae64a-b08b-49a5-b487-b57acd68dc7c';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '461ae64a-b08b-49a5-b487-b57acd68dc7c' AND NOT ('léger' = ANY(tags));

-- Soupe de régime au chou
UPDATE recipes SET nutrition = '{"calories": 285, "protein_g": 11.7, "fat_g": 2.5, "carbs_g": 51.2, "fiber_g": 16.9}' WHERE id = 'fc1fa2ef-9d15-4512-b601-eb20e9dcd7d8';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'fc1fa2ef-9d15-4512-b601-eb20e9dcd7d8' AND NOT ('léger' = ANY(tags));

-- Soupe onctueuse de butternut
UPDATE recipes SET nutrition = '{"calories": 92, "protein_g": 5.4, "fat_g": 5.0, "carbs_g": 6.1, "fiber_g": 1.6}' WHERE id = '6b79fed5-ace4-4b77-a201-7ac6571a3f25';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '6b79fed5-ace4-4b77-a201-7ac6571a3f25' AND NOT ('léger' = ANY(tags));

-- Soupe poireaux - pommes de terre
UPDATE recipes SET nutrition = '{"calories": 1265, "protein_g": 29.3, "fat_g": 12.4, "carbs_g": 253.6, "fiber_g": 14.7}' WHERE id = 'c0558207-e4ee-4532-b5f1-e4809328fa7b';

-- Soupe tomate rapide
UPDATE recipes SET nutrition = '{"calories": 217, "protein_g": 7.6, "fat_g": 2.1, "carbs_g": 40.3, "fiber_g": 8.4}' WHERE id = 'f5ee89d3-56bd-47e6-80fb-baf27be08e02';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'f5ee89d3-56bd-47e6-80fb-baf27be08e02' AND NOT ('léger' = ANY(tags));

-- Soupe veloutée de potimarron et pommes de terre
UPDATE recipes SET nutrition = '{"calories": 173, "protein_g": 5.6, "fat_g": 3.7, "carbs_g": 28.5, "fiber_g": 3.7}' WHERE id = '14d74ffb-dcdc-46e5-8eea-f2f01dd1dbf6';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '14d74ffb-dcdc-46e5-8eea-f2f01dd1dbf6' AND NOT ('léger' = ANY(tags));

-- Soupe à l''oignon
UPDATE recipes SET nutrition = '{"calories": 1189, "protein_g": 30.8, "fat_g": 14.8, "carbs_g": 228.0, "fiber_g": 14.0}' WHERE id = '2637aae8-e5d7-4998-a4d2-a6ace835a163';

-- Spaghetti alle vongole (pâtes aux palourdes)
UPDATE recipes SET nutrition = '{"calories": 982, "protein_g": 114.1, "fat_g": 23.8, "carbs_g": 76.2, "fiber_g": 4.2}' WHERE id = '06bf1501-f44f-4630-84b4-df60a1787a25';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '06bf1501-f44f-4630-84b4-df60a1787a25' AND NOT ('protéiné' = ANY(tags));

-- Spaghetti bolognaise
UPDATE recipes SET nutrition = '{"calories": 1075, "protein_g": 51.1, "fat_g": 19.9, "carbs_g": 167.7, "fiber_g": 10.8}' WHERE id = 'e5f57449-12ba-43e5-8947-46c92306c943';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'e5f57449-12ba-43e5-8947-46c92306c943' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'e5f57449-12ba-43e5-8947-46c92306c943' AND NOT ('gourmand' = ANY(tags));

-- Sushi californien (maki inversé)
UPDATE recipes SET nutrition = '{"calories": 350, "protein_g": 28.1, "fat_g": 6.4, "carbs_g": 43.5, "fiber_g": 4.2}' WHERE id = '0b438923-a3e7-446b-94b6-a14c51a443ab';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '0b438923-a3e7-446b-94b6-a14c51a443ab' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '0b438923-a3e7-446b-94b6-a14c51a443ab' AND NOT ('léger' = ANY(tags));

-- Tacos mexicains
UPDATE recipes SET nutrition = '{"calories": 778, "protein_g": 32.1, "fat_g": 12.7, "carbs_g": 130.2, "fiber_g": 9.7}' WHERE id = '3326ef8b-5ae0-4ce2-865c-ad062eb6e3a8';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '3326ef8b-5ae0-4ce2-865c-ad062eb6e3a8' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '3326ef8b-5ae0-4ce2-865c-ad062eb6e3a8' AND NOT ('gourmand' = ANY(tags));

-- Tagliatelles au saumon fumé à l''italienne
UPDATE recipes SET nutrition = '{"calories": 569, "protein_g": 33.5, "fat_g": 16.7, "carbs_g": 69.4, "fiber_g": 4.0}' WHERE id = '634d6b68-2aec-4294-aec4-cee49f9f04ef';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '634d6b68-2aec-4294-aec4-cee49f9f04ef' AND NOT ('protéiné' = ANY(tags));

-- Tartare de thon de Mohamed Cheikh
UPDATE recipes SET nutrition = '{"calories": 231, "protein_g": 29.1, "fat_g": 5.9, "carbs_g": 14.5, "fiber_g": 3.6}' WHERE id = 'f6514a14-b1d7-44f2-96d8-740532ee4b3f';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'f6514a14-b1d7-44f2-96d8-740532ee4b3f' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'f6514a14-b1d7-44f2-96d8-740532ee4b3f' AND NOT ('léger' = ANY(tags));

-- Tarte amandine aux poires
UPDATE recipes SET nutrition = '{"calories": 256, "protein_g": 7.4, "fat_g": 5.2, "carbs_g": 44.0, "fiber_g": 3.3}' WHERE id = '49d47ec5-b3cb-4217-a3a5-e58a16e9ebb0';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '49d47ec5-b3cb-4217-a3a5-e58a16e9ebb0' AND NOT ('léger' = ANY(tags));

-- Tarte au citron meringuée
UPDATE recipes SET nutrition = '{"calories": 389, "protein_g": 15.3, "fat_g": 11.0, "carbs_g": 55.8, "fiber_g": 3.8}' WHERE id = '0364e7aa-7c09-4753-8e20-690c44cc48a3';

-- Tarte aux poireaux et aux lardons
UPDATE recipes SET nutrition = '{"calories": 441, "protein_g": 28.7, "fat_g": 17.6, "carbs_g": 40.3, "fiber_g": 2.7}' WHERE id = '58dd788a-d61c-4288-80a3-85c8971f1208';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '58dd788a-d61c-4288-80a3-85c8971f1208' AND NOT ('protéiné' = ANY(tags));

-- Tarte aux pommes
UPDATE recipes SET nutrition = '{"calories": 133, "protein_g": 2.7, "fat_g": 1.3, "carbs_g": 26.9, "fiber_g": 2.9}' WHERE id = '1b2bbd67-5ac8-4c24-890a-2a1d2186caf0';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '1b2bbd67-5ac8-4c24-890a-2a1d2186caf0' AND NOT ('léger' = ANY(tags));

-- Tarte aux pommes
UPDATE recipes SET nutrition = '{"calories": 133, "protein_g": 2.7, "fat_g": 1.4, "carbs_g": 26.8, "fiber_g": 3.2}' WHERE id = '0c50a124-b31e-4c07-81ae-537eb1cc3bc1';

-- Tarte aux pommes sans pâte et rapide
UPDATE recipes SET nutrition = '{"calories": 167, "protein_g": 5.7, "fat_g": 4.7, "carbs_g": 24.8, "fiber_g": 1.8}' WHERE id = 'e09d7492-5420-4e60-b99a-b6654d6ce6fe';

-- Tarte thon, tomate et moutarde
UPDATE recipes SET nutrition = '{"calories": 463, "protein_g": 52.3, "fat_g": 17.5, "carbs_g": 23.2, "fiber_g": 2.3}' WHERE id = '5c619ed4-da63-457f-a727-f74f31367601';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '5c619ed4-da63-457f-a727-f74f31367601' AND NOT ('protéiné' = ANY(tags));

-- Tarte à l''oignon rapide
UPDATE recipes SET nutrition = '{"calories": 188, "protein_g": 8.8, "fat_g": 6.8, "carbs_g": 22.1, "fiber_g": 3.6}' WHERE id = 'e7dd3cb4-b622-4539-a520-6b08f55ee553';

-- Tarte à la banane
UPDATE recipes SET nutrition = '{"calories": 287, "protein_g": 8.6, "fat_g": 6.7, "carbs_g": 46.9, "fiber_g": 3.8}' WHERE id = '1e3b1370-9a9b-4e0d-aa69-4d07779f4264';

-- Tartelette au citron maison
UPDATE recipes SET nutrition = '{"calories": 298, "protein_g": 17.0, "fat_g": 7.7, "carbs_g": 39.2, "fiber_g": 3.6}' WHERE id = 'cfc4fa20-d4f9-4174-88aa-3de48cd62efe';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'cfc4fa20-d4f9-4174-88aa-3de48cd62efe' AND NOT ('léger' = ANY(tags));

-- Tartiflette : la vraie recette
UPDATE recipes SET nutrition = '{"calories": 285, "protein_g": 16.5, "fat_g": 7.0, "carbs_g": 37.7, "fiber_g": 6.3}' WHERE id = '9e090d80-88f1-4d2d-9fc0-4b321f03d30e';

-- Tartiflette au reblochon rapide et facile
UPDATE recipes SET nutrition = '{"calories": 302, "protein_g": 17.4, "fat_g": 7.7, "carbs_g": 39.1, "fiber_g": 6.7}' WHERE id = 'f29d1d77-03f9-4636-9d5b-6c371f1761ee';

-- Tartiflette facile et rapide au Cookeo
UPDATE recipes SET nutrition = '{"calories": 361, "protein_g": 21.9, "fat_g": 10.6, "carbs_g": 42.7, "fiber_g": 6.8}' WHERE id = 'd273014f-1dc2-4196-8dae-b8fafa8954b1';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'd273014f-1dc2-4196-8dae-b8fafa8954b1' AND NOT ('protéiné' = ANY(tags));

-- Tartines Alsacienne
UPDATE recipes SET nutrition = '{"calories": 106, "protein_g": 6.6, "fat_g": 3.5, "carbs_g": 11.6, "fiber_g": 1.2}' WHERE id = 'df76567a-632f-408f-a72e-5b90d0ed81ba';

-- Tataki de thon
UPDATE recipes SET nutrition = '{"calories": 250, "protein_g": 23.2, "fat_g": 4.8, "carbs_g": 27.5, "fiber_g": 4.5}' WHERE id = '669b4bf3-7b7f-456f-aeae-8f264a8450ab';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '669b4bf3-7b7f-456f-aeae-8f264a8450ab' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '669b4bf3-7b7f-456f-aeae-8f264a8450ab' AND NOT ('léger' = ANY(tags));

-- Terrine de foie gras au Sauternes
UPDATE recipes SET nutrition = '{"calories": 77, "protein_g": 9.8, "fat_g": 3.8, "carbs_g": 0.6, "fiber_g": 0.1}' WHERE id = '171c0799-d085-45ae-91e7-3c1d6c1a2f78';

-- Tian express
UPDATE recipes SET nutrition = '{"calories": 173, "protein_g": 6.9, "fat_g": 2.9, "carbs_g": 28.7, "fiber_g": 6.0}' WHERE id = 'df940722-e29c-42f9-afcc-cef526ebbc68';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'df940722-e29c-42f9-afcc-cef526ebbc68' AND NOT ('léger' = ANY(tags));

-- Tiramisu (recette originale)
UPDATE recipes SET nutrition = '{"calories": 457, "protein_g": 17.4, "fat_g": 19.2, "carbs_g": 50.8, "fiber_g": 3.2}' WHERE id = 'ce6cb9b0-029e-4ac3-b3fb-2c07c72c2714';

-- Tiramisu chocolat speculoos très facile
UPDATE recipes SET nutrition = '{"calories": 218, "protein_g": 9.7, "fat_g": 9.5, "carbs_g": 22.6, "fiber_g": 1.0}' WHERE id = 'dac0462c-8927-4a8e-afbb-52fafb5d85b7';

-- Tofu façon porc au caramel
UPDATE recipes SET nutrition = '{"calories": 685, "protein_g": 17.4, "fat_g": 8.6, "carbs_g": 130.9, "fiber_g": 7.8}' WHERE id = '940b7e78-7750-4d6b-83d9-8f873c8d3288';

-- Tuiles au parmesan inratable
UPDATE recipes SET nutrition = '{"calories": 50, "protein_g": 2.7, "fat_g": 2.8, "carbs_g": 3.5, "fiber_g": 0.1}' WHERE id = 'b3ebf37c-868c-43cb-aeee-0895fbdc9853';

-- Velouté d''asperges vertes et blanches
UPDATE recipes SET nutrition = '{"calories": 138, "protein_g": 7.8, "fat_g": 6.2, "carbs_g": 11.9, "fiber_g": 3.8}' WHERE id = 'c24a4735-a0e8-493f-95e0-be7a88b8b37b';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'c24a4735-a0e8-493f-95e0-be7a88b8b37b' AND NOT ('léger' = ANY(tags));

-- Velouté de butternut à la cannelle
UPDATE recipes SET nutrition = '{"calories": 111, "protein_g": 3.8, "fat_g": 2.6, "carbs_g": 17.6, "fiber_g": 1.5}' WHERE id = 'cbc4aee9-2deb-420e-9923-7e0f93309fc9';

-- Velouté de chou- fleur
UPDATE recipes SET nutrition = '{"calories": 431, "protein_g": 10.9, "fat_g": 5.2, "carbs_g": 83.2, "fiber_g": 5.6}' WHERE id = 'fb8a28a7-9845-408d-95c6-b6c98265d929';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = 'fb8a28a7-9845-408d-95c6-b6c98265d929' AND NOT ('léger' = ANY(tags));

-- Velouté de courgette au St Môret
UPDATE recipes SET nutrition = '{"calories": 609, "protein_g": 15.9, "fat_g": 6.5, "carbs_g": 119.0, "fiber_g": 9.0}' WHERE id = 'f1d08ae5-9070-4450-be62-ccc373ee0702';

-- Velouté de potiron
UPDATE recipes SET nutrition = '{"calories": 117, "protein_g": 4.1, "fat_g": 2.3, "carbs_g": 19.4, "fiber_g": 2.3}' WHERE id = '5a8675fd-0bf2-498e-bb71-9fc12b606b75';
UPDATE recipes SET tags = array_cat(tags, ARRAY['léger']) WHERE id = '5a8675fd-0bf2-498e-bb71-9fc12b606b75' AND NOT ('léger' = ANY(tags));

-- Verrines express banane yaourt chocolat
UPDATE recipes SET nutrition = '{"calories": 136, "protein_g": 6.1, "fat_g": 6.6, "carbs_g": 12.6, "fiber_g": 1.5}' WHERE id = 'e72188b9-17a8-4b4a-9b7c-4d0c850b4fca';

-- Véritable moelleux au chocolat
UPDATE recipes SET nutrition = '{"calories": 294, "protein_g": 17.5, "fat_g": 8.8, "carbs_g": 35.4, "fiber_g": 1.7}' WHERE id = '5c122af2-3bc7-4e01-a501-66e0c85a86b1';

-- Véritables raviolis japonais de A à Z (Gyoza)
UPDATE recipes SET nutrition = '{"calories": 436, "protein_g": 24.5, "fat_g": 8.2, "carbs_g": 64.4, "fiber_g": 4.0}' WHERE id = '267c8c8c-092b-41ff-b023-b480a16a49f1';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '267c8c8c-092b-41ff-b023-b480a16a49f1' AND NOT ('protéiné' = ANY(tags));

-- Wrap grillé au poulet et au fromage
UPDATE recipes SET nutrition = '{"calories": 973, "protein_g": 53.5, "fat_g": 21.1, "carbs_g": 137.8, "fiber_g": 10.5}' WHERE id = '7517414b-964e-4808-800c-eda9d34ce356';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '7517414b-964e-4808-800c-eda9d34ce356' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = '7517414b-964e-4808-800c-eda9d34ce356' AND NOT ('gourmand' = ANY(tags));

-- Wraps au fromage frais, concombres et saumon fumé
UPDATE recipes SET nutrition = '{"calories": 600, "protein_g": 41.2, "fat_g": 17.0, "carbs_g": 68.8, "fiber_g": 4.5}' WHERE id = '3b118cd1-9c95-42b2-82ac-ce9c47405304';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = '3b118cd1-9c95-42b2-82ac-ce9c47405304' AND NOT ('protéiné' = ANY(tags));

-- Yaourt glacé express à la fraise
UPDATE recipes SET nutrition = '{"calories": 139, "protein_g": 5.0, "fat_g": 4.9, "carbs_g": 18.0, "fiber_g": 1.6}' WHERE id = '4ff9e146-0ac9-45b3-8c51-d265c01dd63f';

-- Yaourt à la noix de coco
UPDATE recipes SET nutrition = '{"calories": 239, "protein_g": 12.7, "fat_g": 13.5, "carbs_g": 16.1, "fiber_g": 0.5}' WHERE id = '94945f17-461e-4094-990d-0d59f3988b2e';

-- gratin de poisson sur lit de pommes de terre
UPDATE recipes SET nutrition = '{"calories": 947, "protein_g": 78.9, "fat_g": 36.3, "carbs_g": 73.3, "fiber_g": 8.2}' WHERE id = 'eb225fbe-2eea-4a96-ad81-cfe448613b52';
UPDATE recipes SET tags = array_cat(tags, ARRAY['protéiné']) WHERE id = 'eb225fbe-2eea-4a96-ad81-cfe448613b52' AND NOT ('protéiné' = ANY(tags));
UPDATE recipes SET tags = array_cat(tags, ARRAY['gourmand']) WHERE id = 'eb225fbe-2eea-4a96-ad81-cfe448613b52' AND NOT ('gourmand' = ANY(tags));

-- raviolis maison viande/chèvre
UPDATE recipes SET nutrition = '{"calories": 220, "protein_g": 8.5, "fat_g": 6.2, "carbs_g": 32.0, "fiber_g": 1.5}' WHERE id = 'ebaf1ef7-7959-439a-bcb1-31655a02e336';

-- tarte légère aux fruits de mer
UPDATE recipes SET nutrition = '{"calories": 211, "protein_g": 15.9, "fat_g": 8.5, "carbs_g": 17.1, "fiber_g": 0.8}' WHERE id = '1eee2a52-9e14-4fd8-8fb5-1619afef95b1';

-- Œufs au plat au four
UPDATE recipes SET nutrition = '{"calories": 195, "protein_g": 12.0, "fat_g": 13.5, "carbs_g": 6.0, "fiber_g": 0.0}' WHERE id = 'b3903e07-ba26-4971-8ad3-da4c12a48ea9';

COMMIT;
