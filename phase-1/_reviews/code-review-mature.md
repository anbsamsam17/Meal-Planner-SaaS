# Code Review Phase 1 Mature -- MealPlanner

Date : 2026-04-12
Reviewer : code-reviewer (senior)
Perimetre : ~100 fichiers produits par 3 agents (backend-developer, frontend-developer, weekly-planner-agent)
Review precedente : scaffold Phase 1 (68/100 initial, 85/100 apres fixes)

---

## Score Phase 1 mature : 76 / 100

Decomposition :
- Securite : 14/20 (rate limiting declare mais jamais applique sur les nouveaux endpoints, SECURITY DEFINER non utilise, contrats frontend/backend desalignes)
- Coherence architecturale : 13/20 (5 desalignements de contrat frontend/backend, SQL sur `re.total_time_min` cible colonne inexistante)
- Qualite code : 18/20 (excellente structure, AAA tests, loguru coherent, docstrings FR)
- Conformite ROADMAP/CLAUDE.md : 16/20 (README WEEKLY_PLANNER present, `run()` conforme, feature flags absents)
- Completude/tests : 15/20 (bonne couverture unitaire, pas de tests d'integration DB reels)

## Score consolide (scaffold + mature) : 80 / 100

---

## Issues CRITIQUES (bloquant le fonctionnement)

### C1 -- Rate limiting absent sur TOUS les nouveaux endpoints
**Fichiers** :
- `apps/api/src/api/v1/households.py` : 0 decorateur `@limiter.limit()`, 0 import de `limiter`
- `apps/api/src/api/v1/plans.py` : `Limiter` importe (ligne 21) mais jamais instancie ni utilise
- `apps/api/src/api/v1/feedbacks.py` : 0 decorateur, 0 import de `limiter`

**Probleme** : Les constantes `LIMIT_USER_READ`, `LIMIT_USER_WRITE`, `LIMIT_LLM_PLAN_USER` sont importees et documentees dans les docstrings OpenAPI, mais **aucun decorateur `@limiter.limit()`** n'est present. Le `default_limits=["300/minute"]` du SlowAPIMiddleware couvre le GET generique, mais le POST /plans/generate (LLM couteux, 10/h/user) n'a AUCUNE limite effective. Un attaquant peut declencher des milliers de generations de plans simultanees, saturant la queue Celery LLM et generant des couts Anthropic illimites.

**Regle violee** : CLAUDE.md -- "Rate limiting sur toutes les API (par tenant et par utilisateur)" (non-negociable).

**Fix** : Ajouter `@limiter.limit(LIMIT_LLM_PLAN_USER, key_func=get_user_key)` sur `generate_plan`, `@limiter.limit(LIMIT_USER_WRITE, key_func=get_user_key)` sur les POST/PATCH, verifier que `limiter` est bien l'instance de `rate_limit.py`.

### C2 -- Households: `create_household_with_owner()` SECURITY DEFINER non appele
**Fichier** : `apps/api/src/api/v1/households.py:120-190`

**Probleme** : Le commentaire ligne 121 dit explicitement `"la fonction SQL SECURITY DEFINER est la cible v1 -- v0 utilise deux INSERTs"`. Or la docstring endpoint (ligne 69) et le module docstring (ligne 9) affirment que `create_household_with_owner` est appele. C'est faux : le code fait 2-3 INSERTs SQL directs. Avec RLS activee sur `households` et `household_members`, ces INSERTs echoueront si la connexion utilise `anon` ou `authenticated` role sans configurer `request.jwt.claims` dans la session Postgres. L'onboarding sera **bloque** en production avec RLS.

**Fix** : Remplacer les INSERTs directs par `SELECT * FROM create_household_with_owner(:name, :user_id::uuid, :display_name)` comme documente dans la migration et le README Phase 0.

### C3 -- Desalignement contrat frontend/backend : 5 incompatibilites
**Fichiers** :
- `apps/web/src/lib/api/endpoints.ts:17-24` vs `apps/api/src/api/v1/schemas/household.py:106-117`
  - Frontend envoie `{ member: {...} }` -- Backend attend `{ first_member: {...} }` (cle differente)
- `apps/web/src/lib/api/endpoints.ts:173` vs `apps/api/src/api/v1/schemas/feedback.py:19`
  - Frontend envoie `feedback_type: "loved" | "ok" | "disliked"` -- Backend attend `"cooked" | "skipped" | "favorited"` (enum completement different)
- `apps/web/src/lib/api/endpoints.ts:37` vs `apps/api/src/api/v1/schemas/household.py:46`
  - Frontend envoie `budget_pref: "low" | "medium" | "high"` -- Backend attend `"economique" | "moyen" | "premium"` (langue differente)
- `apps/web/src/lib/api/endpoints.ts:69-82` vs `apps/api/src/api/v1/schemas/plan.py:16-33`
  - Frontend type `PlanDetail` attend `planned_meals` -- Backend retourne `meals`
- `apps/web/src/lib/api/endpoints.ts:121` : `generatePlan()` envoie `{}` (body vide) -- Backend attend `{ week_start, num_dinners }` (champs obligatoires)

**Impact** : L'onboarding, le feedback, et la generation de plan sont **tous casses** au runtime. Aucune interaction frontend-backend ne fonctionnera sans correction.

**Fix** : Aligner les contrats -- soit le frontend s'adapte, soit le backend ajoute des alias. Recommandation : le backend fait reference, le frontend s'aligne.

### C4 -- SQL invalide dans `recipe_retriever.py` : `re.total_time_min` n'existe probablement pas
**Fichier** : `apps/worker/src/agents/weekly_planner/recipe_retriever.py:264,328`

**Probleme** : La requete SQL filtre sur `re.total_time_min` (alias `re` = `recipe_embeddings`) mais la table `recipe_embeddings` dans la migration initiale ne contient que `(recipe_id, embedding, tags, cuisine_type, total_time_min)`. Si `total_time_min` existe bien sur `recipe_embeddings` (ajoutee dans le UPSERT de `tasks.py:295-306`), la requete fonctionne. MAIS la meme requete utilise aussi `r.total_time_min` (ligne 257) sur la table `recipes` -- or `recipes` ne contient que `prep_time_min` + `cook_time_min` individuellement, pas `total_time_min` en colonne directe. Si `r.total_time_min` n'existe pas, le SELECT echoue avec "column does not exist". A verifier dans la migration.

**Fix** : Remplacer `r.total_time_min` par `(COALESCE(r.prep_time_min, 0) + COALESCE(r.cook_time_min, 0))` ou ajouter une colonne calculee `total_time_min` dans la migration.

---

## Issues HIGH (a fixer avant merge main)

### H1 -- `asyncio.run()` dans Celery : meme pattern casse que la review precedente (H7)
**Fichiers** :
- `apps/worker/src/agents/weekly_planner/tasks.py:98-105`
- `apps/worker/src/agents/recipe_scout/tasks.py:210-217, 331-338, 455-461, 499-507, 560-566`

**Probleme** : Toutes les taches Celery utilisent le pattern `try: asyncio.run() except RuntimeError: new_event_loop()`. Ce pattern est identique a celui signale en H7 de la review precedente. Le fallback `RuntimeError` ne se declenche jamais dans un worker Celery `prefork` (pas d'event loop pre-existante). Si le worker utilise `--pool=gevent` ou `eventlet`, le comportement est imprevisible. Pattern repete 6 fois sans correction.

**Fix** : Creer un helper `run_async_in_celery(coro)` qui gere proprement le cas, ou utiliser `asgiref.sync.async_to_sync`.

### H2 -- Onboarding store : polling sur le mauvais endpoint
**Fichier** : `apps/web/src/stores/onboarding-store.ts:239`

**Probleme** : `pollUntilPlanReady(taskId)` appelle `apiClient.get(/api/v1/plans/${taskId})`. Or `taskId` est un UUID Celery (ex: "celery-task-uuid-test"), PAS un UUID de plan. L'endpoint GET /plans/{plan_id} attend un UUID de `weekly_plans.id`. Le polling retournera systematiquement 404 (plan introuvable).

**Fix** : Soit implementer un endpoint GET /tasks/{task_id}/status (pattern standard async), soit faire le polling via GET /plans/me/current et attendre que le plan apparaisse.

### H3 -- Onboarding store : body creation household desaligne
**Fichier** : `apps/web/src/stores/onboarding-store.ts:138-147`

**Probleme** : Le frontend envoie `{ name: "Mon foyer", member: { display_name: "Moi", is_child: false } }`. Le backend attend `{ name: "...", first_member: { display_name: "...", is_child: ... } }`. Le champ s'appelle `first_member` dans le schema Pydantic `HouseholdCreate`, pas `member`. Reponse attendue : 422 Unprocessable Entity. L'onboarding est bloque a l'etape de creation du foyer.

**Fix** : Renommer `member` en `first_member` dans le body cote frontend.

### H4 -- Callback auth : utilise `getSession()` au lieu de `getUser()`
**Fichier** : `apps/web/src/app/(auth)/callback/route.ts:42`

**Probleme** : Apres l'echange du code PKCE (correct), le callback utilise `supabase.auth.getSession()` (ligne 42) pour recuperer le token d'acces. La review precedente (H4) avait specifiquement signale que `getSession()` ne verifie pas le token cote serveur (risque de session forgee) et qu'il faut utiliser `getUser()`. Ce code le contredit. Le middleware utilise correctement `getUser()`, mais le callback non.

**Fix** : Remplacer par `const { data: { user } } = await supabase.auth.getUser()` et extraire le token depuis la session via un appel separe si necessaire.

### H5 -- Swap meal : aucune verification que `new_recipe_id` existe en DB
**Fichier** : `apps/api/src/api/v1/plans.py:431-448`

**Probleme** : L'UPDATE de `planned_meals` change le `recipe_id` sans verifier que la nouvelle recette existe. Si `new_recipe_id` est un UUID inexistant, l'UPDATE reussit (pas de FK ou FK non activee ?) ou echoue avec IntegrityError non geree. Aucun test ne couvre ce cas.

**Fix** : Ajouter un `SELECT id FROM recipes WHERE id = :new_recipe_id` avant l'UPDATE, ou verifier la FK en base et gerer l'IntegrityError.

### H6 -- Login page : open redirect via `searchParams.get("redirect")`
**Fichier** : `apps/web/src/app/(auth)/login/page.tsx:24`

**Probleme** : `const redirectTo = searchParams.get("redirect") ?? "/dashboard"`. La valeur est utilisee directement dans `emailRedirectTo` (ligne 51). Un attaquant peut forger un lien `/login?redirect=https://evil.com` et le magic link redirigera vers un site malveillant apres l'authentification. Le callback route (route.ts:32) fait un check `redirectTo.startsWith("/")`, mais la page login ne le fait pas avant d'injecter dans `emailRedirectTo`.

**Fix** : Valider que `redirectTo` commence par "/" et ne contient pas "//", ou utiliser une allowlist.

---

## Issues MEDIUM

### M1 -- Plans endpoint : validation plan dans 2 sessions separees (TOCTOU)
**Fichier** : `apps/api/src/api/v1/plans.py:318-365`

Le `validate_plan` fait d'abord un SELECT pour verifier le status (session 1), puis un UPDATE (session 2). Entre les deux, un autre appel peut aussi valider le plan (TOCTOU race condition). L'UPSERT atomique `UPDATE ... WHERE status = 'draft' RETURNING ...` dans une seule session resoudrait cela.

### M2 -- `_denormalize_quantity` : erreur de conversion ml → cl
**Fichier** : `apps/worker/src/agents/weekly_planner/shopping_list_builder.py:161`

`if unit == "ml" and qty_float >= 1000: return f"{qty_float / 100:.2g} cl"` -- Pour 2500 ml, cela donne "25 cl" (faux, devrait etre "2.5 l" ou "250 cl"). La condition `qty_float < 10000` pour le seuil cl/l est arbitraire et incorrecte pour les quantites entre 1000 et 10000 ml.

### M3 -- OFFMapper : session leak dans `_update_off_id`
**Fichier** : `apps/worker/src/agents/recipe_scout/off_mapper.py:213-227`

Chaque appel a `_update_off_id` ouvre une nouvelle session et commit. Si le batch fait 50 ingredients, cela cree 50 sessions separees. Le commit devrait etre fait en batch. De plus, en cas d'erreur, le `async with` ferme la session sans rollback explicite.

### M4 -- Scrapers : `urllib.request` bypass Scrapy settings (meme pattern que M7 precedent)
**Fichiers** :
- `apps/worker/src/agents/recipe_scout/scrapers/cuisine_az.py:537-557`
- `apps/worker/src/agents/recipe_scout/scrapers/allrecipes.py:520-539`

Les methodes `scrape_url()` des wrappers `BaseRecipeScraper` utilisent `urllib.request` directement, bypassing ROBOTSTXT_OBEY, AutoThrottle, et les custom_settings Scrapy. Meme probleme que M7 de la review precedente (Marmiton), replique dans 2 nouveaux scrapers.

### M5 -- `use-plan.ts` : optimistic update avec mauvais champ
**Fichier** : `apps/web/src/hooks/use-plan.ts:100-103`

Le swap met a jour `old.planned_meals` mais le type `PlanDetail` du frontend definit `planned_meals`, tandis que le backend retourne le champ comme `meals`. Si le contrat est corrige pour utiliser `meals`, l'optimistic update cassera.

### M6 -- Login page : import de `Metadata` de next inutilisable dans un Client Component
**Fichier** : `apps/web/src/app/(auth)/login/page.tsx:2`

`import type { Metadata } from "next"` est importe mais inutilisable dans un Client Component (`"use client"`). Les metadonnees doivent etre exportees depuis un fichier `layout.tsx` ou un fichier `metadata.ts` separe.

### M7 -- Weekly planner agent : `_load_members_preferences` en SQL brut
**Fichier** : `apps/worker/src/agents/weekly_planner/agent.py:261-317`

Utilise `text(SQL)` brut avec des colonnes qui dependent de la table `member_preferences`. Si le schema change (ajout de colonnes, renommage), le SQL brut cassera silencieusement. L'agent devrait utiliser les modeles ORM `packages/db` quand disponible.

### M8 -- Tests API : pas de test d'authentification sur les endpoints plans/households
**Fichiers** : `apps/api/tests/api/v1/test_plans.py`, `test_households.py`

Les tests 401 verifient l'absence de token, mais aucun test ne verifie qu'un token invalide (expire, mauvais secret) est correctement rejete. Seul un test verifie le 403 cross-tenant.

---

## Points forts notables

1. **WEEKLY_PLANNER architecture exemplaire** : pipeline clair en 7 etapes, separation propre (constraint_builder, recipe_retriever, plan_selector, shopping_list_builder), methode `run()` unique conforme ROADMAP.

2. **README.md WEEKLY_PLANNER** : documentation complete avec inputs/outputs/effets de bord, tableaux de couts estimes, pipeline visuel, limitations documentees. Reference ROADMAP.

3. **Schemas Pydantic v2 propres** : `ConfigDict(from_attributes=True)`, validateurs `model_post_init` pour week_start, patterns regex pour les enums, types stricts.

4. **Tests AAA exhaustifs** : 40+ tests couvrant les cas nominaux, erreurs, edge cases (422, 401, 403, 404, 409). Fixtures isolees, mocks corrects. Le shopping_list_builder a des tests d'integration avec consolidation verifiee.

5. **Constraint builder : logique UNION/MIN correcte** : les regles d'agregation (allergies = union, temps = min, budget = min semantique) sont bien implementees et testees.

6. **Onboarding store : `partialize` intelligent** : ne persiste pas l'etat "generating" (evite le blocage au refresh), ne persiste pas les tokens.

7. **OpenFoodFacts client robuste** : cache LRU, retry tenacity, throttling respectueux, gestion des generiques (sel, eau), fallback global si pas de resultat local.

8. **Endpoints feedbacks : immutabilite bien pensee** : pas de DELETE/PATCH, journal immuable, le dernier feedback gagne dans l'agregation.

9. **Posthog analytics** : fallback dev console sans clé, lazy import, events types, fail-silent.

10. **Callback auth** : echange PKCE, verification household pour routing intelligent (onboarding vs dashboard), gestion des erreurs de lien expire.

---

## Verdict : GO WITH FIXES

La Phase 1 mature apporte une architecture solide pour WEEKLY_PLANNER et des endpoints bien structures, mais **5 desalignements de contrat frontend/backend** et **l'absence de rate limiting effectif** rendent le systeme non-fonctionnel en l'etat. Les issues C1 (rate limit), C2 (SECURITY DEFINER), C3 (contrats desalignes) et H2 (polling casse) doivent etre corrigees avant tout merge.

**Plan de correction recommande (ordre strict)** :
1. **[30 min]** C3 + H3 -- aligner les contrats frontend/backend (cle `first_member`, enums feedback, budget_pref, `meals` vs `planned_meals`, body `generatePlan`)
2. **[30 min]** C1 -- ajouter `@limiter.limit()` sur les 8 endpoints sans rate limit
3. **[30 min]** C2 -- remplacer les INSERTs par `SELECT create_household_with_owner()`
4. **[30 min]** C4 -- corriger `r.total_time_min` en expression calculee
5. **[30 min]** H2 + H4 + H6 -- polling endpoint, `getUser()` dans callback, validation redirect
6. **[30 min]** H5 + M1 -- verification existence recette swap, TOCTOU validation plan
7. **[15 min]** H1 -- extraire helper `run_async_in_celery()` (6 occurrences)

**Apres correction**, score projete : **88/100** (consolide scaffold + mature).

---

## Resume executif (< 300 mots)

**Top 5 issues :**

1. **C3 -- Contrats frontend/backend desalignes (5 incompatibilites)** : Le frontend et le backend ont ete developpes sans contrat d'interface partage. Les cles JSON (`member` vs `first_member`), les enums (`loved` vs `cooked`), les valeurs (`low` vs `economique`), les champs de reponse (`planned_meals` vs `meals`) et les body de requete (body vide vs `week_start` requis) ne matchent pas. L'onboarding, le feedback et la generation de plan sont tous casses au runtime.

2. **C1 -- Rate limiting non applique** : Les 8 nouveaux endpoints importent les constantes de limite mais aucun n'applique de decorateur. Le POST /plans/generate (LLM couteux) est completement ouvert -- un attaquant peut generer des couts Anthropic illimites. Regle CLAUDE.md non-negociable violee.

3. **C2 -- SECURITY DEFINER non utilise** : La creation de foyer fait des INSERTs SQL directs au lieu d'appeler `create_household_with_owner()`. Avec RLS activee en production, l'onboarding sera bloque.

4. **H2 -- Polling casse** : L'onboarding poll sur `/plans/${taskId}` ou `taskId` est un ID Celery, pas un ID de plan. Retournera 404 systematiquement.

5. **H6 -- Open redirect login** : Le parametre `redirect` n'est pas valide cote login, permettant une redirection vers un site externe apres authentification.

**Verdict** : **GO WITH FIXES** -- l'architecture est solide (WEEKLY_PLANNER exemplaire, tests AAA complets, schemas Pydantic propres) mais les 3 agents n'ont pas partage de contrat d'interface, ce qui produit des incompatibilites runtime bloquantes. Correction estimee : 3h de travail cible. Score consolide projete apres fixes : **88/100**.
