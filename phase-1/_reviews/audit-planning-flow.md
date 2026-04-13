# Audit Flow Generation Planning -- Presto

> Date : 2026-04-13
> Auditeur : debugger senior
> Scope : trace complete du flow clic bouton --> affichage recettes

---

## Trace du flow (etape par etape)

### Etape 1 : Frontend --> API

**Fichiers concernes :**
- `apps/web/src/app/(app)/dashboard/dashboard-content.tsx`
- `apps/web/src/hooks/use-plan.ts`
- `apps/web/src/lib/api/endpoints.ts`
- `apps/web/src/lib/api/client.ts`

**Flow detaille :**

1. L'utilisateur clique sur "Generer mon planning" dans `EmptyPlanState`
2. `handleGenerate()` est appele (dashboard-content.tsx L32-62)
3. Annulation d'un eventuel retry en cours (retryTimerRef)
4. `generateMutation.mutate(undefined, { onError })` est appele
5. `useGeneratePlan()` (use-plan.ts L60-82) declenche `mutationFn: generatePlan`
6. `generatePlan()` (endpoints.ts L158-161) :
   - Calcule `week_start` via `getNextMonday()` (L114-122)
   - Envoie `POST /api/v1/plans/generate` avec body `{ week_start: "YYYY-MM-DD" }`
7. `apiClient.post()` (client.ts L139-142) :
   - Construit l'URL : `${API_BASE_URL}/api/v1/plans/generate`
   - Recupere le JWT Supabase via `getAuthToken()` (supabase.auth.getSession())
   - Envoie le header `Authorization: Bearer <JWT>`
   - Timeout de 15 secondes

**Endpoint appele :** `POST https://meal-planner-saas-production.up.railway.app/api/v1/plans/generate`
**Body :** `{ "week_start": "2026-04-13" }` (lundi calcule dynamiquement)
**Auth :** Bearer JWT Supabase (via `supabase.auth.getSession().access_token`)

**Gestion d'erreurs frontend :**
- TypeError "Failed to fetch" --> toast + retry auto 3s
- 401/403 --> toast "Session expiree"
- Autre erreur --> toast generique

**Calcul getNextMonday() :** VALIDE -- teste pour le 12 avril (dimanche) retourne bien le 13 avril (lundi).

**PROBLEME IDENTIFIE : Pas de polling apres la generation**
- `onSuccess` de la mutation fait `queryClient.invalidateQueries(["plans", "current"])`
- Cela declenche UN SEUL re-fetch de `GET /plans/me/current`
- MAIS la generation est ASYNCHRONE (Celery) -- le plan N'EST PAS pret immediatement
- Le re-fetch retourne probablement `null` --> le frontend reste sur l'etat vide
- Il n'y a AUCUN mecanisme de polling sur le task_id ou de retry periodique

---

### Etape 2 : API --> Celery

**Fichiers concernes :**
- `apps/api/src/api/v1/plans.py` (handler generate_plan L123-207)
- `apps/api/src/core/security.py` (verification JWT)
- `apps/api/src/api/v1/schemas/plan.py` (GeneratePlanRequest)

**Flow detaille :**

1. SlowAPI rate limiter verifie la limite (10/heure par user)
2. `get_current_user_dep()` extrait et verifie le JWT :
   - Essaie 4 methodes de verification de signature (L106-141)
   - Methode 4 (fallback) : decode SANS verification de signature
   - Retourne `TokenPayload` avec `user_id` (claim "sub")
3. `GeneratePlanRequest` Pydantic valide le body :
   - `week_start` : date ISO, DOIT etre un lundi (model_post_init L116-122)
   - `num_dinners` : defaut 5, min 3, max 7
4. `_get_user_household_id(session, user.user_id)` :
   - SQL : `SELECT household_id FROM household_members WHERE supabase_user_id = :user_id`
   - Si pas de resultat --> HTTP 404 "Vous n'appartenez a aucun foyer"
5. Import tardif de la tache Celery (L167-192) :
   - `from src.agents.weekly_planner.tasks import generate_plan_task`
   - `generate_plan_task.apply_async(kwargs={...}, queue="llm")`
   - Retourne `TaskResponse(task_id=..., poll_url="/api/v1/plans/me/current")`

**Nom de la tache Celery :** `weekly_planner.generate_plan`
**Queue :** `llm`
**Reponse :** HTTP 202 `{ task_id, status: "pending", message, poll_url }`

**PROBLEME CRITIQUE IDENTIFIE : Import Celery impossible en production**
- Le Dockerfile API copie UNIQUEMENT `apps/api/` dans l'image
- Le code `from src.agents.weekly_planner.tasks import generate_plan_task` reference `apps/worker/src/agents/...`
- Ce module N'EXISTE PAS dans le conteneur API (pas de dossier `src/agents/`)
- De plus, `celery` n'est PAS dans les dependances de `mealplanner-api` (pyproject.toml)
- L'import echoue avec `ModuleNotFoundError` (ou `ImportError`)
- Le `try/except Exception` attrape l'erreur et retourne HTTP 503
- **CONSEQUENCE : Chaque tentative de generation retourne TOUJOURS 503 en production**

**PROBLEME SECONDAIRE : Validation JWT methode 4 (sans verification)**
- En production, si SUPABASE_JWT_SECRET n'est pas configure et SUPABASE_ANON_KEY est incorrect, les methodes 1-3 echouent
- La methode 4 decode SANS verifier la signature --> faille de securite
- Tout JWT avec un `sub` valide (UUID) est accepte meme sans cle valide
- Ce n'est PAS bloquant pour le flow, mais c'est un risque de securite

---

### Etape 3 : Worker Celery --> DB

**Fichiers concernes :**
- `apps/worker/src/agents/weekly_planner/tasks.py`
- `apps/worker/src/agents/weekly_planner/agent.py`
- `apps/worker/src/agents/weekly_planner/recipe_retriever.py`
- `apps/worker/src/agents/weekly_planner/plan_selector.py`
- `apps/worker/src/agents/weekly_planner/shopping_list_builder.py`
- `apps/worker/src/agents/weekly_planner/constraint_builder.py`
- `packages/db/src/mealplanner_db/session.py`

**Flow detaille (SI la tache arrive au worker) :**

1. `generate_plan_task` (Celery bind=True, queue=llm, soft_time_limit=300s)
2. Parse `week_start_iso` en `date` + valide le format
3. Cree `WeeklyPlannerAgent(session_factory=AsyncSessionLocal)` depuis `mealplanner_db.session`
4. Appelle `agent.run(household_id, week_start, num_dinners)`

**Pipeline agent.run() :**

- **Etape 3.1 : Validation** -- week_start doit etre un lundi (isoweekday() == 1)
- **Etape 3.2 : Chargement preferences** -- SQL JOIN household_members + member_preferences
- **Etape 3.3 : Construction contraintes** -- `build_household_constraints()` :
  - Regimes : UNION (si un membre est vegetarien, plan vegetarien)
  - Allergies : UNION stricte (securite alimentaire)
  - Temps max : MINIMUM des membres
  - Budget : le plus restrictif
- **Etape 3.4 : Vecteur de gout** -- `get_household_taste_vector()` :
  - JOIN member_taste_vectors + household_members
  - Retourne None si aucun vecteur (nouveau foyer sans feedbacks)
- **Etape 3.5 : Recherche candidats** -- `retrieve_candidate_recipes()` :
  - Tente pgvector HNSW si taste_vector disponible
  - Sinon fallback quality_score avec JOIN recipe_embeddings
  - **FALLBACK CRITIQUE : `_retrieve_by_quality_no_embedding()`**
    - Active si aucun candidat (recipe_embeddings vide = 0 embeddings en prod)
    - Retourne les 30 meilleures recettes par quality_score SANS JOIN recipe_embeddings
    - Applique les contraintes (temps, tags exclus) et ORDER BY RANDOM()
    - C'est ce path qui sera emprunte en production (0 embeddings)
- **Etape 3.6 : Scoring et selection** -- `score_candidates()` + `select_diverse_plan()` :
  - Score composite = 0.5*similarity + 0.3*quality + 0.1*difficulty_bonus
  - Sans embeddings, similarity = 0 (distance = 1.0 par defaut)
  - Selection diversifiee : max 2 recettes de meme cuisine
  - Fallback si pas assez : relache la contrainte cuisine
- **Etape 3.7 : Liste de courses** -- `build_shopping_list()` :
  - JOIN recipe_ingredients + ingredients + recipes
  - Scaling par nombre de personnes
  - Normalisation unites (g, ml, etc.)
  - Exclusion ingredients du frigo (fridge_items)
  - Tri par rayon supermarche
- **Etape 3.8 : Persistance** -- `_persist_plan()` :
  - INSERT INTO weekly_plans (UPSERT sur household_id + week_start)
  - DELETE + INSERT batch INTO planned_meals
  - INSERT INTO shopping_lists (UPSERT)
  - COMMIT

**Connexion DB worker :**
- `mealplanner_db.session.AsyncSessionLocal` avec `NullPool` (pas de pool persistant)
- `DATABASE_URL` depuis l'environnement
- `statement_cache_size=0` pour compatibilite pgBouncer/Supabase

**PROBLEME : recipe_embeddings vide (0 embeddings)**
- Le fallback `_retrieve_by_quality_no_embedding()` fonctionne correctement
- Il retourne 30 recettes parmi les 591 en base (quality_score >= 0.6)
- Contraintes temps/allergies respectees
- ORDER BY RANDOM() pour la diversite
- CE N'EST PAS un blocage -- le fallback est operationnel

**PROBLEME POTENTIEL : recipe_ingredients vide**
- Si les recettes n'ont pas d'ingredients lies (recipe_ingredients vide), la liste de courses sera vide
- Cela ne bloque PAS la generation du plan, mais l'experience utilisateur est degradee
- A verifier en base

---

### Etape 4 : Frontend -- Polling du resultat

**Mecanisme actuel :**
1. `POST /plans/generate` retourne `TaskResponse { task_id, status: "pending", poll_url }`
2. `onSuccess` dans `useGeneratePlan()` fait `queryClient.invalidateQueries(["plans", "current"])`
3. Cela declenche `useCurrentPlan()` qui fait `GET /api/v1/plans/me/current`
4. La query a un `staleTime: 2 * 60 * 1000` (2 minutes) et `retry: failureCount < 2`

**PROBLEME BLOQUANT : Pas de vrai polling**
- La generation Celery prend potentiellement 5-60 secondes
- Le re-fetch est un one-shot IMMEDIAT apres la reponse 202
- A ce moment, le plan n'est probablement PAS encore genere
- `GET /plans/me/current` retourne `null` (pas de plan pour la semaine)
- Le frontend affiche l'etat vide "Votre semaine vous attend"
- L'utilisateur croit que rien ne s'est passe
- Il n'y a AUCUN mecanisme de :
  - Polling periodique sur task_id
  - Polling periodique sur /plans/me/current
  - Websocket / Server-Sent Events
  - refetchInterval dans TanStack Query

---

### Etape 5 : Affichage du plan

**Fichiers concernes :**
- `apps/web/src/components/plan/plan-week-grid.tsx`
- `apps/web/src/lib/api/endpoints.ts` (PlanDetail type)
- `apps/web/src/lib/api/types.ts` (WeeklyPlan, PlannedMeal types)

**Flow :**
1. `DashboardContent` recoit `planDetail` depuis `useCurrentPlan()`
2. `PlanWeekGrid` recoit `planDetail` et affiche la grille
3. `planDetail.meals` est itere pour grouper les repas par jour
4. `planDetail.recipes` est indexe par ID pour lookup O(1)

**PROBLEME CRITIQUE : Mismatch types frontend/backend**

**Mismatch 1 -- Structure PlanDetail vs WeeklyPlanDetail :**
- Frontend attend : `{ plan: WeeklyPlan, meals: PlannedMeal[], recipes: Recipe[] }`
- Backend retourne : `{ id, household_id, week_start, status, ..., meals: [...], shopping_list: [...] }`
- Le backend NE retourne PAS un champ `plan` separe ni un champ `recipes`
- Les champs du plan sont directement au top-level
- `planDetail.plan` serait `undefined`
- `planDetail.plan.id` crasherait avec TypeError

**Mismatch 2 -- day_of_week int vs string :**
- Backend : `day_of_week: int` (1-7, 1=lundi)
- Frontend PlanWeekGrid attend des strings ("monday", "tuesday", etc.)
- `mealsByDay.get(meal.day_of_week)` avec `meal.day_of_week = 1` retourne `undefined`
- Les repas ne sont JAMAIS affiches dans la grille
- La grille affiche 7 jours vides "Aucun repas planifie"

**Mismatch 3 -- PlannedMeal.recipe_id vs recipe lookup :**
- `recipesById.get(meal.recipe_id)` -- mais `planDetail.recipes` est `undefined` (pas retourne par le backend)
- Meme si les meals etaient correctement groupes, les recettes ne seraient pas trouvees

**Mismatch 4 -- week_start vs week_start_date :**
- Backend : `week_start: date` (format "YYYY-MM-DD")
- Frontend WeeklyPlan : `week_start_date: string`
- Le champ `plan.week_start_date` serait `undefined`

**Mismatch 5 -- status values :**
- Backend : `"draft" | "validated" | "archived"`
- Frontend WeeklyPlan : `"draft" | "confirmed" | "completed"`
- Le status ne matcherait jamais pour les conditions d'affichage

---

## Resultats curl

### Test 1 : Health
```
GET /api/v1/health --> 200 {"status":"ok"}
```
API UP.

### Test 2 : Ready
```
GET /api/v1/ready --> 200
{"status":"ready","model":true,"database":true,"redis":true,"db_latency_ms":181.25,"redis_latency_ms":738.05}
```
DB connectee (latence ~181ms -- Supabase free tier).
Redis connecte (latence ~738ms -- Redis cloud, normal).
Modele ML charge.

### Test 3 : Generate sans auth
```
POST /api/v1/plans/generate --> 401
{"detail":"Header Authorization manquant ou format invalide. Format attendu : 'Bearer <token>'"}
```
CORRECT -- auth requise.

### Test 4 : Generate avec token dummy (sub non-UUID)
```
POST /api/v1/plans/generate (sub: "test-user-123") --> 500
{"error":"internal_server_error","message":"Une erreur inattendue s'est produite.","correlation_id":"5cc7bb82"}
```
BUG : le `sub` "test-user-123" n'est pas un UUID valide.
La requete SQL `WHERE supabase_user_id = :user_id` crashe car la colonne est de type UUID.
PostgreSQL rejette le cast implicite string --> UUID.

### Test 5 : Generate avec token UUID (pas de household)
```
POST /api/v1/plans/generate (sub: "00000000-0000-0000-0000-000000000001") --> 404
{"detail":"Vous n'appartenez a aucun foyer. Creez-en un via POST /api/v1/households."}
```
CORRECT -- l'utilisateur test n'a pas de household.

### Test 6 : Households/me avec UUID (pas de household)
```
GET /api/v1/households/me (sub: UUID) --> 404
{"detail":"Vous n'appartenez a aucun foyer. Creez-en un via POST /api/v1/households."}
```
CORRECT.

### Test 7 : Plans/me/current avec UUID (pas de household)
```
GET /api/v1/plans/me/current (sub: UUID) --> 404
```
CORRECT.

### Test 8 : Token invalide (non-JWT)
```
Authorization: Bearer invalid --> 401
{"detail":"Token JWT invalide."}
```
CORRECT -- les 4 methodes de decode echouent, 401 retourne.

### Test 9 : Recipes (public, pas d'auth requise)
```
GET /api/v1/recipes?page=1&per_page=2 --> 200
591 recettes en base, donnees correctes.
```

---

## Points de blocage identifies

### 1. [BLOQUANT] Import Celery impossible depuis le conteneur API

**Cause :** Le Dockerfile API ne copie que `apps/api/`. Le code `from src.agents.weekly_planner.tasks import generate_plan_task` reference `apps/worker/src/agents/...` qui n'existe pas dans l'image API. De plus, `celery` n'est pas une dependance de `mealplanner-api`.

**Consequence :** Chaque appel `POST /plans/generate` retourne HTTP 503 "Le service de generation de plans est temporairement indisponible." pour tout utilisateur ayant un household.

**Fix :** Remplacer l'import direct par `celery_app.send_task("weekly_planner.generate_plan", kwargs={...}, queue="llm")`. Ajouter `celery[redis]` aux dependances de l'API, et creer un mini-module `src/celery_client.py` dans l'API qui configure une instance Celery legere (broker-only, pas de worker).

### 2. [BLOQUANT] Pas de polling apres generation asynchrone

**Cause :** `useGeneratePlan()` fait un seul `invalidateQueries` apres le 202. La tache Celery prend des secondes/minutes. Le re-fetch retourne null.

**Consequence :** L'utilisateur clique, voit "Generation en cours..." puis retombe sur l'etat vide. Le plan est peut-etre genere en arriere-plan mais jamais affiche.

**Fix :** Ajouter un `refetchInterval` conditionnel dans `useCurrentPlan()` :
```typescript
refetchInterval: isPolling ? 3000 : false, // Poll toutes les 3s quand en attente
```
Ou bien utiliser le `task_id` retourne pour poller `GET /tasks/{task_id}/status`.

### 3. [BLOQUANT] Mismatch structure PlanDetail frontend/backend

**Cause :** Le backend retourne `WeeklyPlanDetail` (champs plats), le frontend attend `{ plan: WeeklyPlan, meals: PlannedMeal[], recipes: Recipe[] }`.

**Consequence :** `planDetail.plan.id` --> TypeError (plan est undefined). Le dashboard crasherait en runtime si un plan existait.

**Fix :** Aligner le type frontend `PlanDetail` sur la structure backend `WeeklyPlanDetail`, OU ajouter un layer de normalisation dans `getCurrentPlan()`.

### 4. [BLOQUANT] day_of_week int (backend) vs string (frontend)

**Cause :** Backend stocke 1-7 (int), `PlanWeekGrid` utilise "monday"-"sunday" comme cles Map.

**Consequence :** `mealsByDay.get(1)` retourne undefined. Les 7 jours s'affichent vides meme si des meals existent.

**Fix :** Convertir int --> string dans le frontend :
```typescript
const DAY_INT_TO_STRING: Record<number, string> = { 1: "monday", 2: "tuesday", ... };
```

### 5. [BLOQUANT] Pas de champ `recipes` dans la reponse backend

**Cause :** `WeeklyPlanDetail` backend inclut des champs denormalises dans `PlannedMealRead` (recipe_title, recipe_photo_url, etc.) mais pas un tableau `recipes[]` separe.

**Consequence :** `recipesById.get(meal.recipe_id)` retourne undefined. Les RecipeCards ne s'affichent pas.

**Fix :** Soit le backend ajoute un champ `recipes: list[RecipeRead]` a WeeklyPlanDetail, soit le frontend reconstruit les objets Recipe depuis les champs denormalises de PlannedMealRead.

### 6. [MODERE] Securite JWT methode 4 sans verification de signature

**Cause :** Si les methodes 1-3 echouent (SUPABASE_JWT_SECRET mal configure), la methode 4 decode n'importe quel JWT sans verifier la signature.

**Consequence :** Tout attaquant peut forger un JWT avec n'importe quel `sub` (UUID) et acceder aux donnees de cet utilisateur.

**Fix :** Supprimer la methode 4 OU la restreindre a ENV=dev uniquement. En production, si les 3 premieres methodes echouent, retourner 401 inconditionnellement.

### 7. [MODERE] Erreur 500 si sub n'est pas UUID

**Cause :** `supabase_user_id` est de type UUID en PostgreSQL. Si le JWT contient un `sub` non-UUID, le SQL plante avec une erreur de cast.

**Consequence :** 500 Internal Server Error au lieu d'un 401 propre.

**Fix :** Ajouter une validation UUID dans `get_current_user()` :
```python
try:
    UUID(payload.user_id)
except ValueError:
    raise HTTPException(401, "Token JWT invalide : sub n'est pas un UUID.")
```

### 8. [MODERE] recipe_embeddings vide (0 embeddings)

**Cause :** Le pipeline RECIPE_SCOUT n'a pas encore genere les embeddings pour les 591 recettes.

**Consequence :** Le path pgvector est jamais utilise. Le fallback `_retrieve_by_quality_no_embedding()` fonctionne mais sans personnalisation (similarite gout = 0).

**Fix :** Lancer le pipeline RECIPE_SCOUT manuellement pour generer les embeddings. Ou ajouter un endpoint admin `POST /admin/embed-recipes`.

### 9. [MINEUR] Redis latence 738ms

**Cause :** Redis cloud (potentiellement dans une region differente de Railway).

**Consequence :** Rate limiting ajoute ~738ms de latence a chaque requete (via SlowAPI Redis check).

**Fix :** Verifier que Redis et Railway sont dans la meme region. Ou utiliser le Redis fourni par Railway.

### 10. [MINEUR] DB latence 181ms

**Cause :** Supabase Free tier, potentiellement dans une region differente.

**Consequence :** Chaque requete DB ajoute ~181ms minimum.

**Fix :** Verifier la region Supabase (recommande : meme region que Railway). Upgrade vers Supabase Pro pour de meilleures performances.

---

## Plan de correction (ordre d'execution)

### Phase A : Debloquer la generation (critique, <2h)

**A1. Corriger l'import Celery dans l'API**
- Fichier : `apps/api/src/api/v1/plans.py`
- Action : Remplacer l'import direct par `celery_app.send_task()`
- Creer `apps/api/src/core/celery_client.py` avec une instance Celery legere
- Ajouter `celery[redis]` dans `apps/api/pyproject.toml`

**A2. Implementer le polling frontend**
- Fichier : `apps/web/src/hooks/use-plan.ts`
- Action : Apres le 202, activer un polling toutes les 3s sur `/plans/me/current`
- Timeout apres 120s avec message d'erreur

### Phase B : Corriger l'affichage du plan (critique, <3h)

**B1. Aligner PlanDetail frontend sur WeeklyPlanDetail backend**
- Fichier : `apps/web/src/lib/api/endpoints.ts`
- Action : Modifier le type `PlanDetail` pour matcher la structure backend plate
- OU ajouter une fonction de normalisation dans `getCurrentPlan()`

**B2. Convertir day_of_week int --> string**
- Fichier : `apps/web/src/components/plan/plan-week-grid.tsx`
- Action : Ajouter un mapping `{ 1: "monday", 2: "tuesday", ... }`
- Appliquer dans le groupement mealsByDay

**B3. Reconstruire les objets Recipe depuis les champs denormalises**
- Fichier : `apps/web/src/components/plan/plan-week-grid.tsx`
- Action : Construire les Recipe depuis `PlannedMealRead.recipe_*` 
- OU ajouter un champ `recipes[]` dans WeeklyPlanDetail backend

### Phase C : Securite et robustesse (important, <1h)

**C1. Supprimer la methode 4 JWT (nosig) en production**
- Fichier : `apps/api/src/core/security.py`
- Action : Conditionner la methode 4 a `ENV != "prod"`

**C2. Valider le format UUID du sub JWT**
- Fichier : `apps/api/src/core/security.py`
- Action : Ajouter validation `UUID(payload.user_id)` dans `get_current_user()`

### Phase D : Qualite de l'experience (amelioration)

**D1. Generer les embeddings pour les 591 recettes**
- Action : Lancer le pipeline RECIPE_SCOUT ou un script batch

**D2. Optimiser les latences Redis/DB**
- Action : Verifier les regions, co-localiser les services
