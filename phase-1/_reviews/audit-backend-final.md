# Audit Backend + DB Presto -- Exhaustif

> Date : 2026-04-13
> Cible : API FastAPI sur Railway + DB Supabase PostgreSQL
> URL API : https://meal-planner-saas-production.up.railway.app
> DB : postgresql+asyncpg://...@aws-0-eu-west-1.pooler.supabase.com:5432/postgres

---

## 1. Resultats API (chaque endpoint)

| Endpoint | Method | HTTP Code | Resultat | Bug ? |
|----------|--------|-----------|----------|-------|
| `/api/v1/health` | GET | 200 | `{"status":"ok"}` | Non |
| `/api/v1/ready` | GET | 200 | DB OK (221ms), Redis OK (801ms), model OK | Non -- mais latence Redis elevee (801ms) |
| `/api/v1/recipes?per_page=3` | GET | 200 | 3 recettes, total=591 | Non |
| `/api/v1/recipes?cuisine=francaise&per_page=3` | GET | 200 | 3 recettes, total=25 | Non |
| `/api/v1/recipes?budget=economique&per_page=3` | GET | 200 | 3 recettes, total=91 | Non |
| `/api/v1/recipes?diet=vegetarien&per_page=3` | GET | 200 | 3 recettes, total=81 | Non |
| `/api/v1/recipes?max_difficulty=2&per_page=3` | GET | 200 | 3 recettes, total=91 | Non |
| `/api/v1/recipes?max_time=30&per_page=3` | GET | 200 | 1 recette, total=1 | **ALERTE** : seulement 1 recette <= 30min sur 591 |
| `/api/v1/recipes?page=2&per_page=24` | GET | 200 | 24 recettes, total=591 | Non |
| `/api/v1/recipes/random` | GET | 200 | 5 recettes aleatoires | Non |
| `/api/v1/recipes/{id_existant}` | GET | 200 | Detail complet avec ingredients et instructions | **BUG DONNEES** (voir ci-dessous) |
| `/api/v1/recipes/{id_inexistant}` | GET | 404 | Message clair | Non |
| `/api/v1/recipes/invalid-uuid` | GET | 422 | Validation Pydantic | Non |
| `/api/v1/recipes?q=chicken&per_page=3` | GET | 200 | 3 resultats, total=54 | Non |
| `/api/v1/recipes?season=hiver&per_page=3` | GET | 200 | 0 resultats | **ATTENDU** : aucune recette taguee "hiver" |
| `POST /api/v1/plans/generate` (dummy token) | POST | 401 | "Token JWT invalide." | Non -- auth correcte |
| `GET /api/v1/plans/me/current` (dummy token) | GET | 401 | "Token JWT invalide." | Non -- auth correcte |
| `POST /api/v1/households` (dummy token) | POST | 401 | "Token JWT invalide." | Non -- auth correcte |
| `GET /api/v1/households/me` (dummy token) | GET | 401 | "Token JWT invalide." | Non -- auth correcte |
| `GET /api/v1/fridge` (dummy token) | GET | 401 | "Token JWT invalide." | Non -- auth correcte |
| `GET /api/v1/fridge` (sans auth) | GET | 401 | "Header Authorization manquant..." | Non -- auth correcte |
| `GET /api/v1/billing/status` (dummy token) | GET | 401 | "Token JWT invalide." | Non -- auth correcte |
| `GET /api/v1/billing/status` (sans auth) | GET | 401 | "Header Authorization manquant..." | Non -- auth correcte |
| `GET /docs` | GET | 200 | Swagger UI disponible | Non |

### Synthese API

- **Endpoints publics (recettes)** : tous fonctionnels, filtres operationnels
- **Endpoints authentifies** : rejet correct des tokens invalides (401)
- **Aucun endpoint ne retourne 500** : robustesse confirmee

---

## 2. Etat de la base de donnees

| Table | Rows | Probleme |
|-------|------|----------|
| `recipes` | 591 | Titres EN, instructions EN, descriptions auto-generees |
| `ingredients` | 833 | Noms EN (anglais) : "cabbage", "soy sauce", etc. |
| `recipe_ingredients` | 591 recettes liees | **BUG CRITIQUE** : quantity=1.0 pour TOUT, unit contient la vraie quantite texte |
| `recipe_embeddings` | **0** | **BLOQUANT** : table vide, le planner pgvector ne peut PAS fonctionner |
| `member_taste_vectors` | 0 | Attendu (aucun feedback utilisateur) |
| `households` | 0 | Attendu (aucun utilisateur inscrit) |
| `household_members` | 0 | Attendu |
| `member_preferences` | 0 | Attendu |
| `weekly_plans` | 0 | Attendu |
| `planned_meals` | 0 | Attendu |
| `shopping_lists` | 0 | Attendu |
| `fridge_items` | 0 | Attendu |
| `subscriptions` | 0 | Attendu |
| `engagement_events` | 0 | Attendu |
| `weekly_books` | 0 | Attendu |
| `recipe_feedbacks` | 0 | Attendu |

### Tables existantes (16 tables publiques)

`engagement_events`, `fridge_items`, `household_members`, `households`, `ingredients`, `member_preferences`, `member_taste_vectors`, `planned_meals`, `recipe_embeddings`, `recipe_feedbacks`, `recipe_ingredients`, `recipes`, `shopping_lists`, `subscriptions`, `weekly_books`, `weekly_plans`

### Extensions

- **pgvector** : installe
- **Fonction `create_household_with_owner`** : presente (SECURITY DEFINER)

---

## 3. Problemes de donnees detailles

### BUG CRITIQUE #1 : `recipe_embeddings` est VIDE (0 lignes)

La table `recipe_embeddings` ne contient aucune donnee. Cela a un impact direct :

1. **`_retrieve_by_similarity()`** fait un `JOIN recipe_embeddings re ON re.recipe_id = r.id` -- retourne 0 lignes
2. **`_retrieve_by_quality()`** fait AUSSI un `JOIN recipe_embeddings re ON re.recipe_id = r.id` -- retourne 0 lignes
3. Seul **`_retrieve_by_quality_no_embedding()`** (le fallback ultime) fonctionne correctement (pas de JOIN)

**Impact** : Le planner fonctionne MAIS est degrade -- il ne retourne que 5 recettes max via le fallback, et sans aucun filtrage par contraintes (temps, tags exclus).

**Fix existant** : Le fallback `_retrieve_by_quality_no_embedding()` est deja code (BUG 3 FIX du 2026-04-12). Le planner ne crashe pas, mais le resultat est mediocre.

**Fix necessaire** : Lancer le pipeline RECIPE_SCOUT pour generer les embeddings des 591 recettes, OU ameliorer le fallback pour appliquer les contraintes (temps, allergies).

### BUG CRITIQUE #2 : Donnees `recipe_ingredients` corrompues

Les quantites et unites sont inversees/mal parsees depuis TheMealDB :

```
canonical_name=bread     quantity=1.000  unit=[2]           notes=[Bread]
canonical_name=egg       quantity=1.000  unit=[2]           notes=[Egg]
canonical_name=salt      quantity=1.000  unit=[0.5]         notes=[Salt]
canonical_name=lettuce   quantity=1.000  unit=[Leaves]      notes=[Lettuce]
canonical_name=lime      quantity=1.000  unit=[Grated Zest of 2]  notes=[Lime]
canonical_name=soy sauce quantity=1.000  unit=[1/4 cup]     notes=[Soy Sauce]
```

**Le probleme** : `quantity` vaut toujours `1.0` (valeur par defaut), et `unit` contient en realite la quantite texte brute de TheMealDB (ex: "2 tbsp", "1/4 cup", "650g").

**Impact** :
- La liste de courses generee par `shopping_list_builder` est fausse (toutes les qty=1)
- L'affichage des ingredients dans le detail recette est incoherent
- Le mode frigo ne peut pas comparer les quantites correctement

### BUG #3 : Tous les titres sont en anglais

Sur 591 recettes, **589/591 titres suivent un pattern anglais**. Exemples :
- "Bread omelette", "Anzac biscuits", "Apple & Blackberry Crumble"
- "Chicken Ham and Leek Pie", "General Tsos Chicken"
- "Vegan Chocolate Cake"

Les descriptions sont auto-generees avec un pattern minimal : `"Bread omelette -- recette indienne. 3 ingredients."`

**Impact** : L'application cible un public francophone, mais l'integralite du contenu est en anglais.

### BUG #4 : Instructions en anglais

Toutes les instructions sont en anglais brut de TheMealDB :
```json
[{"step": 1, "text": "Simply mix all dry ingredients with wet ingredients..."}]
```

### BUG #5 : Noms d'ingredients en anglais

Les 833 ingredients sont en anglais : "cabbage", "soy sauce", "rice vinegar", "egg roll wrappers", etc.

Exception : "fromage frais" (vient de TheMealDB tel quel).

### BUG #6 : 10 cuisine_types non traduites en francais

| cuisine_type (EN) | Traduction attendue | Recettes |
|--------------------|---------------------|----------|
| algerian | algerienne | 12 |
| australian | australienne | 13 |
| argentinian | argentine | 10 |
| norwegian | norvegienne | 17 |
| saudi arabian | saoudienne | 12 |
| slovakian | slovaque | 4 |
| syrian | syrienne | 6 |
| ukrainian | ukrainienne | 7 |
| uruguayan | uruguayenne | 9 |
| venezulan | venezuelienne | 10 |

**Total** : 100 recettes avec un `cuisine_type` non traduit (17% du catalogue).

### BUG #7 : `quality_score` uniforme

**100% des recettes ont `quality_score = 0.82`**. Ce score est identique pour toutes les 591 recettes, ce qui rend le tri par `quality_score DESC` inutile (aucune differentiation).

### BUG #8 : `difficulty` mal repartie

| Difficulty | Count | % |
|------------|-------|---|
| 1 (tres facile) | 5 | 0.8% |
| 2 (facile) | 86 | 14.6% |
| 3 (moyen) | 251 | 42.5% |
| 4 (difficile) | 249 | 42.1% |
| 5 (expert) | 0 | 0% |

Seulement 5 recettes "tres faciles" -- le filtre `max_difficulty=1` retourne quasi rien.
Seulement 1 recette avec `total_time_min <= 30` -- le filtre temps rapide est inutilisable.

### BUG #9 : Aucune recette avec tag saison

Le filtre `?season=hiver` retourne 0 resultats. Aucune recette n'a de tag saison ("printemps", "ete", "automne", "hiver"). Le filtre est code mais inutilisable.

### BUG #10 : Tags mixtes FR/EN

Les tags sont un melange de francais et anglais :
- **FR** : "economique", "vegetarien", "sans-gluten", "petit-dejeuner", "plat", "accompagnement", "poisson", "pates", "dessert", "premium", "entree"
- **EN** : "alcoholic", "baking", "bbq", "breakfast", "brunch", "cake", "calorific", "cheap", "cheesy", "chocolate", "curry", "dairy", "expensive", etc.

La majorite des tags sont en anglais (hrites de TheMealDB). Seuls les tags ajoutes par le seed script sont en francais.

---

## 4. Flow "Generer planning" -- Analyse complete

| Etape | Status | Detail |
|-------|--------|--------|
| 1. User connecte (JWT Supabase) | **OK** | Auth JWT fonctionne, rejet 401 correct |
| 2. User a un household | **KO en prod** | 0 households en base -- aucun utilisateur n'a fait l'onboarding |
| 3. `POST /plans/generate` verifie household_id | **OK** (code) | Retourne 404 si pas de household |
| 4. Envoi tache Celery `generate_plan_task` | **OK** (code) | Fallback 503 si Redis/Celery indisponible |
| 5. RecipeRetriever cherche candidates pgvector | **KO** | `recipe_embeddings` vide -- pgvector retourne 0 candidates |
| 6. Fallback `_retrieve_by_quality` | **KO** | FAIT AUSSI un JOIN sur `recipe_embeddings` -- retourne 0 |
| 7. Fallback ultime `_retrieve_by_quality_no_embedding` | **OK** | Fonctionne MAIS limite a 5 recettes, sans filtres contraintes |
| 8. Score + selection | **OK** (code) | Fonctionne avec les candidates du fallback |
| 9. Shopping list generation | **DEGRADE** | Quantities corrompues (toutes = 1.0) |
| 10. Persistance en base | **OK** (code) | UPSERT correct, batch INSERT |
| 11. Validation `week_start` doit etre lundi | **OK** | Validation stricte ISODOW=1 |

### Verdict du flow planning

Le planning **peut techniquement fonctionner** grace au triple fallback du `recipe_retriever`, mais en mode tres degrade :
1. Seulement 5 recettes candidates (au lieu de 50)
2. Aucun filtrage par contraintes (allergies, temps max, tags exclus)
3. Liste de courses avec quantites fausses (toutes = 1.0)
4. Contenu 100% en anglais

---

## 5. Analyse du code backend

### `recipes.py` -- Filtres

| Filtre | Fonctionnel ? | Detail |
|--------|---------------|--------|
| `?q=` (texte) | Oui | ILIKE sur titre |
| `?cuisine=` | Oui | Exact match sur `cuisine_type` |
| `?max_time=` | Oui | Mais 1 seule recette <= 30min |
| `?budget=` | Oui | `ANY(tags)` -- fonctionne |
| `?min_difficulty=` | Oui | Range sur colonne `difficulty` |
| `?max_difficulty=` | Oui | Range sur colonne `difficulty` |
| `?diet=` | Oui | `ANY(tags)` -- fonctionne |
| `?season=` | Oui (code) | **0 resultats** : aucune recette taguee saison |
| Pagination | Oui | `page` + `per_page` + `total_count` window function |

**Conclusion** : Le code des filtres est correct. Les problemes viennent des donnees (pas de tags saison, temps de prep gonfles, quality_score uniforme).

### `plans.py` -- Endpoint generate

- Code correct : auth JWT, household check, Celery dispatch
- Route ordering fix (BUG #4) : `/me/current` declare AVANT `/{plan_id}` -- correct
- Session unique via `Depends(get_db)` (BUG #5 fix) -- correct
- Rate limit LLM 10/h -- correct
- Fallback 503 si Celery indisponible -- correct

### `households.py` -- Creation foyer

- Idempotence (BUG #7 fix) : retourne 200 si foyer existe deja -- correct
- Appel `create_household_with_owner` SECURITY DEFINER -- correct
- La fonction SQL existe en base -- confirme

### `recipe_retriever.py` -- Fallbacks

- **`_retrieve_by_similarity`** : JOIN `recipe_embeddings` -- KO (table vide)
- **`_retrieve_by_quality`** : JOIN `recipe_embeddings` -- KO (table vide)
- **`_retrieve_by_quality_no_embedding`** : SELECT FROM `recipes` directement -- OK mais :
  - Pas de filtre par contraintes (temps max, tags exclus, allergies)
  - Limite a `k=5` seulement
  - Tri par `quality_score DESC` inutile (toutes = 0.82)

### `fridge.py` -- Mode frigo

- Code correct : CRUD items, suggest-recipes avec jointure
- Necessite un household (auth) -- 0 households en base
- Noms d'ingredients en anglais -- UX degradee pour un public FR

### `billing.py` -- Stripe

- Code correct : checkout, portal, status
- Verification `_check_stripe_configured()` -- correct
- Import conditionnel de stripe -- correct
- 0 subscriptions en base -- attendu

---

## 6. Latences observees

| Composant | Latence | Verdict |
|-----------|---------|---------|
| DB Supabase (SELECT 1) | 221 ms | Acceptable pour EU West |
| Redis | 801 ms | **ELEVEE** -- verifier config Redis Railway |
| `/api/v1/recipes?per_page=3` | ~300 ms | OK |
| `/api/v1/recipes/random` | ~400 ms | OK (TABLESAMPLE + fallback) |
| `/api/v1/recipes/{id}` | ~350 ms | OK |

---

## 7. Plan de correction backend (par priorite)

### P0 -- Bloquants fonctionnels

| # | Tache | Fichier(s) | Detail |
|---|-------|------------|--------|
| 1 | **Generer les embeddings pour les 591 recettes** | `apps/worker/src/agents/recipe_scout/` | Sans embeddings, le planner est degrade. Lancer le pipeline RECIPE_SCOUT ou creer un script batch qui genere les embeddings via sentence-transformers. |
| 2 | **Ameliorer le fallback no-embedding** | `apps/worker/src/agents/weekly_planner/recipe_retriever.py` | `_retrieve_by_quality_no_embedding()` doit appliquer les contraintes (time_max, excluded_tags, allergies) et retourner plus que 5 recettes (au moins `num_dinners + 10`). |
| 3 | **Corriger les quantites d'ingredients** | Script de migration + `recipe_ingredients` | Parser correctement le champ `unit` (qui contient la vraie quantite texte) pour extraire `quantity` numerique et `unit` normalise. Ex: "1/4 cup" -> qty=0.25, unit="cup". |

### P1 -- Qualite donnees (impact UX direct)

| # | Tache | Fichier(s) | Detail |
|---|-------|------------|--------|
| 4 | **Traduire les titres en francais** | Script de migration batch (LLM ou API) | 591 titres a traduire. Soit via un agent LLM, soit via un script batch avec DeepL/GPT. |
| 5 | **Traduire les instructions en francais** | Script de migration batch | Toutes les instructions step-by-step sont en anglais. |
| 6 | **Traduire les noms d'ingredients** | Script de migration + table `ingredients` | 833 ingredients a traduire. Ajouter une colonne `canonical_name_fr` ou remplacer `canonical_name`. |
| 7 | **Traduire les 10 cuisine_types restantes** | Script SQL UPDATE | `UPDATE recipes SET cuisine_type = 'algerienne' WHERE cuisine_type = 'algerian'` etc. |
| 8 | **Harmoniser les tags en francais** | Script SQL + mapping | Les tags EN (breakfast, cheap, cake, etc.) doivent etre traduits ou mappes vers des equivalents FR. |
| 9 | **Enrichir les descriptions** | Script LLM batch | Les descriptions actuelles sont des stubs auto-generes ("X -- recette Y. N ingredients."). |

### P2 -- Ameliorations donnees (impact filtres)

| # | Tache | Fichier(s) | Detail |
|---|-------|------------|--------|
| 10 | **Ajouter des tags saison** | Script de classification | Aucune recette n'a de tag saison. Utiliser un LLM pour classifier chaque recette par saison(s). |
| 11 | **Recalculer les quality_scores** | Script de scoring | Toutes les recettes ont 0.82 -- le scoring ne differentie rien. Implementer un vrai scoring (nombre d'ingredients, completude instructions, presence photo, diversite). |
| 12 | **Recalculer les temps de preparation** | Script + source TheMealDB | prep_time_min et cook_time_min semblent arbitraires (beaucoup de cook_time=80 min). Verifier la source ou estimer via LLM. |
| 13 | **Recalculer les difficultes** | Script de re-scoring | 0 recettes difficulty=5, seulement 5 a difficulty=1. Redistribuer sur la base du nombre d'ingredients, temps, et techniques. |

### P3 -- Performance & Ops

| # | Tache | Fichier(s) | Detail |
|---|-------|------------|--------|
| 14 | **Investiguer latence Redis 801ms** | Config Railway Redis | Redis a 800ms est anormalement lent. Verifier si Redis est dans la meme region que l'API. |
| 15 | **Ajouter un cache Redis sur les recettes** | `apps/api/src/api/v1/recipes.py` | Les recettes sont statiques -- TTL 1h pour les listes, 24h pour les details. |

---

## 8. Resume executif

### Ce qui marche

- API FastAPI stable : aucun 500, tous les endpoints repondent correctement
- Auth JWT Supabase : rejet 401 correct pour tokens invalides/absents
- Filtres recettes : tous les filtres (cuisine, budget, diet, difficulty, max_time, search) fonctionnent
- Pagination : correcte avec window function COUNT(*) OVER()
- Rate limiting : configure sur tous les endpoints
- Readiness/Liveness : operationnels
- Code backend : bien structure, bonnes pratiques (session unique, route ordering, idempotence)
- DB schema : complet, 16 tables, pgvector installe, fonction SECURITY DEFINER presente

### Ce qui ne marche pas

1. **`recipe_embeddings` VIDE** : le planner est degrade (fallback 5 recettes sans filtres)
2. **Quantites d'ingredients corrompues** : toutes = 1.0, le champ `unit` contient la vraie quantite texte
3. **Contenu 100% en anglais** : titres, instructions, ingredients, 10 cuisine_types non traduits
4. **Tags mixtes FR/EN** et absence de tags saison
5. **quality_score uniforme (0.82)** : tri par qualite inutile
6. **Temps de prep gonfles** : 1 seule recette <= 30min, beaucoup de cook_time=80min arbitraires
7. **Difficulte mal repartie** : 0 recettes expert, 5 tres faciles

### Priorite absolue

**Corriger les donnees** est plus urgent que modifier le code. Le backend est solide, mais les donnees seed de TheMealDB sont brutes et non traitees pour un produit francophone.
