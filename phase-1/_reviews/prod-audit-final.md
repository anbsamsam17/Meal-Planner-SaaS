# Audit Prod Presto -- 2026-04-12

> Audit exhaustif de l'application Presto en production.
> Frontend : https://hop-presto-saas-sa.vercel.app
> API : https://meal-planner-saas-production.up.railway.app

---

## Resultats API (curl)

| Endpoint | Code HTTP | Resultat |
|---|---|---|
| `GET /api/v1/health` | 200 | `{"status":"ok"}` |
| `GET /api/v1/ready` | 200 | DB ok, Redis ok, latences normales |
| `GET /api/v1/recipes?per_page=3` (sans filtre) | 200 | 591 recettes, fonctionne |
| `GET /api/v1/recipes?cuisine=francaise` | 200 | 25 resultats -- FONCTIONNE |
| `GET /api/v1/recipes?max_time=30` | 200 | 1 resultat -- FONCTIONNE |
| `GET /api/v1/recipes?max_difficulty=2` | 200 | 91 resultats -- FONCTIONNE |
| `GET /api/v1/recipes?diet=vegetarien` | 200 | 81 resultats -- FONCTIONNE |
| `GET /api/v1/recipes?diet=vegetarian` | 200 | 9 resultats (tag EN) -- FONCTIONNE |
| `GET /api/v1/recipes?diet=vegan` | 200 | 1 resultat -- FONCTIONNE |
| `GET /api/v1/recipes?diet=gluten-free` | 200 | **0 resultats** -- TAG ABSENT EN DB |
| `GET /api/v1/recipes?diet=halal` | 200 | **0 resultats** -- TAG ABSENT EN DB |
| `GET /api/v1/recipes?diet=no-pork` | 200 | **0 resultats** -- TAG ABSENT EN DB |
| `GET /api/v1/recipes?budget=economique` | 200 | **0 resultats** -- TAG ABSENT EN DB |
| `GET /api/v1/recipes?budget=moyen` | 200 | **0 resultats** -- TAG ABSENT EN DB |
| `GET /api/v1/recipes?budget=premium` | 200 | **0 resultats** -- TAG ABSENT EN DB |
| `GET /api/v1/recipes?difficulty=2` | 200 | **591 resultats (non filtre)** -- PARAMETRE IGNORE |
| `GET /api/v1/recipes?page=2&per_page=24` | 200 | Pagination ok |
| `GET /api/v1/recipes/{uuid}` (detail) | 200 | Fonctionne avec ingredients + instructions |
| `GET /api/v1/recipes/random` | 200 | 5 recettes aleatoires |
| `GET /api/v1/recipes/search?q=poulet` | 422 | **ROUTE CASSEE** -- interceptee par `/{recipe_id}` (UUID parsing) |

---

## Bugs identifies

### BUG-001 : Filtre difficulte ne fonctionne pas (frontend envoie le mauvais parametre)

- **Gravite** : CRITIQUE
- **Page** : `/recipes`
- **Symptome** : Cliquer sur un chip de difficulte (ex: "Facile") ne filtre rien. Les 591 recettes restent affichees.
- **Cause racine** : Le frontend envoie `difficulty=2` mais l'API attend `max_difficulty=2` (ou `min_difficulty`). Le parametre `difficulty` est inconnu de l'API et silencieusement ignore.
- **Fichiers** :
  - `apps/web/src/lib/api/endpoints.ts` (ligne 214) : `params.set("difficulty", ...)` -- mauvais nom
  - `apps/api/src/api/v1/recipes.py` (lignes 369-373) : API declare `min_difficulty` et `max_difficulty`
- **Fix** : Dans `searchRecipesAdvanced()`, remplacer `params.set("difficulty", ...)` par `params.set("max_difficulty", ...)` pour correspondre au contrat API.

---

### BUG-002 : Filtre budget retourne toujours 0 resultats (tags absents en DB)

- **Gravite** : HAUTE
- **Page** : `/recipes`
- **Symptome** : Cliquer sur "Economique", "Moyen" ou "Premium" affiche "Aucune recette ne correspond a vos filtres".
- **Cause racine** : L'API filtre via `:budget = ANY(tags)` mais aucune recette en DB n'a de tag "economique", "moyen" ou "premium". Les 591 recettes n'ont que des tags de categorie (plat, dessert, accompagnement...) et quelques tags EN (baking, stew, curry...). Le pipeline d'import des recettes (themealdb) ne genere pas de tags budget.
- **Fichiers** :
  - `apps/api/src/api/v1/recipes.py` (lignes 438-439) : le filtre SQL est correct mais les donnees n'existent pas
  - Script de seed/import des recettes (a localiser)
- **Fix** : Deux options :
  1. **Approche recommandee** : Inferer le budget depuis les ingredients (nombre, cout moyen) lors du seed et ajouter le tag "economique"/"moyen"/"premium" dans le tableau `tags`.
  2. **Approche rapide** : Desactiver le filtre budget dans le frontend jusqu'a ce que les donnees soient enrichies, pour eviter la confusion utilisateur.

---

### BUG-003 : Filtres regime alimentaire ne fonctionnent pas pour la plupart des valeurs (tags absents en DB)

- **Gravite** : HAUTE
- **Page** : `/recipes`
- **Symptome** : Les filtres "Sans gluten", "Sans lactose", "Sans porc", "Sans fruits de mer", "Halal", "Sans fruits a coque" retournent 0 resultats.
- **Cause racine** : Le frontend envoie des valeurs EN normalisees (`gluten-free`, `lactose-free`, `no-pork`, `no-seafood`, `halal`, `nut-free`) mais ces tags n'existent pas dans la DB. Seuls les tags `vegetarien` (FR, 81 resultats), `vegetarian` (EN, 9 resultats) et `vegan` (1 resultat) sont presents. Le pipeline d'import ne genere pas ces tags alimentaires.
- **Fichiers** :
  - `apps/web/src/components/recipe/recipe-filters.tsx` (lignes 20-29) : DIET_OPTIONS envoie des valeurs EN
  - DB recipes.tags : ne contient pas ces valeurs
- **Fix** : Enrichir les donnees en DB avec les tags alimentaires corrects via le script de seed. Alternativement, modifier l'API pour inferer ces tags depuis les ingredients (ex: recette sans ingredient de porc -> tag "no-pork").

---

### BUG-004 : Tags en DB contiennent des chaines vides (data quality)

- **Gravite** : MOYENNE
- **Page** : `/recipes`, `/recipes/[id]`
- **Symptome** : Les tags retournes par l'API contiennent systematiquement des chaines vides : `["plat","","","","",""]` au lieu de `["plat"]`. Cela pollue l'affichage et genere du bruit dans les filtres.
- **Cause racine** : Le pipeline d'import ecrit un tableau de taille fixe (6 elements) avec du padding par chaines vides au lieu de stocker uniquement les tags significatifs.
- **Fichiers** : Script de seed/import (a localiser), table `recipes` colonne `tags`
- **Fix** : Nettoyer les tags en DB (`UPDATE recipes SET tags = array_remove(tags, '');`) et corriger le script d'import pour ne pas inserer de chaines vides.

---

### BUG-005 : Mismatch types RecipeCard -- l'API retourne des noms de champs differents de ceux attendus par le type Recipe frontend

- **Gravite** : CRITIQUE
- **Page** : `/recipes`, `/dashboard`, `/recipes/[id]`
- **Symptome** : Les RecipeCards dans l'explorateur de recettes n'affichent PAS le temps de preparation, pas de cuisine, pas de rating, et le badge cout est toujours incorrect.
- **Cause racine** : Le type TypeScript `Recipe` (types.ts) attend des champs qui ne correspondent pas a ce que l'API retourne :

  | Frontend (type Recipe) | API retourne | Match ? |
  |---|---|---|
  | `total_time_minutes` | `total_time_min` | NON |
  | `prep_time_minutes` | `prep_time_min` | NON |
  | `cook_time_minutes` | `cook_time_min` | NON |
  | `cuisine` | `cuisine_type` | NON |
  | `dietary_tags` | `tags` | NON |
  | `difficulty: "easy"\|"medium"\|"hard"` | `difficulty: 1\|2\|3\|4\|5` (int) | NON |
  | `rating_average` | absent de RecipeOut | NON |
  | `rating_count` | absent de RecipeOut | NON |
  | `ingredients[].id` | `ingredients[].ingredient_id` | NON |
  | `ingredients[].name` | `ingredients[].canonical_name` | NON |
  | `ingredients[].note` | `ingredients[].notes` | NON |

- **Fichiers** :
  - `apps/web/src/lib/api/types.ts` : type `Recipe` (lignes 9-34)
  - `apps/api/src/api/v1/recipes.py` : `RecipeOut` (lignes 37-53)
  - `apps/web/src/components/recipe/recipe-card.tsx` : utilise `recipe.total_time_minutes`, `recipe.cuisine`, `recipe.dietary_tags`, `recipe.difficulty === "hard"`, `recipe.rating_average`, `recipe.rating_count`
- **Fix** : Aligner le type `Recipe` frontend sur les noms reels de l'API OU ajouter une couche de normalisation dans `searchRecipesAdvanced()` qui mappe les champs API vers les champs frontend. La page detail (`[id]/page.tsx`) fait deja cette normalisation manuellement (lignes 58-82), mais l'explorateur ne le fait pas.

  Champs a ajouter dans RecipeOut ou a mapper :
  - `total_time_min` -> `total_time_minutes`
  - `prep_time_min` -> `prep_time_minutes`
  - `cook_time_min` -> `cook_time_minutes`
  - `cuisine_type` -> `cuisine`
  - `tags` -> `dietary_tags`
  - `difficulty` (int 1-5) -> gerer les deux formats

---

### BUG-006 : RecipeCard getCostBadge et getDisplayTime ne fonctionnent pas (toujours null/incorrect)

- **Gravite** : HAUTE
- **Page** : `/recipes`
- **Symptome** : Le badge temps n'apparait pas sur les cards de l'explorateur. Le badge cout est toujours "euro-euro" car la condition `recipe.dietary_tags` est un tableau vide (le champ n'existe pas dans la reponse API -- c'est `tags`).
- **Cause racine** : Consequence directe de BUG-005. `getDisplayTime()` lit `recipe.total_time_minutes` qui est `undefined` (l'API retourne `total_time_min`). `getCostBadge()` lit `recipe.dietary_tags` qui est `undefined` (l'API retourne `tags`) et `recipe.difficulty === "hard"` qui est toujours false (l'API retourne un int).
- **Fichiers** : `apps/web/src/components/recipe/recipe-card.tsx` (lignes 32-51)
- **Fix** : Corrige par BUG-005. Si le type est aligne, les fonctions fonctionneront.

---

### BUG-007 : Filtre "Desserts" (quick filter) ne fonctionne pas correctement

- **Gravite** : MOYENNE
- **Page** : `/recipes`
- **Symptome** : Le quick filter "Desserts" fait une recherche textuelle `q=dessert` au lieu de filtrer par tag.
- **Cause racine** : Dans `recipes-explorer.tsx` (ligne 114), le quick filter "dessert" est mappe sur `{ q: "dessert" }` ce qui fait un `ILIKE '%dessert%'` sur le titre. Cela retourne les recettes dont le titre contient "dessert" mais pas celles qui ont le tag "dessert" sans le mot dans le titre.
- **Fichiers** : `apps/web/src/app/(app)/recipes/recipes-explorer.tsx` (ligne 114)
- **Fix** : Utiliser un filtre par tag (ex: `{ diet: "dessert" }`) ou ajouter un parametre `tag` a l'API. Alternativement, utiliser une recherche combinee titre + tags cote API.

---

### BUG-008 : Filtre "Vegetarien" (quick filter) envoie "vegetarian" (EN) mais la DB a surtout "vegetarien" (FR)

- **Gravite** : HAUTE
- **Page** : `/recipes`
- **Symptome** : Le quick filter "Vegetarien" retourne 9 resultats au lieu de 81, car il filtre sur le tag EN "vegetarian" alors que 81 recettes ont le tag FR "vegetarien".
- **Cause racine** : Dans `recipes-explorer.tsx` (ligne 115), le quick filter utilise `{ diet: "vegetarian" }` (EN). La DB contient principalement des tags FR ("vegetarien" = 81 recettes) et quelques tags EN residuels ("vegetarian" = 9 recettes).
- **Fichiers** :
  - `apps/web/src/app/(app)/recipes/recipes-explorer.tsx` (ligne 115)
  - `apps/web/src/components/recipe/recipe-filters.tsx` (ligne 21) : DIET_OPTIONS utilise aussi "vegetarian" (EN)
- **Fix** : Harmoniser les tags en DB pour utiliser une seule langue (FR recommande pour une app FR), puis aligner le frontend. Alternative : faire le filtre API avec `tags && ARRAY['vegetarien', 'vegetarian']` pour les deux langues.

---

### BUG-009 : Route `/api/v1/recipes/search` cassee (conflit de routing FastAPI)

- **Gravite** : BASSE (l'ancien endpoint `searchRecipes()` n'est plus utilise par le frontend)
- **Page** : Aucune page frontend affectee directement
- **Symptome** : `GET /api/v1/recipes/search?q=poulet` retourne une erreur 422 "Input should be a valid UUID".
- **Cause racine** : La route `/{recipe_id}` (UUID path parameter) est declaree avant `/search` dans le router FastAPI, donc `/search` est intercepte comme un `recipe_id` invalide.
- **Fichiers** : `apps/api/src/api/v1/recipes.py` -- ordre des routes
- **Fix** : Deplacer la route `/random` et eventuellement ajouter `/search` AVANT la route `/{recipe_id}` dans le router. Alternativement, si `/search` n'est plus utilise, le documenter comme deprecie.

---

### BUG-010 : Page recette detail -- temps non affiche (mismatch champs)

- **Gravite** : HAUTE
- **Page** : `/recipes/[id]`
- **Symptome** : Sur la page de detail d'une recette, le temps n'est pas affiche dans le hero overlay.
- **Cause racine** : La page (`[id]/page.tsx` ligne 188) lit `recipe.total_time_minutes` mais l'API retourne `total_time_min`. La normalisation dans `fetchRecipe()` (lignes 58-82) ne mappe pas les champs de temps.
- **Fichiers** :
  - `apps/web/src/app/(app)/recipes/[id]/page.tsx` (lignes 188, 44-47)
- **Fix** : Ajouter dans `fetchRecipe()` la normalisation des champs de temps :
  ```js
  data.total_time_minutes = data.total_time_min ?? null;
  data.prep_time_minutes = data.prep_time_min ?? null;
  data.cook_time_minutes = data.cook_time_min ?? null;
  data.cuisine = data.cuisine_type ?? null;
  ```

---

### BUG-011 : Page recette detail -- cuisine non affichee (mismatch champ)

- **Gravite** : MOYENNE
- **Page** : `/recipes/[id]`
- **Symptome** : Le label de cuisine (ex: "francaise") n'apparait pas dans le hero overlay.
- **Cause racine** : La page lit `recipe.cuisine` (ligne 183) mais l'API retourne `cuisine_type`.
- **Fichiers** : `apps/web/src/app/(app)/recipes/[id]/page.tsx` (ligne 183)
- **Fix** : Ajouter `data.cuisine = data.cuisine_type ?? null;` dans la normalisation `fetchRecipe()`.

---

### BUG-012 : PaginatedResponse type mismatch -- le frontend attend `data` mais l'API retourne `results`

- **Gravite** : BASSE (contourne par le code)
- **Page** : `/recipes`
- **Symptome** : Pas de crash grace a la double lecture `(data as any)?.results ?? (data as any)?.data` dans recipes-explorer.tsx (ligne 129), mais le type TypeScript `PaginatedResponse<T>` declare `data: T[]` (types.ts ligne 152) alors que l'API retourne `results`.
- **Cause racine** : Le schema `RecipeSearchResult` (recipes.py ligne 87) retourne `results` comme cle, pas `data`.
- **Fichiers** :
  - `apps/web/src/lib/api/types.ts` (ligne 152) : `data: T[]`
  - `apps/api/src/api/v1/recipes.py` (ligne 90) : `results: list[RecipeOut]`
- **Fix** : Aligner le type frontend sur `results: T[]` ou ajouter `has_next` dans la reponse API pour correspondre au type PaginatedResponse.

---

### BUG-013 : cook_time_min suspicieusement eleve (80 min) pour toutes les recettes

- **Gravite** : MOYENNE
- **Page** : Toutes les pages affichant des recettes
- **Symptome** : Quasiment toutes les recettes ont `cook_time_min: 80`, ce qui semble etre une valeur par defaut erronee du pipeline d'import plutot qu'un vrai temps de cuisson.
- **Cause racine** : Le script d'import TheMealDB met probablement une valeur par defaut de 80 quand le temps de cuisson n'est pas fourni par l'API source (TheMealDB ne fournit pas de temps de cuisson structuree).
- **Fichiers** : Script de seed/import
- **Fix** : Utiliser `null` comme valeur par defaut quand le temps de cuisson est inconnu, au lieu d'une valeur arbitraire. Alternativement, inferer un temps raisonnable depuis la categorie de recette.

---

### BUG-014 : Filtre temps max retourne trop peu de resultats a cause de cook_time_min=80

- **Gravite** : HAUTE
- **Page** : `/recipes`
- **Symptome** : Le slider "Temps max" a 30 min ne retourne qu'1 seule recette (sur 591), car `total_time_min` = `prep_time_min + 80` pour la quasi-totalite des recettes.
- **Cause racine** : Consequence directe de BUG-013. Le `total_time_min` est gonfle artificiellement par le `cook_time_min=80` faux.
- **Fichiers** : Script de seed/import
- **Fix** : Corriger BUG-013 reglera automatiquement ce probleme.

---

### BUG-015 : Explorateur de recettes -- cuisine non affichee sous le titre des cards

- **Gravite** : MOYENNE
- **Page** : `/recipes`
- **Symptome** : Le label cuisine (ex: "TURQUE", "CHINOISE") n'apparait pas sous l'image de la card.
- **Cause racine** : RecipeCard (ligne 126) lit `recipe.cuisine` mais l'API retourne `cuisine_type`. Consequence de BUG-005.
- **Fichiers** : `apps/web/src/components/recipe/recipe-card.tsx` (ligne 126)
- **Fix** : Corrige par BUG-005 (normalisation ou alignement des types).

---

## Inventaire des tags en DB (591 recettes)

Tags presents dans la base de donnees (par frequence) :

| Tag | Nombre de recettes |
|---|---|
| plat | ~200+ |
| dessert | ~80+ |
| accompagnement | ~50+ |
| vegetarien | ~80+ |
| poisson | ~30+ |
| petit-dejeuner | ~10+ |
| entree | ~5+ |
| pates | ~5+ |
| baking, stew, meat, soup, curry, pie... | < 10 chacun |
| vegetarian (EN) | 9 |
| vegan | 1 |

Tags ABSENTS (que le frontend essaie d'utiliser) :
- economique, moyen, premium (budget)
- gluten-free, lactose-free, no-pork, no-seafood, halal, nut-free (regime)

---

## Pages fonctionnelles

| Page | Statut | Notes |
|---|---|---|
| `/login` | OK | Auth email/password + magic link + forgot password |
| `/signup` | OK | Inscription email/password + magic link |
| `/dashboard` | OK (partiel) | Structure OK, mais recettes dans PlanWeekGrid souffrent du mismatch types (BUG-005) |
| `/recipes` | BUGGY | Explorateur fonctionne mais filtres casses (BUG-001 a 008) et cards sans temps/cuisine/rating (BUG-005/006) |
| `/recipes/[id]` | BUGGY | Contenu affiche mais temps + cuisine manquants (BUG-010/011). Ingredients et instructions OK grace a la normalisation manuelle dans fetchRecipe |
| `/settings` | OK | Page de parametres creee |
| `/account` | OK | Page compte creee |
| `/billing` | OK | Page abonnement creee |
| `/fridge` | OK | Mode frigo fonctionnel (necessite auth) |
| `/shopping-list` | OK | Liste de courses fonctionnelle (necessite un plan actif) |
| `/books` | OK | Page livres PDF |

---

## Plan de correction (ordre de priorite)

### Priorite 1 -- CRITIQUE (a corriger immediatement)

1. **BUG-005** : Aligner les types frontend `Recipe` sur les noms reels de l'API OU creer une couche de normalisation dans `searchRecipesAdvanced()`.
   - Fichiers : `apps/web/src/lib/api/types.ts`, `apps/web/src/lib/api/endpoints.ts`
   - Cela corrige aussi BUG-006, BUG-010, BUG-011, BUG-015

2. **BUG-001** : Changer `difficulty` -> `max_difficulty` dans `searchRecipesAdvanced()`.
   - Fichier : `apps/web/src/lib/api/endpoints.ts` (ligne 214)

### Priorite 2 -- HAUTE (a corriger cette semaine)

3. **BUG-008** : Harmoniser les tags FR/EN dans la DB et aligner le frontend.
   - Fichier : SQL migration + `apps/web/src/components/recipe/recipe-filters.tsx`
   - SQL : `UPDATE recipes SET tags = array_replace(tags, 'vegetarian', 'vegetarien') WHERE 'vegetarian' = ANY(tags);`

4. **BUG-013/014** : Corriger le pipeline d'import pour ne pas mettre cook_time_min=80 par defaut.
   - Fichier : Script de seed/import TheMealDB
   - SQL immediate : `UPDATE recipes SET cook_time_min = NULL, total_time_min = prep_time_min WHERE cook_time_min = 80;`

5. **BUG-002/003** : Enrichir les tags en DB (budget, regimes alimentaires) via le script de seed.
   - Alternative rapide : masquer les filtres budget et regimes non-disponibles dans le frontend.

### Priorite 3 -- MOYENNE (a corriger cette semaine)

6. **BUG-004** : Nettoyer les tags vides en DB.
   - SQL : `UPDATE recipes SET tags = array_remove(tags, '');`

7. **BUG-007** : Corriger le quick filter "Desserts" pour filtrer par tag au lieu de recherche textuelle.
   - Fichier : `apps/web/src/app/(app)/recipes/recipes-explorer.tsx`

8. **BUG-012** : Aligner le type `PaginatedResponse` sur le format reel de l'API (`results` au lieu de `data`).
   - Fichier : `apps/web/src/lib/api/types.ts`

### Priorite 4 -- BASSE (backlog)

9. **BUG-009** : Corriger l'ordre des routes FastAPI (si `/search` doit etre reutilise).
   - Fichier : `apps/api/src/api/v1/recipes.py`

---

## Synthese

| Categorie | Nombre de bugs |
|---|---|
| Mismatch noms de champs frontend/API | 6 (BUG-005, 006, 010, 011, 012, 015) |
| Filtres casses (mauvais parametre API) | 2 (BUG-001, 008) |
| Donnees manquantes en DB (tags) | 3 (BUG-002, 003, 004) |
| Qualite des donnees (valeurs par defaut) | 2 (BUG-013, 014) |
| Logique filtre incorrecte | 1 (BUG-007) |
| Routing API | 1 (BUG-009) |
| **Total** | **15 bugs** |

Le bug racine le plus impactant est **BUG-005** (mismatch des noms de champs) car il affecte toutes les pages qui affichent des recettes. Le corriger resout automatiquement 5 autres bugs.
