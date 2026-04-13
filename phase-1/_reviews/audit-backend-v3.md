# Audit Backend v3 -- Exhaustif

**Date** : 2026-04-13
**API** : https://meal-planner-saas-production.up.railway.app
**DB** : Supabase PostgreSQL (aws-0-eu-west-1.pooler.supabase.com)
**Auth token** : JWT test user `48efe38e-bd66-484a-9386-8d4bd093f796`

---

## 1. Resultats API (chaque endpoint)

| # | Endpoint | Method | Status | Resultat (50 chars) | Bug ? |
|---|---|---|---|---|---|
| 1 | `/api/v1/health` | GET | **200** | `{"status":"ok"}` | Non |
| 2 | `/api/v1/ready` | GET | **200** | `{"status":"ready","model":true,"database":true` | Non |
| 3 | `/api/v1/recipes?per_page=3` | GET | **200** | `{"results":[{"id":"0f0fcf10-46a7-411c-9f13` | Non |
| 4 | `/api/v1/recipes/{id}` | GET | **200** | `{"id":"0f0fcf10-...","title":"Bakewell tart"` | Non |
| 5 | `/api/v1/recipes/random` | GET | **200** | `[{"id":"11c98d12-0057-45b8-a3a5-6857902adba` | Non |
| 6 | `/api/v1/recipes?cuisine=francaise` | GET | **200** | `{"results":[{"id":"a50d9ee1-...","title":"C` | Non |
| 7 | `/api/v1/recipes?budget=economique` | GET | **200** | `{"results":[{"id":"a681ec00-...","title":"C` | Non |
| 8 | `/api/v1/recipes?diet=vegetarien` | GET | **200** | `{"results":[{"id":"2b364444-...","title":"K` | Non |
| 9 | `/api/v1/recipes?max_difficulty=2` | GET | **200** | `{"results":[{"id":"a681ec00-...","title":"C` | Non |
| 10 | `/api/v1/recipes?max_time=30` | GET | **200** | `{"results":[{"id":"c78054e2-...","title":"P` | Non |
| 11 | `/api/v1/plans/generate` | POST | **422** | `week_start doit etre un lundi. Recu : 2026-04-14` | Oui (B01) |
| 11b | `/api/v1/plans/generate` (lundi) | POST | **200** | `{"task_id":"5625116f-...","status":"completed` | Non |
| 12 | `/api/v1/plans/me/current` | GET | **200** | `{"id":"d13464eb-...","household_id":"68922a0c` | Non |
| 13 | `/api/v1/plans/{plan_id}` | GET | **200** | `{"id":"d13464eb-...","household_id":"68922a0c` | Non |
| 14 | `/api/v1/plans/{plan_id}/suggestions` | GET | **200** | `[{"id":"6eaae16d-...","title":"Borsch","slug` | Non |
| 15 | `PATCH /plans/{plan_id}/meals/{meal_id}` | PATCH | **200** | `{"id":"897eb050-...","recipe_title":null,...` | Oui (B02) |
| 16 | `POST /plans/{plan_id}/validate` | POST | **409** | `{"detail":"Ce plan est deja valide."}` | Non |
| 17 | `POST /plans/{plan_id}/meals/add` | POST | **200** | `{"id":"fe54d6b1-...","recipe_title":null,...` | Oui (B03) |
| 18 | `GET /plans/me/{plan_id}/shopping-list` | GET | **200** | `[{"ingredient_id":"","canonical_name":"apple` | Oui (B04) |
| 19 | `GET /households/me` | GET | **200** | `{"id":"68922a0c-...","name":"Famille Presto"` | Non |
| 20 | `POST /households` | POST | **200** | `{"id":"68922a0c-...","name":"Famille Presto"` | Non (idempotent) |
| 21 | `GET /fridge` | GET | **200** | `[]` puis `[{"id":"b570f507-...",...}]` | Non |
| 22 | `POST /fridge` | POST | **201** | `{"id":"b570f507-...","canonical_name":"plain` | Non |
| 23 | `GET /billing/status` | GET | **500** | `{"error":"internal_server_error","message":"U` | **Oui (B05 CRITIQUE)** |
| 24 | `GET /plans/me/history` | GET | **200** | `[{"id":"d13464eb-...","status":"draft",...}]` | Non |

---

## 2. Etat DB

| Table | Rows | Probleme ? |
|---|---|---|
| `recipes` | 591 | Non |
| `ingredients` | 833 | Non |
| `recipe_ingredients` | 6021 | Non |
| `households` | 1 | Non |
| `household_members` | 1 | Non |
| `weekly_plans` | 2 | Non |
| `planned_meals` | 11 | Non |
| `shopping_lists` | 1 | Non |
| `fridge_items` | 1 | Non |
| `recipe_embeddings` | **0** | Oui -- vide, recherche semantique non operationnelle |
| `member_preferences` | 1 | Non |
| `subscriptions` | **0** | Oui -- vide + mismatch colonnes code vs schema (B05) |
| `weekly_books` | 0 | Non -- normal, aucun PDF genere |

### Schema DB vs Code : Mismatch detecte

**Table `subscriptions`** -- colonnes reelles en DB :
```
id, household_id, stripe_sub_id, plan, status, current_period_end,
created_at, updated_at, stripe_customer_id, stripe_price_id,
cancel_at_period_end, canceled_at, trial_end
```

**Code billing.py / webhooks.py** -- colonnes utilisees :
```
plan_name (INEXISTANT -- la colonne s'appelle "plan")
stripe_subscription_id (INEXISTANT -- la colonne s'appelle "stripe_sub_id")
```

---

## 3. Bugs identifies

| ID | Endpoint | Description | Gravite | Fichier | Ligne |
|---|---|---|---|---|---|
| **B05** | `GET /billing/status` | **500 en prod** -- `SELECT plan_name ... FROM subscriptions` echoue car la colonne s'appelle `plan` (pas `plan_name`). Meme probleme dans `_get_or_create_stripe_customer` qui INSERT `plan_name` et dans le webhook qui UPDATE `plan_name`. | **CRITIQUE** | `billing.py` L378-389, `webhooks.py` L67-88, L117-133, L152-163, `subscription.py` L63 | |
| **B02** | `PATCH /plans/{plan_id}/meals/{meal_id}` | Le swap retourne `recipe_title: null`, `recipe_cuisine_type: null`, `recipe_difficulty: null`, `recipe_photo_url: null`. Le RETURNING SQL ne fait pas de JOIN avec `recipes` -- les champs denormalises sont absents. | **HAUTE** | `plans.py` L726-758 | |
| **B03** | `POST /plans/{plan_id}/meals/add` | Meme probleme que B02 : le RETURNING ne joint pas `recipes` -- tous les champs `recipe_*` sont null dans la reponse. | **HAUTE** | `plans.py` L841-866 | |
| **B04** | Shopping list | Tous les 54 items ont `ingredient_id: ""` (string vide), `category: "other"`, `rayon: "Epicerie"`, `off_id: null`, `in_fridge: false`. La generation ne mappe pas les `ingredient_id` reels et toutes les categories sont "other". | **HAUTE** | `plans.py` L1052-1065 | |
| **B06** | `PATCH /plans/{plan_id}/meals/{meal_id}` | Le swap sur un plan `validated` le revert silencieusement en `draft` (L719-724) sans avertir l'utilisateur. Le validate a genere une shopping list, le revert l'invalide implicitement. | **MOYENNE** | `plans.py` L719-724 | |
| **B07** | `POST /plans/{plan_id}/meals/add` | Meme revert silencieux validated->draft (L823-827). L'utilisateur perd son plan valide sans en etre informe. | **MOYENNE** | `plans.py` L823-827 | |
| **B08** | `GET /api/v1/recipes` | La reponse ne contient pas `has_next` ni `has_prev`. Le schema `RecipeSearchResult` dans `recipes.py` (L87-94) ne les declare pas, alors que `schemas/recipe.py` et `schemas/common.py` les declarent. Le endpoint utilise son propre schema local incomplet. | **MOYENNE** | `recipes.py` L87-94, L513-515 | |
| **B09** | `verify_jwt` | **Methode 4 (L131-140) : fallback sans verification de signature.** Si les 3 methodes de verification echouent, le code decode le JWT avec `verify_signature=False` et accepte le token. Un attaquant peut forger un JWT arbitraire. | **CRITIQUE** | `security.py` L131-140 | |
| **B10** | Webhook Stripe | Les INSERT/UPDATE utilisent `plan_name` et `stripe_subscription_id` au lieu de `plan` et `stripe_sub_id`. Tous les webhooks Stripe echoueront en DB. | **CRITIQUE** | `webhooks.py` L67-88, L117-133, L152-163 | |
| **B11** | `_get_or_create_stripe_customer` | INSERT dans `subscriptions` utilise `plan_name` au lieu de `plan`. Echouera en DB si un checkout Stripe est effectue. | **HAUTE** | `billing.py` L129-140 | |
| **B12** | `require_plan` | Lit `household_id` depuis `request.state.household_id` qui est le claim JWT (peut etre None si pas d'onboarding). Si None, retourne 401 au lieu de verifier en DB. Les utilisateurs sans `household_id` dans leur JWT token (onboarding recent) ne peuvent pas acceder aux features premium meme avec un abonnement actif. | **BASSE** | `subscription.py` L113-119 | |
| **B13** | `recipe_embeddings` | Table vide (0 lignes). La recherche semantique pgvector est non operationnelle. Les embeddings n'ont jamais ete generes apres le seed des 591 recettes. | **MOYENNE** | DB | |
| **B14** | Shopping list `off_id` | Le champ `off_id` (Open Food Facts) est toujours `null`. Ni la generation ni le schema ne peuplent ce champ depuis la table `ingredients`. | **BASSE** | `plans.py` L1024-1065 | |
| **B15** | Shopping list `in_fridge` | Toujours `false`. La generation ne cross-reference pas les `fridge_items` pour marquer les ingredients deja en stock. | **BASSE** | `plans.py` L1052-1065 | |

---

## 4. Analyse detaillee des bugs critiques

### B05 + B10 + B11 : Mismatch colonnes subscriptions (CRITIQUE)

**Cause racine** : Le schema SQL de la table `subscriptions` utilise `plan` et `stripe_sub_id`, mais tout le code Python (billing.py, webhooks.py, subscription.py) utilise `plan_name` et `stripe_subscription_id`.

**Colonnes DB reelles** :
- `plan` (text, CHECK IN ('starter', 'famille', 'coach'))
- `stripe_sub_id` (text, UNIQUE)

**Colonnes utilisees dans le code** :
- `plan_name` -- billing.py L378, webhooks.py L70/120/156, subscription.py L63
- `stripe_subscription_id` -- webhooks.py L71/125/158

**Impact** :
- `GET /billing/status` retourne 500 systematiquement
- Tout webhook Stripe echouera (checkout.session.completed, subscription.updated/deleted, invoice.payment_failed)
- Le checkout Stripe ne pourra pas persister l'abonnement

**Fix** : Renommer dans le code SQL toutes les references :
- `plan_name` -> `plan`
- `stripe_subscription_id` -> `stripe_sub_id`

### B09 : JWT sans verification de signature (CRITIQUE)

**Cause racine** : `security.py` L131-140 contient un fallback qui decode le JWT avec `verify_signature=False`. Si les 3 methodes de verification echouent (secret inconnu, base64 invalide, anon key invalide), le token est accepte sans aucune verification.

```python
# Methode 4 : sans verification de signature (fallback temporaire)
payload = jwt.decode(token, "dummy", algorithms=["HS256"],
    options={"verify_signature": False, "verify_aud": False})
```

Un attaquant peut forger un JWT avec n'importe quel `sub` (user_id) et acceder aux donnees de n'importe quel foyer.

**Impact** : Faille de securite critique. Bypass total de l'authentification.

**Fix** : Supprimer la methode 4 (L131-140). Si les 3 methodes echouent, le code doit retourner 401.

---

## 5. Autres observations

### Qualite du code

**Points positifs** :
- Rate limiting multi-niveau bien implemente (5 niveaux, fail-open)
- Isolation tenant correcte (household_id verifie sur tous les endpoints)
- Idempotence POST /households (pas de doublon)
- UPSERT ON CONFLICT pour planned_meals et shopping_lists
- Logging structure avec loguru (correlation_id)
- Readiness check complet (DB + Redis + modele ML)

**Points d'amelioration** :
- Le `recipes.py` definit ses propres schemas Pydantic au lieu d'utiliser ceux de `schemas/recipe.py` (duplication)
- La generation de plan est synchrone (pas Celery) -- acceptable en v1 mais limitant pour les gros calculs
- `_generate_shopping_list` ne resout pas les ingredient_id (toujours "")
- Pas de tests automatises trouves dans le repertoire `apps/api/`

### Performance DB

- `db_latency_ms: 288.8` -- latence elevee depuis Railway vers Supabase EU (acceptable mais a surveiller)
- `redis_latency_ms: 160.49` -- Redis sur Railway interne, latence correcte
- Pas d'index GIN explicite vu sur les tags arrays (implicitement cree par Supabase ?)
- `ORDER BY RANDOM()` pour la generation de plan et les suggestions -- O(n) full scan, acceptable avec 591 recettes mais problematique a l'echelle

---

## 6. Plan de correction

### Priorite 1 -- Critiques (deployer immediatement)

1. **B09 -- Supprimer le fallback JWT sans verification** (`security.py` L131-140)
   - Supprimer la methode 4 (`verify_signature=False`)
   - Si les 3 methodes echouent, lever HTTPException 401
   - Configurer correctement `SUPABASE_JWT_SECRET` dans les variables Railway

2. **B05/B10/B11 -- Corriger le mismatch colonnes subscriptions**
   - `billing.py` : remplacer `plan_name` par `plan`, `stripe_subscription_id` par `stripe_sub_id`
   - `webhooks.py` : memes remplacement dans les 4 handlers
   - `subscription.py` : remplacer `plan_name` par `plan` dans le SELECT L63

### Priorite 2 -- Haute (corriger cette semaine)

3. **B02/B03 -- Enrichir les reponses swap/add meal avec les donnees recette**
   - Apres le RETURNING, faire un SELECT JOIN recipes pour peupler `recipe_title`, `recipe_cuisine_type`, etc.
   - Ou retourner le plan complet via `_get_plan_detail()`

4. **B04/B14/B15 -- Ameliorer la generation de shopping list**
   - Mapper les vrais `ingredient_id` depuis la jointure `ingredients.id`
   - Remplir `category` depuis `ingredients.category` au lieu de hardcoder "other"
   - Cross-reference `fridge_items` pour marquer `in_fridge: true`
   - Peupler `off_id` depuis `ingredients.off_id`

### Priorite 3 -- Moyenne (corriger pour la prochaine release)

5. **B06/B07 -- Avertir l'utilisateur avant le revert validated->draft**
   - Retourner 409 si le plan est valide au lieu de le reverter silencieusement
   - Ou ajouter un header `X-Plan-Reverted: true` dans la reponse

6. **B08 -- Harmoniser RecipeSearchResult avec le schema partage**
   - Utiliser `PaginatedResponse[RecipeOut]` de `schemas/common.py`
   - Ou ajouter `has_next` et `has_prev` dans le schema local

7. **B13 -- Generer les embeddings recettes**
   - Lancer le script de generation des embeddings pour les 591 recettes
   - Planifier un cron pour les nouvelles recettes

### Priorite 4 -- Basse (Phase 2)

8. **B12 -- require_plan fallback DB pour household_id**
9. **Suppression des schemas dupliques dans recipes.py** (utiliser schemas/recipe.py)
10. **Ajout de tests automatises** pour tous les endpoints

---

## 7. Resume

| Categorie | Nombre |
|---|---|
| Endpoints testes | 24 |
| Endpoints OK (2xx) | 22 |
| Endpoints KO (5xx) | **1** (billing/status) |
| Endpoints 4xx attendu | 1 (validate plan deja valide = 409) |
| Bugs critiques | **2** (JWT bypass + mismatch colonnes) |
| Bugs haute gravite | 4 |
| Bugs moyenne gravite | 4 |
| Bugs basse gravite | 3 |
| **Total bugs** | **13** |

Les deux bugs critiques (B09 et B05/B10/B11) doivent etre corriges et deployes dans les 24h. Le JWT sans verification (B09) est une faille de securite exploitable.
