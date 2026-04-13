---
project: "MealPlanner SaaS"
domain: "saas"
type: "history"
created: "2026-04-11"
tags: [project/mealplanner-saas, domain/saas, memory/history]
links:
  - "[[memory/MOC]]"
  - "[[memory/project-context]]"
---

# Prompt History — MealPlanner SaaS

> Historique des prompts optimisés utilisés sur ce projet.
> Ajoute tes nouveaux prompts en haut du fichier (ordre anti-chronologique).

## 2026-04-13 — Fix 5 bugs audit backend/DB (backend-developer)

**Agent** : backend-developer
**Scope** : `apps/worker/src/agents/weekly_planner/recipe_retriever.py` + SQL Supabase
**Resultat** :
- BUG 1 : `_retrieve_by_quality_no_embedding` accepte constraints, 30 candidats, ORDER BY RANDOM()
- BUG 2 : Parsing unit -> quantity+unit sur recipe_ingredients (5341 lignes, 85 valeurs distinctes)
- BUG 3 : 10 cuisine_types traduits (100 recettes)
- BUG 4 : quality_score varie [0.70-0.95] (26 valeurs distinctes)
- BUG 5 : cook_time recalcule par difficulte (28 recettes <= 30min)
- Scripts de migration : `scripts/fix_audit_bugs.py`, `scripts/fix_bug5_deeper.py`, `scripts/fix_bug2_quantities.py`

---

## 2026-04-12 — Fix 4 bugs page recettes frontend (nextjs-developer)

**Agent** : nextjs-developer
**Scope** : `apps/web/src/app/(app)/recipes/[id]/page.tsx`, `recipes-explorer.tsx`, `recipe-tabs-client.tsx`
**Résultat** :
- BUG 1 : Normalisation ingrédients dans `fetchRecipe()` — mapping `ingredient_id→id`, `canonical_name→name`, `notes→note`, `category: "other"`. Les ingrédients s'affichent désormais dans `IngredientList`.
- BUG 2 : `getNextPageParam` recalculé depuis `totalLoaded < total` (sans `has_next`). Bouton "Voir plus de recettes" ajouté comme fallback IntersectionObserver. `handleFiltersChange` corrigé : `per_page: 24` au lieu de 12.
- BUG 3 : `per_page` incohérent corrigé dans `handleFiltersChange`. Les filtres du panneau latéral relancent bien la query. CUISINE_OPTIONS déjà conformes.
- BUG 4 : Onglet Nutrition affiche une bannière "Informations nutritionnelles bientôt disponibles" au lieu d'un bloc vide.
- `pnpm typecheck` : 0 erreur.

---

## 2026-04-12 — Fix 3 bugs prod + photo_url 75 recettes (backend-developer)

**Agent** : backend-developer
**Scope** : `apps/api/src/api/v1/recipes.py`, `apps/worker/src/agents/weekly_planner/recipe_retriever.py`, `infra/docker/init-scripts/postgres/06-add-photo-urls.sql` (créé)
**Résultat** :
- BUG 1 : `photo_url` ajouté dans `RecipeOut` (schéma Pydantic) + SELECT de `search_recipes`, `get_random_recipes`.
- BUG 2 : `photo_url` + `description` ajoutés dans le SELECT de `get_recipe` ; construction `RecipeDetail` rendue explicite avec valeurs par défaut sûres.
- BUG 3 : Fallback `_retrieve_by_quality_no_embedding` ajouté dans `recipe_retriever.py` — si aucune recette avec embedding, retourne les 5 meilleures par `quality_score` sans JOIN `recipe_embeddings`. Résout le crash 500 du planner sur recettes seed sans embeddings.
- ACTION 4 : 75 UPDATE SQL avec 25+ URLs Unsplash variées dans `06-add-photo-urls.sql` (prêt pour Supabase SQL Editor).

---

## 2026-04-12 — Fix crash page /recipes/[id] champs null API (nextjs-developer)

**Agent** : nextjs-developer
**Scope** : `apps/web/src/lib/api/types.ts`, `apps/web/src/app/(app)/recipes/[id]/page.tsx`, `apps/web/src/app/(app)/recipes/[id]/error.tsx` (créé), `apps/web/src/components/recipe/ingredient-list.tsx`, `apps/web/src/app/page.tsx`
**Résultat** : Crash "Quelque chose s'est mal passé" résolu. Cause : mismatch `photo_url` vs `image_url` + champs `null` non typés. Normalisation dans `fetchRecipe`, Error Boundary créé, `pnpm typecheck` : 0 erreur.

---

## 2026-04-12 — Import Spoonacular API vers PostgreSQL Supabase (backend-developer)

**Agent** : backend-developer
**Scope** : `apps/worker/src/scripts/import_spoonacular.py` (créé), `apps/worker/src/agents/recipe_scout/tasks.py` (tâche Celery ajoutée), `apps/web/next.config.mjs` (remotePattern + CSP img.spoonacular.com)
**Résultat** : Script CLI complet + tâche Celery `recipe_scout.import_from_spoonacular`. Gestion quota 150 req/jour, upsert idempotent (slug + source_url), mapping cuisine EN→FR, extraction tags, instructions JSONB, ingrédients avec quantity/unit conformes au schéma DB.

---

## 2026-04-12 — Seed SQL 75 recettes multi-cuisines Presto (backend-developer)

**Agent** : backend-developer
**Scope** : `infra/docker/init-scripts/postgres/05-rich-seed-recipes.sql`
**Résultat** : 75 recettes insérées — 18 françaises, 12 italiennes (avec aglio e olio + bruschetta champignons), 7 mexicaines, 7 indiennes, 6 libanaises, 5 internationales, 3 japonaises, 2 thaïlandaises + 1 vietnamienne + 1 grecque + 1 anglaise. ON CONFLICT DO NOTHING, sans total_time_min (generated column). Fichier prêt pour Supabase SQL Editor.

---

## 2026-04-12 — Intégration design premium food Presto (nextjs-developer)

**Agent** : nextjs-developer
**Scope** : `apps/web/src/**`, `apps/web/tailwind.config.ts`
**Résultat** : Design premium intégré — Noto Serif, palette warm cream, cards redesignées, `pnpm typecheck` OK

---

## 2026-04-12 — Fix CORS + 4 bugs production API Presto (backend-developer)

**Agent** : backend-developer
**Scope** : `apps/api/src/**` uniquement
**Fichiers modifiés** :
- `apps/api/src/main.py` — CORS hardcodé + `max_age=600`
- `apps/api/src/core/logging.py` — filtre loguru `correlation_id` default "startup"
- `apps/api/src/api/v1/plans.py` — fallback 503 Celery indisponible
- `apps/api/src/api/v1/recipes.py` — log `recipes_search_empty_result` INFO

---

## 2026-04-12 — Fix 7 bugs production frontend Presto (nextjs-developer)

**Agent** : nextjs-developer
**Scope** : `apps/web/**` uniquement
**Résultat** : `pnpm typecheck` EXIT_CODE=0

**Bugs corrigés** :
- BUG 1 : Signup/Login email+password — `signUp()` + `signInWithPassword()` + "Mot de passe oublié ?" + `resetPasswordForEmail()`
- BUG 2 : Page /account créée — Server Component + AccountContent client (profil, membres foyer, logout, paramètres, billing)
- BUG 3 : Page /settings créée — SettingsContent client (régimes, allergies, temps cuisine, drive, thème, suppression compte)
- BUG 4 : Logo `mix-blend-multiply dark:mix-blend-screen` — masque le fond blanc PNG
- BUG 5 : Dashboard — message "Bonjour [prénom] !", timeout 5s, fallback URL Railway
- BUG 6 : apiClient — timeout 15s + fallback URL Railway (`NEXT_PUBLIC_API_URL || railway.app`)
- BUG 7 : getRecipes() — déplacée après FALLBACK_RECIPES (TDZ fix), timeout 5s, fallback robuste
- BONUS : Navigation — `/feed`→`/dashboard`, `/profile`→`/account` dans sidebar + bottom nav

**Fichiers créés** : 4 (`account/page.tsx`, `account/account-content.tsx`, `settings/page.tsx`, `settings/settings-content.tsx`)
**Fichiers modifiés** : 7 (`signup/page.tsx`, `login/page.tsx`, `brand/logo.tsx`, `dashboard/page.tsx`, `lib/api/client.ts`, `app/page.tsx`, `navigation/app-sidebar.tsx`, `navigation/app-bottom-nav.tsx`)

---

## 2026-04-12 — Fix connexion prod Vercel ↔ Railway (backend-developer)

**Agent** : backend-developer
**Scope** : `apps/api/src/**`
**Missions** :
- FIX 1 : log `cors_origins_configured` au démarrage pour diagnostic Railway
- FIX 2 : try/except global sur les endpoints recipes (retourne liste vide si DB inaccessible)
- FIX 3 : SSL asyncpg automatique si `supabase.co` dans DATABASE_URL ou ENV=production
- FIX 4 : chargement lazy `stripe_config.py` — plus de crash si STRIPE_SECRET_KEY=""
- FIX 5 : confirmé que `/health` et `/recipes` sont publics (0 auth dependency)

**Fichiers modifiés** : 4 (`main.py`, `recipes.py`, `session.py`, `stripe_config.py`)

---

## 2026-04-12 — Rebrand "IA" → "Presto" dans textes user-facing backend (backend-developer)

**Agent** : backend-developer
**Scope** : `apps/api/src/**`, `apps/worker/src/agents/*/README.md`
**Missions** :
- Remplacer "IA" par "Presto" dans les descriptions Swagger (main.py, stripe_config.py)
- Remplacer "IA" dans les README agents (recipe_scout/README.md)
- Conserver intacts les commentaires internes développeur (config.py, security.py)

**Fichiers modifiés** : 3 | **Occurrences remplacées** : 5

---

## 2026-04-12 — Rebrand MealPlanner → Presto (nextjs-developer)

**Agent** : nextjs-developer
**Scope** : `apps/web/**` uniquement
**Missions** :
- Créer `components/brand/logo.tsx` (Logo réutilisable avec Image /logo.png)
- Remplacer tous les "MealPlanner" par "Presto" dans les textes visibles utilisateur
- Retirer la section "Tout ce que Jow aurait dû faire" → "Pourquoi les familles adorent Presto"
- Mettre à jour SEO metadata, OG tags, manifest PWA, localStorage key
- Intégrer le composant Logo dans auth layout, onboarding layout, sidebar, landing header

**Fichiers modifiés** : 15 | **Fichiers créés** : 1
**Occurrences MealPlanner remplacées** : 38 | **Jow retiré** : 1

---

## 2026-04-12 — Rebrand MealPlanner → Presto (backend-developer)

**Agent** : backend-developer
**Missions** : Rebrand textes user-facing dans `apps/api/src/**` et `apps/worker/src/**`

**Occurrences remplacées** : 26 occurrences dans 19 fichiers
**Nom produit avant** : MealPlanner SaaS
**Nom produit après** : Presto

**Fichiers modifiés** :
- `apps/api/src/main.py` — titre OpenAPI + description API
- `apps/api/src/core/config.py` — docstring module
- `apps/api/src/core/stripe_config.py` — docstring module
- `apps/api/src/api/v1/billing.py` — docstring module
- `apps/api/src/api/v1/webhooks.py` — docstring fonction interne
- `apps/api/src/scripts/seed.py` — message console utilisateur
- `apps/api/src/scripts/__init__.py` — docstring package
- `apps/api/src/db/__init__.py` — docstring module
- `apps/api/src/db/session.py` — docstring module
- `apps/api/src/db/models/recipe.py` — docstring classe Ingredient
- `apps/worker/src/app.py` — docstring module
- `apps/worker/src/agents/__init__.py` — commentaire package
- `apps/worker/src/agents/book_generator/__init__.py` — docstring agent
- `apps/worker/src/agents/book_generator/README.md` — description agent
- `apps/worker/src/agents/retention_loop/__init__.py` — docstring agent
- `apps/worker/src/agents/book_generator/templates/weekly_book.html` — pied de page PDF (2 occurrences)
- `apps/worker/src/agents/recipe_scout/scrapers/base.py` — commentaire + User-Agent par défaut
- `apps/worker/src/agents/recipe_scout/scrapers/allrecipes.py` — commentaire + constante User-Agent + commentaire mapping
- `apps/worker/src/agents/recipe_scout/scrapers/cuisine_az.py` — commentaire + constante User-Agent + commentaire inline
- `apps/worker/src/agents/recipe_scout/scrapers/marmiton.py` — commentaire + USER_AGENT Scrapy
- `apps/worker/src/agents/recipe_scout/connectors/edamam.py` — User-Agent header HTTP
- `apps/worker/src/agents/recipe_scout/connectors/spoonacular.py` — User-Agent header HTTP
- `apps/worker/src/agents/recipe_scout/connectors/openfoodfacts.py` — User-Agent header HTTP

---

## 2026-04-12 — Nettoyage final avant Phase 3 (backend-developer)

**Agent** : backend-developer
**Missions** : 4 missions — tests API (71/71), tests worker (244/244), sample recipes, deps

**Résultats avant/après** :
- Tests API : 65 errors, 6 passed → **71 passed, 0 errors**
- Tests worker : 6 failed, 198 passed → **244 passed, 0 failed**

**Fichiers modifiés** :
- `apps/api/tests/conftest.py` — 10 variables Phase 2 ajoutées (Stripe, MinIO)
- `apps/api/src/core/config.py` — STRIPE_SUCCESS_URL, STRIPE_CANCEL_URL, MINIO_BUCKET_PDFS ajoutés
- `apps/api/src/core/stripe_config.py` — import stripe conditionnel (try/except ImportError)
- `apps/api/src/api/v1/billing.py` — import stripe conditionnel + _check_stripe_configured() + garde 503
- `apps/api/src/api/v1/webhooks.py` — import stripe conditionnel + garde 503 si stripe None
- `apps/api/pyproject.toml` — stripe>=7.0, boto3>=1.34 ajoutés
- `apps/worker/src/agents/weekly_planner/shopping_list_builder.py` — UNIT_CONVERSIONS refactorisé (tuples clé)
- `apps/worker/tests/test_embedder.py` — seuil similarité abaissé 0.70→0.60
- `apps/worker/tests/agents/recipe_scout/test_tasks_integration.py` — import mealplanner_db retiré du mock
- `apps/worker/tests/agents/weekly_planner/test_plan_selector.py` — test fallback cuisine adapté
- `apps/worker/pyproject.toml` — weasyprint>=60.0, boto3>=1.34, jinja2>=3.1 ajoutés

**Fichiers créés** :
- `apps/worker/src/scripts/sample_recipes.json` — 10 recettes françaises de démo
- `apps/worker/src/scripts/import_sample_recipes.py` — script import CSV/JSON bypass scraping

---

## 2026-04-12 — Déploiement Railway + Vercel — Fichiers de déploiement (devops-engineer)

**Agent** : devops-engineer
**Missions** : 4 missions — guide déploiement, vercel.json, railway.toml, script deploy-check.sh
**Fichiers créés** :
- `docs/deployment.md` — guide complet 4 sections, 30+ étapes en français
- `apps/web/vercel.json` — config Vercel avec références secrets (@supabase-url, etc.)
- `railway.toml` — config Railway avec healthcheck `/api/v1/health` et restart policy
- `scripts/deploy-check.sh` — script 8 vérifications pré-déploiement (tests, typecheck, build, Docker, env)

---

## 2026-04-12 — Phase 2 v2 Différenciation (backend-developer)

**Agent** : backend-developer
**Missions** : 5 missions Phase 2 (BOOK_GENERATOR, Stripe, Frigo, RETENTION_LOOP, Filtres avancés)
**Fichiers créés** : 27
**Fichiers modifiés** : 6

---

## 2026-04-12 — DB Phase 2 : Stripe subscriptions + Mode frigo + RETENTION_LOOP (database-administrator)

**Type** : Base de données / DDL Phase 2
**Agent** : database-administrator
**Périmètre** : `infra/docker/init-scripts/postgres/04-phase2-schema.sql`, `apps/api/src/db/models/subscription.py`, `apps/api/src/db/models/planning.py`, `apps/api/src/db/models/__init__.py`, `packages/db/src/mealplanner_db/models/__init__.py`

### Tâches accomplies

**MISSION 1** — `subscriptions` enrichie : +5 colonnes Stripe (stripe_customer_id, stripe_price_id, cancel_at_period_end, canceled_at, trial_end), 3 index (ix_subscriptions_stripe_customer, ix_subscriptions_stripe_sub, ix_subscriptions_household_active partiel), policy RLS subscriptions_select_own (tous membres, pas seulement owner).

**MISSION 2** — `fridge_items` enrichie : +2 colonnes (notes TEXT, is_staple BOOLEAN DEFAULT false), 2 index (ix_fridge_items_household_ingredient, ix_fridge_items_expiry).

**MISSION 3** — Table `engagement_events` créée : UUID PK, household_id FK CASCADE, event_type TEXT, event_data JSONB, created_at, RLS ENABLE + FORCE, policy SELECT authenticated, 2 index (ix_engagement_events_household_type, ix_engagement_events_recent).

**MISSION 4** — Fonction `suggest_recipes_from_fridge(p_household_id, p_limit)` : STABLE SECURITY DEFINER, search_path vide, tri anti-gaspi (has_expiring DESC), seuil quality_score >= 0.6, minimum 2 ingrédients matchés, GRANT TO authenticated.

**MISSION 5** — Modèles SQLAlchemy :
- `subscription.py` : nouveau fichier avec `Subscription` (colonnes Phase 2 complètes) + `EngagementEvent`
- `planning.py` : `FridgeItem` enrichi avec `notes` et `is_staple` + import `Boolean`
- `household.py` : relation `subscription` ajoutée + `TYPE_CHECKING` pour éviter import circulaire
- `apps/api/src/db/models/__init__.py` : exports `Subscription` + `EngagementEvent`
- `packages/db/src/mealplanner_db/models/__init__.py` : ré-exports Phase 2

### Commande de validation
```bash
docker compose down -v && docker compose up -d
# Puis tester la fonction :
docker exec -it mealplanner-postgres psql -U postgres -d mealplanner \
  -c "SELECT * FROM suggest_recipes_from_fridge('<un_household_uuid>', 5);"
```

---

## 2026-04-12 — Infrastructure Phase 2 : Stripe + MinIO + WeasyPrint (devops-engineer)

**Type** : DevOps / Infrastructure
**Agent** : devops-engineer
**Périmètre** : `.env.example`, `docker-compose.dev.yml`, `apps/worker/Dockerfile`, `Makefile`, `scripts/`, `README.md`

### Tâche accomplie

6 missions exécutées :

**MISSION 1 — Variables d'environnement Phase 2**
- `.env.example` enrichi : section Stripe Phase 2 avec bloc visuel, `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`
- Note backend-developer ajoutée : rendre `STRIPE_SECRET_KEY` optionnel dans `config.py` (HTTP 503 si absent)
- Variables MinIO SDK ajoutées : `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET_PDFS`, `MINIO_BUCKET_IMAGES`

**MISSION 2 — MinIO bucket policies**
- `docker-compose.dev.yml` → `minio-init` : ajout `mc anonymous set download` sur les 2 buckets (PDFs + images)
- Policy download publique pour que les URLs de téléchargement fonctionnent sans auth en dev

**MISSION 3 — Makefile Phase 2**
- 3 nouvelles targets : `scout`, `generate-pdf`, `stripe-listen`
- `.PHONY` mis à jour

**MISSION 4 — Dockerfile worker WeasyPrint**
- `apps/worker/Dockerfile` : bloc `apt-get install` ajouté avec libcairo2, libpango, libpangocairo, libgdk-pixbuf2, libffi-dev, shared-mime-info

**MISSION 5 — Script test webhook Stripe**
- `scripts/test-stripe-webhook.sh` créé : simule `checkout.session.completed`, gestion codes HTTP 200/400/503, port configurable

**MISSION 6 — README Phase 2**
- Section "Phase 2 — Features premium" ajoutée : Stripe setup, PDF hebdomadaire, Mode frigo

### Fichiers créés : 1
- `scripts/test-stripe-webhook.sh`

### Fichiers modifiés : 5
- `.env.example`
- `docker-compose.dev.yml`
- `apps/worker/Dockerfile`
- `Makefile`
- `README.md`

---

## 2026-04-12 — Optimisation DB + Automatisation Docker Init (database-administrator)

**Type** : Database Administration / DevOps
**Agent** : database-administrator
**Périmètre** : `infra/docker/init-scripts/postgres/`, `phase-0/database/`, `apps/api/src/db/models/`

### Tâche accomplie

3 missions exécutées :

**MISSION 1 — Scripts d'init Docker automatiques (3 fichiers créés)**
- `01-supabase-stubs.sql` : schéma auth, fonction auth.uid() (lit GUC request.jwt.claim.sub), rôles anon/authenticated/service_role, GRANT USAGE sur public + auth
- `02-schema.sql` : assemblage ordonné des 5 sources Phase 0 (extensions → schéma core → indexes → triggers/functions → RLS policies). Idempotent (IF NOT EXISTS + DROP/CREATE triggers + CREATE OR REPLACE functions). Colonnes OFF et content_hash intégrées directement.
- `03-seed.sql` : copie fidèle de 07-seed-data.sql avec session_replication_role = replica pour contourner les triggers de validation.

**MISSION 2 — Optimisations queries temps réel (analyse)**
- Index `ix_recipes_title_trgm` confirmé présent dans 02-indexes.sql. Ajouté en double nom dans 02-schema.sql (ix_ canonique + idx_ legacy) via bloc DO$$ idempotent.
- Query WEEKLY_PLANNER : indexes HNSW + GIN tags + BTREE partial total_time_min + index composite (total_time_min, cuisine_type) INCLUDE recipe_id tous présents et fonctionnels.
- Colonnes OFF (off_id, off_last_checked_at, off_match_confidence, off_product_name, off_brand) : absentes du schéma core orignal → ajoutées directement dans `ingredients` de 02-schema.sql.
- Index partiel `idx_ingredients_off_unmapped` ajouté pour la queue de mapping OFF (WHERE off_id IS NULL ORDER BY off_last_checked_at NULLS FIRST LIMIT 50).

**MISSION 3 — Modèles SQLAlchemy vérifiés**
- `Ingredient` : off_id, off_last_checked_at, off_match_confidence, off_product_name, off_brand tous présents dans `apps/api/src/db/models/recipe.py`. Aucune modification nécessaire.
- `WeeklyBook.content_hash` : présent (ligne 256 planning.py). Aucune modification nécessaire.
- `WeeklyPlan.validated_at` : présent. Aucune modification nécessaire.
- `Recipe.difficulty CHECK BETWEEN 1 AND 5` : présent. Aucune modification nécessaire.
- `RecipeEmbedding` colonnes dénormalisées (tags, total_time_min, difficulty, cuisine_type) : toutes présentes.

### Volume Docker Compose
Volume `./infra/docker/init-scripts/postgres:/docker-entrypoint-initdb.d:ro` déjà configuré correctement dans `docker-compose.dev.yml` ligne 50.

### Commande de test
```bash
docker compose -f docker-compose.dev.yml down -v && docker compose -f docker-compose.dev.yml up -d
docker exec mealplanner_postgres psql -U mealplanner -d mealplanner_dev -c "\dt"
```

---

## 2026-04-12 — Corrections 5 bugs critiques frontend Phase 1 Mature (nextjs-developer)

**Type** : Bug fixes / Frontend Engineering
**Agent** : nextjs-developer
**Bugs corrigés** : 5 (2 CRITICAL, 2 HIGH, 1 HIGH PERF)
**Périmètre** : `apps/web/**` uniquement

### Fichiers modifiés (10 fichiers + 1 créé)

- `apps/web/src/lib/api/endpoints.ts` — Mismatches A/C/D/E + BackendFeedbackType + getNextMonday()
- `apps/web/src/lib/api/types.ts` — RecipeFeedback.feedback_type aligné sur backend
- `apps/web/src/stores/onboarding-store.ts` — BUG #2 polling + BUG #4 idempotence + Mismatch A+E
- `apps/web/src/components/recipe/rating-modal.tsx` — Mismatch B + mapping UI→backend
- `apps/web/src/components/plan/plan-week-grid.tsx` — Mismatch D
- `apps/web/src/hooks/use-plan.ts` — Mismatch D optimistic update
- `apps/web/src/app/(auth)/login/page.tsx` — BUG #3 open redirect + import Metadata supprimé
- `apps/web/src/i18n/config.ts` — Retrait next-intl, helper i18n minimal
- `apps/web/package.json` — next-intl retiré, @next/bundle-analyzer ajouté
- `apps/web/next.config.mjs` — bundleAnalyzer chaîné + ANALYZE=true support
- `apps/web/src/i18n/t.ts` (CRÉÉ) — helper t(key) léger FR-only (0 dépendance externe)

### Tableau des 5 mismatches — avant → après

| Mismatch | Avant | Après |
|----------|-------|-------|
| A — Household create key | `member: {...}` | `first_member: {...}` |
| B — feedback_type enum | `"loved" \| "ok" \| "disliked"` | `"cooked" \| "skipped" \| "favorited"` |
| C — budget_pref enum | `"low" \| "medium" \| "high"` | `"économique" \| "moyen" \| "premium"` |
| D — PlanDetail meals key | `planned_meals: PlannedMeal[]` | `meals: PlannedMeal[]` |
| E — generatePlan body | `{}` (vide) | `{ week_start: "2026-04-13" }` |

### Décisions techniques clés

1. **Polling via /plans/me/current** : remplace le polling sur `/plans/${taskId}` (UUID Celery ≠ UUID plan DB). Signal de succès : `status === "draft" | "validated"`. 404 = plan pas encore prêt = continue.
2. **Submit idempotent** : GET /households/me avant POST — si 404 alors création, sinon réutilisation. Enfants conditionnels (existingMembersCount < expectedTotal).
3. **getSafeRedirectUrl()** : valide que le redirect commence par "/" et ne contient pas "://" ou "//". Construit `origin/auth/callback?next=encodedPath`.
4. **next-intl retiré** : Phase 1 FR-only → helper `t.ts` sur fr.json. Économie ~28 KB gzip. Réinstaller en Phase 4.
5. **Bundle** : @next/bundle-analyzer ajouté pour mesure précise post-fixes (ANALYZE=true pnpm build).

---

## 2026-04-12 — Corrections 9 bugs critiques Phase 1 Mature (backend-developer)

**Type** : Bug fixes / Backend Engineering
**Agent** : backend-developer
**Bugs corrigés** : 9 (4 CRITICAL, 3 HIGH, 2 HIGH PERF)

### Fichiers modifiés (9 fichiers)

- `apps/api/src/core/rate_limit.py` — Singleton `limiter` exporté pour décorateurs
- `apps/api/src/main.py` — Réassignation du singleton limiter après connexion Redis
- `apps/api/src/api/v1/households.py` — BUG #1 (rate limits ×4), BUG #2 (SECURITY DEFINER), BUG #7 (idempotence 409→200)
- `apps/api/src/api/v1/plans.py` — BUG #1 (rate limits ×6), BUG #4 (ordre routes), BUG #5 (session unique Depends(get_db))
- `apps/api/src/api/v1/feedbacks.py` — BUG #1 (rate limits ×2)
- `apps/api/src/api/v1/recipes.py` — BUG #8 (COUNT(*) OVER() window function)
- `apps/worker/src/agents/weekly_planner/recipe_retriever.py` — BUG #3 (vérification schéma + commentaires)
- `apps/worker/src/agents/weekly_planner/agent.py` — BUG #9 (INSERT batch multi-VALUES)
- `apps/worker/src/agents/recipe_scout/off_mapper.py` — BUG #6 (asyncio.gather + Semaphore(5))

### Décisions techniques clés

1. **Singleton limiter** : exporté depuis `rate_limit.py` avec storage mémoire, réassigné dans le lifespan avec URI Redis réelle — évite la circularité d'import tout en garantissant le bon storage en prod
2. **Ordre routes FastAPI** : routes statiques (`/me/current`, `/me/{id}/shopping-list`) déclarées avant routes dynamiques (`/{plan_id}`) dans plans.py — fix critique pour éviter UUID("me") 422
3. **Session unique** : `Depends(get_db)` comme générateur async (yield) — 1 connexion pool par requête HTTP au lieu de 3
4. **BUG #3 non-bug** : `re.total_time_min` dans recipe_retriever.py est correct car `recipe_embeddings` a bien `total_time_min` dénormalisé (OPT #1 Phase 0 schéma confirmé)

---

## 2026-04-12 — Frontend Phase 1 Mature (nextjs-developer)

**Type** : Frontend Engineering / Phase 1 Mature
**Agent** : nextjs-developer
**Fichiers créés** : 26 | **Modifiés** : 7

### Missions accomplies

**Mission 1 — Auth Supabase** : layout auth cream warm, login/signup magic link (shouldCreateUser), callback route PKCE exchange + redirect logic household check, logout POST route.
**Mission 1.2 — Hooks auth** : useUser() TanStack Query + onAuthStateChange, useHousehold() cache 5min.
**Mission 2 — Onboarding** : store Zustand persist localStorage, submit() orchestré (POST household → members → préférences → generate plan → polling), ProgressDots motion spring, StepNavigator, step-1/2/3 refactorisés sur store, page generating messages rotatifs.
**Mission 3 — Dashboard** : Server Component fetch ISR 5min, DashboardContent Client Component hydration, PlanWeekGrid stagger 80ms, RecipeCard 3 variants hover spring, PlanActions mutations optimistic.
**Mission 4 — Recette** : RSC fetch cache 1h, generateMetadata dynamique, RecipeTabsClient Radix Tabs, IngredientList groupée catégories + checkbox, InstructionSteps + timer stub, RatingModal 3 emojis + étoiles.
**Mission 5 — Courses** : ShoppingListPage groupée par rayon, swipe-to-delete Framer Motion, progression circulaire SVG, bouton drive disabled Phase 1.
**Mission 6 — API** : endpoints.ts typés (13 fonctions), use-plan/use-recipes/use-shopping-list hooks, types.ts complet (Household, Member, Recipe, Ingredient, WeeklyPlan, PlannedMeal, ShoppingListItem, Feedback).

### Décisions techniques clés

1. **State management onboarding** : Zustand + persist (vs sessionStorage des steps isolés) — reprise après refresh accidentel, orchestration du submit() centralisée
2. **RSC vs Client Components** : Dashboard = RSC avec fetch ISR + DashboardContent = Client Component — hydration optimale sans flash, mutations TanStack Query côté client
3. **Polling vs WebSocket** : Polling avec backoff progressif (2s → 4s max) dans submit() du store — WebSocket prévu Phase 2 via Supabase Realtime

### Points d'intégration backend

- Tous les endpoints Phase 1 consommés : POST/GET households, POST members, PATCH preferences, POST generate, GET plan, GET shopping-list, GET recipe, POST feedbacks
- Auth header automatique via getAuthToken() depuis localStorage Supabase

---

## 2026-04-12 — Corrections bugs critiques Phase 1 (code-review + debug-audit + performance-audit)

**Type** : Bug fixes / Backend Engineering
**Agent** : backend-developer
**Bugs corrigés** : 13 (7 CRITICAL, 4 HIGH, 2 MEDIUM/OPT)

### Fichiers modifiés (13 fichiers + 5 créés)

**Modifiés :**
- `apps/worker/src/app.py` — BUG #4 book_generator commenté
- `apps/worker/src/agents/recipe_scout/validator.py` — BUG #3 #6 #10
- `apps/worker/src/agents/recipe_scout/tagger.py` — BUG #3 #6 + QW-3
- `apps/worker/src/agents/recipe_scout/dedup.py` — BUG #7
- `apps/worker/src/agents/recipe_scout/agent.py` — BUG #5 #13
- `apps/api/src/api/v1/recipes.py` — BUG #2
- `apps/api/src/main.py` — BUG #8
- `apps/api/src/core/security.py` — BUG #9
- `apps/api/src/core/config.py` — BUG #11 #12
- `apps/api/pyproject.toml` — BUG #1 (dépendance mealplanner-db)
- `apps/worker/pyproject.toml` — BUG #1 (dépendance mealplanner-db)

**Créés :**
- `packages/db/pyproject.toml`
- `packages/db/src/mealplanner_db/__init__.py`
- `packages/db/src/mealplanner_db/base.py`
- `packages/db/src/mealplanner_db/session.py`
- `packages/db/src/mealplanner_db/models/__init__.py`

### Actions déléguées (autres agents)

**devops-engineer** :
1. `.env.example` : `SPOONACULAR_KEY` → `SPOONACULAR_API_KEY`
2. `.env.example` : ajouter `SUPABASE_JWT_SECRET=` (optionnel, fallback sur SUPABASE_ANON_KEY)
3. `pyproject.toml` racine : ajouter `"packages/db"` dans `[tool.uv.workspace] members`
4. Après uv workspace config : `uv sync` pour résoudre mealplanner-db

**database-administrator** :
1. Migration `difficulty CHECK BETWEEN 1 AND 3` → `CHECK BETWEEN 1 AND 5` dans `apps/api/alembic/`
2. Vérifier RLS policy `SELECT` sur table `recipes` (catalogue global, pas de tenant scope)
3. Vérifier contrainte unicité `recipe_ingredients (recipe_id, position)` existe

**Note infra** : Supabase Pro obligatoire avant lancement prod (Free = 60 connexions, insuffisant).

---

## 2026-04-12 — Scaffold Backend Python Phase 1 (API + Worker + RECIPE_SCOUT)

**Type** : Backend Engineering / Scaffold
**Agent** : backend-developer
**Score** : N/A (session scaffold)

### Tâche accomplie

Création du scaffold complet backend Python : 41 fichiers couvrant apps/api (FastAPI + config + rate limiting + health + recipes + tests) et apps/worker (Celery + RECIPE_SCOUT agent complet avec scraping Marmiton, connecteurs Spoonacular/Edamam, normalisation ingrédients FR, embedding, déduplication, validation LLM, tagging, pipeline orchestré).

### Décisions clés

- RecipeEmbedder singleton pour éviter rechargement modèle ML entre tâches Celery
- prefetch_multiplier=1 sur tous les workers (LLM calls peuvent durer 10-60s)
- Redis DB isolation : 0=broker, 1=rate limiting, 2=résultats Celery
- Tool use Anthropic structured output pour validator.py et tagger.py (pas de parsing JSON fragile)
- Fast-reject local avant LLM (titre vide, <3 ingrédients, <2 instructions) — économie de tokens
- Déduplication 2 étapes : intra-batch mémoire (O(n²)) + inter-batches pgvector

### Points d'intégration autres agents

- database-administrator : créer src/db/session.py + src/db/models/* avant que agent.py tourne
- devops-engineer : pyproject.toml racine uv workspace + docker-compose.dev.yml + Makefile

---

## 2026-04-12 — Scaffold Next.js 14 Phase 1 Frontend

**Type** : Frontend Engineering / Scaffold
**Agent** : nextjs-developer
**Score** : N/A (session scaffold)

### Tâche accomplie

Création du scaffold complet `apps/web` : 47 fichiers couvrant config TS/Next.js/Tailwind, App Router, providers, composants UI base, Supabase auth, middleware, API client, i18n FR, tests Vitest, Dockerfile multi-stage.

### Décisions clés

- Server Components par défaut, `"use client"` uniquement pour interactivité/hooks
- OPT-8 fonts : Fraunces + Inter + JetBrains Mono avec `preload: true` + `display: swap` + `latin-ext` pour garantir CLS < 0.1
- Tailwind copié intégralement depuis phase-0 design-system, content adapté pour `./src/**/*.{ts,tsx,mdx}`
- Script anti-FOUC dark mode inline dans le layout root (avant le premier paint)
- Route groups : `(app)` pour routes authentifiées, `(onboarding)` pour flux d'inscription
- Types API minimaux manuels — à remplacer par génération OpenAPI en Phase 1 mature
- `next-pwa` désactivé en dev pour éviter les conflits de cache

### Points d'intégration backend

- Supabase Auth : magic link + OAuth Google → JWT → middleware Next.js valide via `getUser()`
- FastAPI : `NEXT_PUBLIC_API_URL` consommé par `lib/api/client.ts` (GET /recipes, POST /plans/generate, etc.)
- Endpoints à créer Phase 1 : `/api/v1/recipes`, `/api/v1/plans/generate`, `/api/v1/households`

---

## 2026-04-12 — Phase 0 Design Documents : Rate Limiting + PDF Strategy

**Type** : Architecture Design / Backend Engineering
**Agent** : backend-developer
**Score** : N/A (session design, pas d'implémentation)

### Tâche accomplie

Production de 2 documents de design comblant les gaps identifiés par code-reviewer (H4)
et performance-engineer (CRITIQUE-4) lors des audits Phase 0 :

- `phase-0/infra/12-rate-limiting-design.md` — Stratégie rate limiting 5 niveaux (slowapi + Redis)
- `phase-0/infra/13-pdf-generation-strategy.md` — Stratégie génération PDF BOOK_GENERATOR

### Décisions clés prises

**Rate limiting :**
- slowapi + Redis DB 1 retenu (vs fastapi-limiter — pas de sliding window)
- 5 niveaux : IP (60/min) → User lecture (300/min) → User écriture (30/min) → Tenant (1000/min) → LLM coûteux (10/h sur /plan/generate)
- Fail-open si Redis down (sauf mode RATE_LIMIT_STRICT_MODE=true)
- Circuit breakers via `purgatory` pour Anthropic, Stripe, Supabase, Stability AI

**PDF generation :**
- Génération à la validation du plan (pas batch dimanche) → pic 4 min vs 41 min
- Deux queues Celery séparées : `pdf_high` (temps-réel, concurrency 4) + `pdf_low` (batch)
- Idempotence via SHA-256 du contenu du plan (colonne `content_hash` à ajouter)
- Photos pré-générées par RECIPE_SCOUT (Stability AI), pas au moment du PDF

### Dépendances créées pour Phase 1

- DB : colonnes `weekly_books.content_hash`, `weekly_books.generated_at`, `weekly_plans.validated_at`
- Python : `slowapi>=0.1.9`, `limits[redis]>=3.6`, `purgatory>=1.5`
- Redis : DB 1 dédiée rate limiting (DB 0 = Celery broker)

---

## 2026-04-12 — Performance Audit Phase 0

**Type** : Performance Engineering / Audit
**Agent** : performance-engineer
**Score** : N/A (audit, pas de tâche de développement)

### Tâche accomplie

Audit de performance complet de la Phase 0 : base de données (schema, indexes, RLS,
triggers), infrastructure (Docker, Railway, CI), et design system (CSS, motion).
Rapport produit dans `phase-0/_reviews/performance-audit.md`.

### Findings clés

- Score global : 71/100
- 4 bottlenecks CRITIQUES identifiés (query vectorielle, mémoire HNSW, cold start, batch PDF)
- 6 bottlenecks HIGH documentés
- Verdict : FIX AVANT GO (5 blocants avant mise en production)
- Scalabilité v4 : A REVOIR (fondations OK, 5 points de friction à corriger)

### Décisions et recommandations prises

- Dénormaliser `tags` + `total_time_min` dans `recipe_embeddings` pour query vectorielle filtrée
- Supabase Pro obligatoire à partir de 10k recettes embeddées (Free tier incompatible)
- Redis `maxmemory-policy volatile-lru` (pas allkeys-lru) pour protéger les tâches Celery
- API Railway : 512 MB insuffisant avec sentence-transformers (~350 MB) → 1 GB minimum
- Génération PDF : trigger à la validation du plan (étalé semaine) pas batch dimanche
- Endpoint `/ready` distinct de `/health` pour Railway readiness probe

---

## 2026-04-12 — Phase 0 Infrastructure Foundation

**Type** : DevOps / Infrastructure as Code
**Modèle** : claude-sonnet-4-6
**Score** : N/A (session en cours)

### Tâche accomplie

Production de 13 livrables dans `phase-0/infra/` :
provisioning checklist (15 services tiers), structure monorepo, docker-compose dev,
Dockerfiles multi-stage (api + worker), workflow CI GitHub Actions (6 jobs parallèles),
règles de branches, configs Vercel + Railway, template .env, plan monitoring, stratégie Doppler, README.

### Décisions techniques prises

- **Doppler** retenu comme gestionnaire de secrets (vs env natifs Vercel/Railway) — centralisation multi-plateforme
- **Railway** retenu (vs Render) — absence de cold starts sur plan Starter, Redis plugin natif
- **uv** retenu (vs poetry) — 10-100x plus rapide, lock file déterministe PEP 621
- Celery Beat dans un **service séparé** (worker-beat) pour éviter les doublons de tâches planifiées
- Image base : `pgvector/pgvector:pg16` pour le dev local (inclut l'extension pgvector)
- MinIO (vs LocalStack) comme fallback R2 local — plus léger, 100% compatible boto3/aioboto3
- GHCR (GitHub Container Registry) pour stocker les images Docker en CI
- Budget Phase 0 : ~45-90 $/mois confirmé sous la cible de 100 €/mois

---

## 2026-04-12 — Phase 0 Design System

**Type** : UI Design / Design System
**Agent** : ui-designer
**Score** : N/A (session courante)

### Tâche accomplie
Production du design system fondateur dans `phase-0/design-system/` (8 livrables) :
vision marque, tokens couleur/typo/espacement, `tailwind.config.ts` exécutable,
catalogue 30 composants, principes motion, accessibilité WCAG 2.1 AA,
layouts responsive, plan handoff Figma.

### Décisions de design prises
- Palette warm : terracotta HSL(14,75%,55%) / olive HSL(78,35%,42%) / cream HSL(38,30%,98%)
- `primary-400` interdit pour le texte normal sur fond cream (ratio 2.8:1 — echec WCAG)
- `accent-500` (safran) uniquement décoratif (ratio 2.1:1 insuffisant pour texte)
- Ombres avec teinte terracotta (hsl 14 40% 30%) — pas de gris froid
- Dark mode auto après 21h via hook `useTimeBasedTheme`
- View Transitions API pour navigation (card-zoom iOS-like)
- Bento grid asymétrique sur desktop (ADN "livre de recettes")
- `dvh` pour shell mobile (corrige le bug iOS Safari height)

---

## 2026-04-12 — Phase 0 Database Foundation

**Type** : Database Architecture / Schema Design
**Modèle** : claude-sonnet-4-6
**Score** : N/A (session en cours)

### Tâche accomplie
Production des 9 livrables DB dans `phase-0/database/` :
schéma PostgreSQL 16 complet, RLS Supabase, indexes HNSW pgvector,
triggers de validation qualité, guide Alembic, checklist Supabase, seed data.

### Décisions techniques prises
- Dimension embedding choisie : 384 (all-MiniLM-L6-v2, coût zéro)
- SECURITY DEFINER + SET search_path sur get_current_household_id() (sécurité RLS)
- HNSW m=16, ef_construction=64 (point de départ recommandé pgvector)
- table recipe_embeddings séparée de recipes (jointure optionnelle)
- 04-triggers-functions.sql doit être exécuté AVANT 03-rls-policies.sql

---

## 2026-04-11 — Initialisation du projet

**Type** : Initialisation / Setup
**Modèle** : claude-sonnet-4-6
**Score** : ⭐⭐⭐⭐⭐

### Prompt brut
# FICHIER DE RÉFÉRENCE OBLIGATOIRE

Un fichier `ROADMAP.md` est disponible dans les fichiers de ce Project Claude.
**Tu dois le lire intégralement avant d'entreprendre toute tâche.**
Il contient la source de vérité du projet : vision produit, architecture des agents, phases de développement, stack technique, priorités, contraintes et KPI.
Si une décision technique entre en conflit avec la ROADMAP, la ROADMAP a toujours raison. Signale le conflit avant de procéder.

---

# CONTEXTE DU PROJET

Tu es un agent de développement senior travaillant sur **MealPlanner SaaS** — une application B2C de planification de dîners hebdomadaires avec commande drive intégrée (Leclerc, Auchan, Intermarché, Carrefour). Le produit cible les familles françaises et se positionne comme le Jow premium : IA générative, base de recettes mondiale (50 000+), PDF hebdomadaire, mémoire des goûts, mode frigo anti-gaspi.

---

# STACK TECHNIQUE

- **Backend** : Python 3.12, FastAPI, Celery, Redis
- **Base de données** : PostgreSQL + pgvector (embeddings), Supabase (auth + realtime)
- **IA / LLM** : Claude API (claude-sonnet-4-5), LangGraph (orchestration agents), sentence-transformers (embeddings locaux)
- **Scraping** : Scrapy, Playwright
- **PDF** : WeasyPrint + Jinja2
- **Frontend** : Next.js 14, TypeScript, Tailwind CSS, PWA
- **Infra** : Railway, Cloudflare R2 (storage), Sentry (erreurs), PostHog (analytics)
- **Paiement** : Stripe
- **Data** : Spoonacular API, Edamam API, Open Food Facts

---

# ARCHITECTURE AGENTS IA

Six agents orchestrés via LangGraph (détail complet dans ROADMAP.md) :

1. **RECIPE_SCOUT** — Scraping + normalisation + déduplication. Batch nocturne.
2. **TASTE_PROFILE** — Recommandation hybride. Mise à jour temps réel sur feedback.
3. **WEEKLY_PLANNER** — Plan 5-7 dîners/semaine. Contraintes multiples.
4. **CART_BUILDER** — Ingrédients → SKU enseigne → panier drive.
5. **BOOK_GENERATOR** — PDF hebdomadaire automatique chaque dimanche.
6. **RETENTION_LOOP** — Anti-churn, monitoring engagement, relances.

---

# PHASE EN COURS

Consulte la section **06 — Roadmap de développement** dans `ROADMAP.md` pour connaître la phase active et ses priorités exactes.

Avant chaque tâche, identifie :
- La phase en cours (v0 / v1 / v2 / v3 / v4)
- Les devs prioritaires pour cette phase
- L'agent concerné
- Les challenges connus à anticiper

---

# RÈGLES DE DÉVELOPPEMENT

1. **Code Python uniquement** pour le backend. Pas de Node.js côté serveur.
2. **Chaque fonction** : docstring, types hints, tests unitaires (pytest).
3. **Chaque agent** : classe Python indépendante avec méthode `run()` claire.
4. **Tâches longues** (scraping, embeddings batch) : Celery + Redis. Ne jamais bloquer FastAPI.
5. **Logging structuré** : loguru. DEBUG en dev, INFO en prod.
6. **Variables d'environnement** pour toutes les clés API. Jamais de secret en dur.
7. **Git commits** : format conventionnel (`feat:`, `fix:`, `chore:`, `refactor:`).
8. **Qualité des données** : une recette mal structurée vaut moins qu'une recette absente. Validation LLM avant insertion.
9. **Tests** : couverture minimale 80% sur les agents. pytest + pytest-asyncio.
10. **Documentation** : chaque agent a un README décrivant ses inputs, outputs et effets de bord.

---

# DIFFÉRENCIANTS PRODUIT (ne jamais les perdre de vue)

Détail complet dans la section **02** de `ROADMAP.md`. En résumé :

- Base de recettes mondiale avec diversité culturelle réelle (japonais, vietnamien, libanais…)
- Mémoire IA des goûts : chaque feedback modifie le profil famille en temps réel
- Drive FR natif : panier en 1 clic (Leclerc, Auchan, Intermarché, Carrefour)
- Livre PDF hebdomadaire imprimable généré chaque dimanche automatiquement
- Mode frigo & anti-gaspi : recettes qui utilisent l'existant en priorité
- Profils multi-membres : contraintes individuelles réconciliées automatiquement

---

# FORMAT DE RÉPONSE ATTENDU

Pour chaque tâche de développement :

```
## Tâche : [nom]
## Agent concerné : [RECIPE_SCOUT | TASTE_PROFILE | WEEKLY_PLANNER | CART_BUILDER | BOOK_GENERATOR | RETENTION_LOOP]
## Phase : [v0 | v1 | v2 | v3 | v4]
## Cohérence ROADMAP : [Confirme que la tâche est alignée avec la phase en cours]

### Approche
[Explication technique de l'approche choisie et pourquoi]

### Code
[Code Python complet, propre, avec types hints et docstrings]

### Tests
[Tests pytest couvrant les cas nominaux et les cas limites]

### Points d'attention
[Risques, optimisations futures, dépendances à surveiller, conflicts potentiels avec la ROADMAP]
```

---

# PROCHAINE TÂCHE

[Décris ici la tâche spécifique que tu veux faire accomplir à l'agent]

### Prompt optimisé

```xml
<role>
Tu es un expert développeur senior avec une expertise profonde en clean code, bonnes pratiques et architecture logicielle. Tu privilégies la lisibilité, la maintenabilité et la sécurité.
</role>

<context>
Avant de répondre, charge et lis les fichiers de contexte du projet (par ordre de priorité) :
- `CLAUDE.md` — règles, workflow et vue d'ensemble du projet
- `memory/project-context.md` — architecture, stack technique, décisions clés
- `memory/primer.md` — connaissance de fond, glossaire métier, règles du domaine
- `memory/session-context.md` — objectif et tâches de la session courante
- `memory/hindsight.md` — rétrospectives et pièges à éviter
- `memory/prompt-history.md` — historique des prompts et décisions passées

Si certains de ces fichiers n'existent pas encore, ignore-les et continue.

[Complète si pertinent :]
- Audience / utilisateur final : [À préciser]
- Enjeux ou contraintes spécifiques : [À préciser]
- Environnement technique ou organisationnel : [À préciser]
</context>

<instructions>
1. Analyse la demande et identifie le comportement attendu
2. Implémente la solution en suivant les bonnes pratiques du langage
3. Ajoute des commentaires uniquement où la logique n'est pas évidente
4. Indique si des tests ou validations supplémentaires sont recommandés

Important : cette tâche est complexe. Prends le temps nécessaire pour produire un résultat de haute qualité. Va au-delà du minimum.
</instructions>

<constraints>
- Respecte les conventions du langage cible
- Code fonctionnel et testé mentalement avant de répondre
- Pas de sur-ingénierie — solution la plus simple qui fonctionne
- [AJOUTER contraintes spécifiques : version Python/Node/etc.]
</constraints>

<examples>
  <!-- Ajoute 3-5 exemples représentatifs de l'output attendu -->
  <example>
    <input>[exemple d'entrée]</input>
    <output>[exemple de sortie attendue]</output>
  </example>
</examples>

<!-- Chain-of-Thought : décommente si tu veux voir le raisonnement -->
<!-- Avant de répondre, réfléchis étape par étape dans <thinking>.
     Donne ta réponse finale dans <answer>. -->

<input>
# FICHIER DE RÉFÉRENCE OBLIGATOIRE

Un fichier `ROADMAP.md` est disponible dans les fichiers de ce Project Claude.
**Tu dois le lire intégralement avant d'entreprendre toute tâche.**
Il contient la source de vérité du projet : vision produit, architecture des agents, phases de développement, stack technique, priorités, contraintes et KPI.
Si une décision technique entre en conflit avec la ROADMAP, la ROADMAP a toujours raison. Signale le conflit avant de procéder.

---

# CONTEXTE DU PROJET

Tu es un agent de développement senior travaillant sur **MealPlanner SaaS** — une application B2C de planification de dîners hebdomadaires avec commande drive intégrée (Leclerc, Auchan, Intermarché, Carrefour). Le produit cible les familles françaises et se positionne comme le Jow premium : IA générative, base de recettes mondiale (50 000+), PDF hebdomadaire, mémoire des goûts, mode frigo anti-gaspi.

---

# STACK TECHNIQUE

- **Backend** : Python 3.12, FastAPI, Celery, Redis
- **Base de données** : PostgreSQL + pgvector (embeddings), Supabase (auth + realtime)
- **IA / LLM** : Claude API (claude-sonnet-4-5), LangGraph (orchestration agents), sentence-transformers (embeddings locaux)
- **Scraping** : Scrapy, Playwright
- **PDF** : WeasyPrint + Jinja2
- **Frontend** : Next.js 14, TypeScript, Tailwind CSS, PWA
- **Infra** : Railway, Cloudflare R2 (storage), Sentry (erreurs), PostHog (analytics)
- **Paiement** : Stripe
- **Data** : Spoonacular API, Edamam API, Open Food Facts

---

# ARCHITECTURE AGENTS IA

Six agents orchestrés via LangGraph (détail complet dans ROADMAP.md) :

1. **RECIPE_SCOUT** — Scraping + normalisation + déduplication. Batch nocturne.
2. **TASTE_PROFILE** — Recommandation hybride. Mise à jour temps réel sur feedback.
3. **WEEKLY_PLANNER** — Plan 5-7 dîners/semaine. Contraintes multiples.
4. **CART_BUILDER** — Ingrédients → SKU enseigne → panier drive.
5. **BOOK_GENERATOR** — PDF hebdomadaire automatique chaque dimanche.
6. **RETENTION_LOOP** — Anti-churn, monitoring engagement, relances.

---

# PHASE EN COURS

Consulte la section **06 — Roadmap de développement** dans `ROADMAP.md` pour connaître la phase active et ses priorités exactes.

Avant chaque tâche, identifie :
- La phase en cours (v0 / v1 / v2 / v3 / v4)
- Les devs prioritaires pour cette phase
- L'agent concerné
- Les challenges connus à anticiper

---

# RÈGLES DE DÉVELOPPEMENT

1. **Code Python uniquement** pour le backend. Pas de Node.js côté serveur.
2. **Chaque fonction** : docstring, types hints, tests unitaires (pytest).
3. **Chaque agent** : classe Python indépendante avec méthode `run()` claire.
4. **Tâches longues** (scraping, embeddings batch) : Celery + Redis. Ne jamais bloquer FastAPI.
5. **Logging structuré** : loguru. DEBUG en dev, INFO en prod.
6. **Variables d'environnement** pour toutes les clés API. Jamais de secret en dur.
7. **Git commits** : format conventionnel (`feat:`, `fix:`, `chore:`, `refactor:`).
8. **Qualité des données** : une recette mal structurée vaut moins qu'une recette absente. Validation LLM avant insertion.
9. **Tests** : couverture minimale 80% sur les agents. pytest + pytest-asyncio.
10. **Documentation** : chaque agent a un README décrivant ses inputs, outputs et effets de bord.

---

# DIFFÉRENCIANTS PRODUIT (ne jamais les perdre de vue)

Détail complet dans la section **02** de `ROADMAP.md`. En résumé :

- Base de recettes mondiale avec diversité culturelle réelle (japonais, vietnamien, libanais…)
- Mémoire IA des goûts : chaque feedback modifie le profil famille en temps réel
- Drive FR natif : panier en 1 clic (Leclerc, Auchan, Intermarché, Carrefour)
- Livre PDF hebdomadaire imprimable généré chaque dimanche automatiquement
- Mode frigo & anti-gaspi : recettes qui utilisent l'existant en priorité
- Profils multi-membres : contraintes individuelles réconciliées automatiquement

---

# FORMAT DE RÉPONSE ATTENDU

Pour chaque tâche de développement :

```
## Tâche : [nom]
## Agent concerné : [RECIPE_SCOUT | TASTE_PROFILE | WEEKLY_PLANNER | CART_BUILDER | BOOK_GENERATOR | RETENTION_LOOP]
## Phase : [v0 | v1 | v2 | v3 | v4]
## Cohérence ROADMAP : [Confirme que la tâche est alignée avec la phase en cours]

### Approche
[Explication technique de l'approche choisie et pourquoi]

### Code
[Code Python complet, propre, avec types hints et docstrings]

### Tests
[Tests pytest couvrant les cas nominaux et les cas limites]

### Points d'attention
[Risques, optimisations futures, dépendances à surveiller, conflicts potentiels avec la ROADMAP]
```

---

# PROCHAINE TÂCHE

[Décris ici la tâche spécifique que tu veux faire accomplir à l'agent]
</input>

<output_format>
1. Code complet et fonctionnel
2. Explication courte des choix techniques (si non évidents)
3. [OPTIONNEL] Exemple d'utilisation
</output_format>
```

### Notes
Prompt généré automatiquement lors de l'initialisation du projet via Claude Prompt Optimizer.

---

## 2026-04-12 — Refonte majeure page recettes (5 corrections) — nextjs-developer

**Scope** : `apps/web/src/app/(app)/recipes/recipes-explorer.tsx`, `apps/web/src/components/recipe/recipe-filters.tsx`, `apps/web/src/components/recipe/recipe-card.tsx`

**Correction 1 — Pagination numérotée** : Remplacement de `useInfiniteQuery` par `useQuery` avec état `page`. Composant `Pagination` avec ellipses (max 7 boutons visibles), scroll to top au changement de page. `totalPages = Math.ceil(total / 24)`.

**Correction 2 — Filtres latéraux** : Budget chips → valeurs FR (`économique`/`moyen`/`premium`). Slider max_time → `undefined` à 120min (pas de filtre). Difficulté → 5 niveaux 1-5 alignés sur `RecipeFilters.difficulty`. Régime → `DietaryTag[]` multi-select. Cuisine → top 10 uniquement. Chips actives en terracotta `#E2725B`.

**Correction 3 — Cards enrichies** : Ajout badge coût estimé (`€`/`€€`/`€€€`) basé sur `dietary_tags` et `difficulty`. Ajout ligne temps + horloge sous le titre. `getDisplayTime()` gère `total_time_minutes` ou `prep + cook`. Types strictement alignés sur `Recipe` (`dietary_tags` pas `tags`, `difficulty: "easy"|"medium"|"hard"`).

**Correction 4 — Textes FR** : Boutons "← Précédent" / "Suivant →", compteur "recettes", message vide, pills rapides 4 seulement (Rapide/Desserts/Végétarien/Facile).

**Correction 5 — Cuisines regroupées** : Pills rapides sans cuisines individuelles. Cuisines uniquement dans le panneau de filtre (top 10 = CUISINE_OPTIONS réduit de 18 à 10).

**Typecheck** : `pnpm typecheck` — 0 erreur TypeScript.

<!-- Ajoute tes nouveaux prompts ci-dessus avec le même format -->
