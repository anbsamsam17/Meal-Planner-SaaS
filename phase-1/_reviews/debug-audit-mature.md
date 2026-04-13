# Debug Audit Phase 1 Mature — MealPlanner
> Date : 2026-04-12 | Auditeur : Claude Debugger | Scope : ~100 nouveaux fichiers Phase 1 mature

---

## Bugs CRITICAL (code ne démarre/fonctionne pas)

### BUG #C1 — `asyncio.run()` dans Celery prefork avec event loop existant [CRITICAL]
**Fichiers :** `apps/worker/src/agents/weekly_planner/tasks.py` lignes 98-105
**Symptôme :** `asyncio.run(_run())` lève `RuntimeError: This event loop is already running` dans le pool prefork Celery si le worker a déjà un loop actif. Le `except RuntimeError` fallback vers `new_event_loop()` est la bonne approche, **mais** il y a un risque silencieux : si c'est eventlet/gevent qui est utilisé comme pool, `asyncio.run()` crashe d'une façon différente que `RuntimeError` (il lève `DeprecationWarning` + `RuntimeError` monkeypatch) et le fallback ne se déclenche pas de manière fiable.
**Root cause :** Le fallback est correct pour prefork mais ne couvre pas eventlet/gevent.
**Fix :** Documenter explicitement que le pool doit être `--pool=prefork` (pas eventlet) dans le `Makefile`/`docker-compose`. Alternative : utiliser `asyncio.get_event_loop().run_until_complete()` systématiquement avec vérification `loop.is_running()`.
**Sévérité réelle :** HIGH si prefork (fonctionne), CRITICAL si eventlet activé.

---

### BUG #C2 — `pollUntilPlanReady` poll sur `/api/v1/plans/{taskId}` : le `taskId` est un UUID Celery, pas un plan_id [CRITICAL]
**Fichier :** `apps/web/src/stores/onboarding-store.ts` lignes 238 + plans.py route `GET /{plan_id}`
**Symptôme :** `pollUntilPlanReady(taskId)` appelle `GET /api/v1/plans/{taskId}` en passant le **task_id Celery** (UUID de tâche). Mais l'endpoint `GET /plans/{plan_id}` attend un **UUID de plan** en base, pas un task_id Celery. PostgreSQL retournera systématiquement 404 car aucun plan n'a l'UUID Celery comme `id`. Le polling ne se termine jamais avec succès → après 30 tentatives (≈ 90 secondes) → `throw "Délai d'attente dépassé"` → rollback step 3.
**Root cause :** Confusion task_id Celery vs plan_id DB. Le `TaskResponse` retourné par `POST /plans/generate` donne `poll_url: "/api/v1/plans/me/current"` dans le commentaire mais le store poll sur `plans/{task_id}`.
**Fix :** Le store doit utiliser `GET /api/v1/plans/me/current` (qui vérifie le plan de la semaine courante) et checker `status === 'draft'` ou `status === 'validated'` comme signal de readiness. Ou ajouter un endpoint `GET /tasks/{task_id}/status` qui wrape `AsyncResult(task_id)`.
**Impact :** Le 1er onboarding ne se termine jamais → 100% des nouveaux users bloqués.

---

### BUG #C3 — `recipe_retriever.py` : filtre `re.total_time_min` sur `recipe_embeddings` mais la colonne est sur `recipes` [CRITICAL]
**Fichier :** `apps/worker/src/agents/weekly_planner/recipe_retriever.py` lignes 264, 318
**Symptôme :** `AND (re.total_time_min IS NULL OR re.total_time_min <= :time_max)` — `re` est l'alias de `recipe_embeddings` mais `total_time_min` est une colonne de la table `recipes` (alias `r`), pas de `recipe_embeddings`. La query PostgreSQL lève `ERROR: column re.total_time_min does not exist` → toute recherche de recettes candidates crash → aucun plan ne peut être généré.
**Root cause :** Confusion d'alias table dans le SQL inline. Le filtre doit être `r.total_time_min`.
**Fix :** Remplacer `re.total_time_min` par `r.total_time_min` aux deux endroits (fonctions `_retrieve_by_similarity` et `_retrieve_by_quality`).

---

### BUG #C4 — `onboarding-store.ts` submit : pas de rollback DB en cas d'échec partiel [CRITICAL - DATA ORPHELINE]
**Fichier :** `apps/web/src/stores/onboarding-store.ts` lignes 136-208
**Symptôme :** Le submit enchaîne séquentiellement : (1) créer household, (2) créer membres enfants, (3) PATCH préférences, (4) POST generate plan. Si l'étape 3 ou 4 échoue, le household et les membres sont créés en DB sans préférences ni plan. Au retry, l'user retombe sur `POST /households` qui retourne 409 (household déjà existant). L'user est bloqué : il a un household orphelin sans plan et ne peut pas en créer un nouveau.
**Root cause :** Orchestration côté client sans transaction distribuée ni endpoint d'onboarding atomique.
**Fix immédiat :** Ajouter `GET /api/v1/households/me` en début de submit pour détecter un household existant et reprendre depuis l'étape correcte. Fix structurel : créer un endpoint `POST /api/v1/onboarding/complete` qui effectue toutes les opérations en une seule transaction server-side.

---

## Bugs HIGH (crash au 1er usage)

### BUG #H1 — `OFFMapper` : `off_client.search_product()` est synchrone dans une coroutine async [HIGH]
**Fichiers :** `apps/worker/src/agents/recipe_scout/off_mapper.py` + `openfoodfacts.py`
**Symptôme :** `OFFMapper.map_missing_ingredients()` est `async def` mais appelle `self.off_client.search_product()` qui est synchrone (httpx.Client + `time.sleep(0.5)` bloquant). Chaque appel OFF bloque l'event loop 0.5-10s. En batch de 50 ingrédients → 25-500 secondes de blocage total de l'event loop asyncio.
**Fix :** Utiliser `asyncio.get_event_loop().run_in_executor(None, self.off_client.search_product, query)` ou migrer `OpenFoodFactsClient` vers `httpx.AsyncClient`.

### BUG #H2 — `plans.py` : route `/me/current` vs `/{plan_id}` — conflit de routing FastAPI [HIGH]
**Fichier :** `apps/api/src/api/v1/plans.py` lignes 161-278
**Symptôme :** FastAPI résout les routes dans l'ordre de déclaration. `GET /{plan_id}` est déclaré **avant** `GET /me/current` (ligne 163 avant 228). Quand le frontend appelle `GET /plans/me/current`, FastAPI matche d'abord `/{plan_id}` avec `plan_id="me"` → tente `UUID("me")` → `ValueError` → 422 Unprocessable Entity. La route `/me/current` n'est jamais atteinte.
**Fix :** Inverser l'ordre des routes : déclarer `GET /me/current` **avant** `GET /{plan_id}`.

### BUG #H3 — `households.py` : création household pas vraiment atomique [HIGH]
**Fichier :** `apps/api/src/api/v1/households.py` lignes 101-200
**Symptôme :** La création du household et du premier membre se fait dans `async with db_session() as session:` mais si l'INSERT member échoue (violation contrainte, DB timeout), la session rollback automatiquement → les deux INSERTs sont annulés. C'est correct. **Cependant**, après le `await session.commit()` (ligne 190), la méthode appelle `_get_household_by_id()` qui ouvre **une nouvelle session** (ligne 200). Si cette session échoue (DB momentanément indisponible), le household est créé en DB mais l'API retourne 500 → le client croit que ça a échoué et retry → 409 au retry.
**Fix :** Le 409 au retry doit être traité comme un succès par le client — renvoyer le household existant plutôt que 409 quand l'utilisateur tente de créer un household alors qu'il en possède déjà un.

---

## Bugs MEDIUM

### BUG #M1 — `shopping_list_builder.py` : `1 boîte + 500g` génère deux entrées distinctes — comportement attendu mais non documenté [MEDIUM]
**Fichier :** `apps/worker/src/agents/weekly_planner/shopping_list_builder.py` lignes 283
**Symptôme :** L'ingrédient "tomates pelées" avec `(1, "boîte")` d'une recette et `(500, "g")` d'une autre génère `quantities: [{"unit": "boîte", "qty": 1}, {"unit": "g", "qty": 500}]` — deux entrées séparées par unité (comportement intentionnel documenté en v0). Non bloquant mais peut surprendre l'utilisateur (deux lignes pour le même ingrédient).

### BUG #M2 — `plan_selector.py` : `candidate not in selected` utilise `__eq__` de dataclass qui compare tous les champs [MEDIUM]
**Fichier :** `apps/worker/src/agents/weekly_planner/plan_selector.py` ligne 202
**Symptôme :** `if candidate not in selected` — les dataclasses Python comparent tous les champs. Si deux recettes ont le même `recipe_id` mais des `composite_score` différents (recalculés), elles ne seront pas considérées comme identiques → duplication possible en fallback diversité.
**Fix :** Comparer par `recipe_id` explicitement : `if candidate.recipe_id not in {r.recipe_id for r in selected}`.

### BUG #M3 — Migrations `0004`/`0005` : `op.execute()` avec `ADD COLUMN IF NOT EXISTS` — syntaxe valide mais perd le type checking Alembic [MEDIUM]
**Fichiers :** migrations 0004 et 0005
**Symptôme :** `op.execute("ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...")` est syntaxiquement valide en PostgreSQL 9.6+. Mais Alembic ne peut pas générer de `downgrade()` automatique et ne peut pas détecter les conflits de type. Le `downgrade()` manuel présent est correct. Non bloquant.

### BUG #M4 — `cuisine_az.py` (750g.com) : le fichier est nommé `cuisine_az` mais scrape `750g.com` [MEDIUM]
**Fichier :** `apps/worker/src/agents/recipe_scout/scrapers/cuisine_az.py` lignes 37-38
**Symptôme :** Le nom du module (`cuisine_az`) ne correspond pas au site scrapé (`750g.com`). `CUISINE_AZ_BASE_URL = "https://www.750g.com"`. Confusion certaine à la maintenance. Cuisine-AZ est un site différent (cuisine-az.com) — si quelqu'un ajoute un vrai scraper cuisine-az.com, collision de nommage garantie.

---

## Flows validés (ça devrait marcher)

1. **`WeeklyPlannerAgent.run()`** — pipeline complet async correct (session factory, contraintes, scoring, persistance). Atomicité de `_persist_plan()` via une seule session avec commit final.

2. **`constraint_builder.py`** — agrégation UNION/MINIMUM propre, gestion des None, tri déterministe.

3. **`plan_selector.py`** — algorithme de diversité cuisine correct (`MAX_SAME_CUISINE=2`), fallback sans contrainte documenté.

4. **`allrecipes.py`** — parsing JSON-LD robuste, gère array/objet/`@graph`, HowToSection, fallback CSS. `_parse_time_iso()` correct pour PT1H30M.

5. **`openfoodfacts.py`** — cache dict + retry tenacity + throttling 0.5s. Gestion des produits sans `product_name` correcte (filtre ligne 260 : `p.get("product_name")`).

6. **`households.py`** — création atomique dans une seule session, vérification d'appartenance préalable, UPSERT préférences correct.

7. **`feedbacks.py`** — pagination `offset = (page - 1) * per_page` **correcte** (page 1 → offset 0).

8. **`router.py`** — tous les routers inclus : `health`, `recipes`, `households`, `plans`, `feedbacks`.

9. **Auth callback `route.ts`** — `searchParams.get("code")` correct, vérification household via API avec JWT, fallback onboarding sécuritaire.

10. **`step-1/page.tsx`** — `adultsCount` initialisé à 2, min=1 → impossible d'avoir 0 adultes. `isValid = totalMembers >= 1` toujours vrai grâce au min=1. Correct.

11. **`step-2/page.tsx`** — `toggleRestriction("no-restriction")` efface tous les autres tags, et choisir n'importe quelle restriction efface `no-restriction`. Logique d'exclusion mutuelle correcte.

12. **Migrations `0004`/`0005`** — chaîne `0001 → 0003 → 0004 → 0005` correcte (`down_revision` vérifiés). `ADD COLUMN IF NOT EXISTS` et `CREATE INDEX IF NOT EXISTS` idempotents.

13. **`tasks.py` weekly_planner** — `name="weekly_planner.generate_plan"` correspond au nom attendu. Import tardif des dépendances dans `_run()` évite la circularité.

14. **`shopping_list_builder.py`** — conversion d'unités `g+kg→g`, `ml+cl→ml` correcte via `_normalize_unit()`. Scaling portions correct (`Decimal` pour éviter les erreurs float).

---

## Commandes de validation prioritaires

```bash
# BUG #C3 : valider le SQL recipe_retriever
psql "$DATABASE_URL" -c "SELECT r.total_time_min FROM recipes r JOIN recipe_embeddings re ON re.recipe_id = r.id LIMIT 1"

# BUG #H2 : vérifier l'ordre des routes FastAPI (me/current doit être avant /{plan_id})
uv run python -c "from apps.api.src.api.v1.plans import router; [print(r.path) for r in router.routes]"

# BUG #C2 : vérifier que le polling utilise le bon endpoint
grep -n "plans/" apps/web/src/stores/onboarding-store.ts
```

---

## Résumé par sévérité

| # | Bug | Fichier | Sévérité | Impact |
|---|-----|---------|----------|--------|
| C1 | asyncio.run() eventlet incompatibility | `weekly_planner/tasks.py` | CRITICAL/HIGH | Celery crash si eventlet pool |
| C2 | Polling task_id vs plan_id | `onboarding-store.ts` + `plans.py` | CRITICAL | 100% nouveaux users bloqués |
| C3 | `re.total_time_min` colonne inexistante | `recipe_retriever.py` | CRITICAL | Aucun plan ne peut être généré |
| C4 | Household orphelin sans rollback | `onboarding-store.ts` | CRITICAL | User bloqué si échec étape 3-4 |
| H1 | off_client sync dans coroutine async | `off_mapper.py` | HIGH | Event loop bloquée 25-500s |
| H2 | Route `/me/current` masquée par `/{plan_id}` | `plans.py` | HIGH | GET plans/me/current → 422 |
| H3 | household créé + _get retour 500 → retry 409 | `households.py` | HIGH | User pense que création a échoué |
| M1 | 1 boîte + 500g = 2 entrées | `shopping_list_builder.py` | MEDIUM | UX confuse (voulu en v0) |
| M2 | `candidate not in selected` par equality pas id | `plan_selector.py` | MEDIUM | Duplication possible en fallback |
| M3 | `op.execute()` perd type checking Alembic | `migrations 0004/0005` | LOW | Maintenabilité réduite |
| M4 | Fichier cuisine_az scrape 750g.com | `cuisine_az.py` | LOW | Confusion maintenance |

---

## Verdict : FIXES REQUIRED (3 CRITICAL bloquants runtime)

**BUG #C2** et **BUG #C3** rendent le produit inutilisable en l'état :
- **C3** : aucun plan ne peut être généré (SQL error sur chaque appel)
- **C2** : même si C3 est corrigé, le polling frontend ne converge jamais
- **C4** : les retries après erreur laissent des données orphelines en DB

**BUG #H2** (ordre routes FastAPI) bloque silencieusement le dashboard si `GET /plans/me/current` est appelé — 422 au lieu de 200.

**Priorité de correction :**
1. `recipe_retriever.py` : `re.total_time_min` → `r.total_time_min` (2 lignes, 2 min)
2. `plans.py` : inverser `GET /me/current` avant `GET /{plan_id}` (déplacer 50 lignes, 5 min)
3. `onboarding-store.ts` : corriger l'URL de polling vers `/api/v1/plans/me/current` + gérer le retry 409 (15 min)
4. `onboarding-store.ts` : ajouter détection household existant en début de submit (30 min)
