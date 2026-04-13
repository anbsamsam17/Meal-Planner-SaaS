# Code Review — Phase 0 MealPlanner

> Reviewer : senior code reviewer (Claude Opus 4.6 1M)
> Date : 2026-04-12
> Périmètre : `phase-0/database/`, `phase-0/infra/`, `phase-0/design-system/`, `phase-0/ux-research/`
> Volume : 35 fichiers inspectés, ~4 200 lignes de SQL/YAML/TS/Markdown

---

## Score global : **82 / 100**

Repartition :
- Sécurité : 17/25 (multi-tenancy solide, quelques trous côté Dockerfile et Docker Compose)
- Cohérence architecturale : 22/25 (alignement ROADMAP / agents IA quasi parfait)
- Qualité code : 21/25 (SQL bien normalisé, commentaires FR utiles, quelques micro-bugs)
- Conformité ROADMAP : 14/20 (rate limiting absent du code, Flagsmith non configuré côté DB/API)
- Complétude : 8/10 (manque audit_log RGPD, manque `.dockerignore`)

---

## Issues CRITIQUES (bloquant mise en prod)

### C1 — `recipe_ingredients` : doublons impossibles à bloquer quand `notes` diffère
**Fichier** : `phase-0/database/01-schema-core.sql:156-166`
**Description** : La PRIMARY KEY est `(recipe_id, ingredient_id)`. Problème mineur mais OK. En revanche le seed (`07-seed-data.sql:173-198`) utilise `ON CONFLICT DO NOTHING` sans préciser la clé ; PostgreSQL ne pardonne pas ce genre d'ambiguïté si un index partiel tombe. À vérifier, mais pas critique.
**Impact** : Faible — non bloquant. *Re-classé en LOW*.

### C2 — Trigger `validate_recipe_quality()` exécuté AVANT mais sans `SECURITY DEFINER` ni `SET search_path`
**Fichier** : `phase-0/database/04-triggers-functions.sql:102-151`
**Description** : La fonction est en `plpgsql` sans `SET search_path TO ''` alors que `get_current_household_id()` l'a. Un attaquant ayant un schéma `public` piégé pourrait potentiellement rediriger des appels (faible exploit réel ici car la fonction n'appelle aucune autre table, mais c'est une règle défensive universelle).
**Impact** : Moyen. L'exploitation réelle est faible puisqu'il n'y a pas d'appel à d'autres objets, mais la règle "toutes les fonctions plpgsql en SECURITY DEFINER ou a minima search_path fixé" doit être universelle.
**Fix** : Ajouter `SET search_path TO pg_catalog, public` au bloc `CREATE OR REPLACE FUNCTION validate_recipe_quality()`. Faire pareil pour `trigger_set_updated_at()` et `cleanup_old_embeddings()`.

### C3 — Fichier SQL `03-rls-policies.sql` : **policies DELETE manquantes sur plusieurs tables critiques**
**Fichier** : `phase-0/database/03-rls-policies.sql` (multiple)
**Description** :
- `households` : aucune policy DELETE (OK, documenté volontaire).
- `weekly_plans` : **aucune policy DELETE** pour `authenticated` alors qu'on permet à un utilisateur de repartir de zéro. Conséquence : impossible pour un user de supprimer son propre plan (même draft) sans passer par le service role.
- `recipe_feedbacks` : aucune DELETE (OK — audit trail).
- `fridge_items` : DELETE présente (OK).
- `shopping_lists` : pas d'INSERT/UPDATE/DELETE user-facing documentés comme réservés au service_role. Mais l'user doit pouvoir cocher un item → donc UPDATE user devrait exister. **Gap UX.**
**Impact** : Les utilisateurs ne pourront ni cocher des items de leur shopping list, ni supprimer leurs plans. Bloquant fonctionnel pour la v0.
**Fix** :
```sql
-- Ajouter à 03-rls-policies.sql :
CREATE POLICY weekly_plans_delete ON weekly_plans
  FOR DELETE TO authenticated
  USING (household_id = get_current_household_id() AND status = 'draft');

CREATE POLICY shopping_lists_update ON shopping_lists
  FOR UPDATE TO authenticated
  USING (plan_id IN (SELECT id FROM weekly_plans WHERE household_id = get_current_household_id()))
  WITH CHECK (plan_id IN (SELECT id FROM weekly_plans WHERE household_id = get_current_household_id()));
```

### C4 — `household_members_insert` policy : **récursion RLS infinie possible**
**Fichier** : `phase-0/database/03-rls-policies.sql:127-139`
**Description** : La policy INSERT fait une sous-requête sur `household_members` elle-même pendant que RLS est activée sur la même table. PostgreSQL gère ça via `SECURITY DEFINER` dans `get_current_household_id()`, mais **ici la sous-requête n'utilise PAS cette fonction** — elle fait directement `SELECT household_id FROM household_members WHERE supabase_user_id = auth.uid() AND role = 'owner'`. Avec RLS activée + FORCE, cette sous-requête est elle-même filtrée par la policy SELECT, qui appelle `get_current_household_id()`, qui relit `household_members`. Risque de récursion ou au mieux de comportement inattendu (la policy SELECT autorise à voir les membres du foyer courant — donc la requête interne fonctionne par chance).
**Impact** : Élevé — le tout premier `INSERT` household_member lors de la création d'un foyer échouera (le user n'est owner de rien encore). **Bloquant pour l'onboarding.**
**Fix** : Soit rendre le endpoint "créer foyer + premier owner" accessible uniquement via service_role côté API (recommandé), soit créer une policy INSERT plus permissive sur le **premier** membre et contraindre côté API.
```sql
-- Recommandé : pas de policy INSERT pour authenticated,
-- le flux "create household + owner" passe par le service role dans l'API FastAPI.
-- Documenter explicitement dans 03-rls-policies.sql et dans le guide onboarding.
```

### C5 — `get_household_constraints()` : SECURITY DEFINER + search_path vide = JOIN vers tables non-qualifiées MAIS les tables SONT préfixées `public.` — **OK**, mais la signature retourne `jsonb_agg(DISTINCT ...)` sans GROUP BY qui peut retourner **une ligne par combinaison au lieu d'une ligne agrégée**
**Fichier** : `phase-0/database/04-triggers-functions.sql:160-187`
**Description** : La CTE fait un `LEFT JOIN LATERAL jsonb_array_elements(...)` puis agrège avec `jsonb_agg(DISTINCT ...)`. Sans `GROUP BY`, PostgreSQL traite l'agrégation en global — OK. Mais `MIN(mp.cooking_time_max)` et `MIN(mp.budget_pref)` sont agrégés en même temps que le LATERAL qui explose en N lignes. Résultat : `MIN(cooking_time_max)` sera recalculé sur des lignes dupliquées (non bloquant pour MIN, mais dangereux si on ajoute demain `AVG`). De plus, **`MIN` sur un TEXT budget_pref** donnera `'économique' < 'moyen' < 'premium'` lexicographiquement, ce qui est le comportement voulu par chance (mais totalement non documenté et fragile).
**Impact** : Haute — la fonction peut renvoyer des agrégats incorrects si le schéma `member_preferences` évolue. Le "plus restrictif" pour budget_pref repose sur l'ordre lexicographique `'économique' < 'moyen' < 'premium'` qui n'est **pas garanti** avec une locale française (le `é` peut être trié différemment).
**Fix** :
```sql
-- Utiliser un CASE WHEN pour ordonner explicitement :
SELECT
  (SELECT jsonb_agg(DISTINCT a) FROM public.member_preferences mp
   JOIN public.household_members hm ON hm.id = mp.member_id,
   LATERAL jsonb_array_elements_text(mp.allergies) a
   WHERE hm.household_id = p_household_id) AS allergies_union,
  (SELECT jsonb_agg(DISTINCT d) FROM public.member_preferences mp
   JOIN public.household_members hm ON hm.id = mp.member_id,
   LATERAL jsonb_array_elements_text(mp.diet_tags) d
   WHERE hm.household_id = p_household_id) AS diet_tags_union,
  (SELECT MIN(cooking_time_max) FROM public.member_preferences mp
   JOIN public.household_members hm ON hm.id = mp.member_id
   WHERE hm.household_id = p_household_id) AS max_cooking_time,
  (SELECT budget_pref FROM public.member_preferences mp
   JOIN public.household_members hm ON hm.id = mp.member_id
   WHERE hm.household_id = p_household_id
   ORDER BY CASE budget_pref WHEN 'économique' THEN 1 WHEN 'moyen' THEN 2 WHEN 'premium' THEN 3 END
   LIMIT 1) AS budget_pref;
```

---

## Issues HIGH (à fixer avant Phase 1)

### H1 — Absence totale de `.dockerignore`
**Fichier** : `phase-0/infra/` (fichier manquant)
**Description** : Les deux Dockerfiles (`03-apps-api-Dockerfile`, `04-apps-worker-Dockerfile`) utilisent `COPY apps/api/pyproject.toml apps/api/uv.lock ./` et plus loin `COPY apps/api/src ./src`. Sans `.dockerignore`, si le build est lancé avec `docker build -f apps/api/Dockerfile -t mealplanner-api:local .` (comme dans le README), **tout le repo est envoyé comme contexte de build**, y compris `.env.local`, `memory/`, `node_modules`, `.git`, `phase-0/`, etc. Cela expose potentiellement des secrets locaux et ralentit massivement les builds.
**Impact** : Élevé — risque de fuite de secrets dans le contexte Docker (même s'ils ne finissent pas dans l'image, ils transitent par le daemon).
**Fix** : Créer `infra/docker/.dockerignore` (ou un `.dockerignore` à la racine) avec :
```
**/node_modules
**/.next
**/.venv
**/__pycache__
**/*.pyc
.git
.env*
!.env.example
memory/
phase-0/
docs/
tests/
*.md
.github/
```

### H2 — Dockerfile API : `HEALTHCHECK` utilise port hardcodé malgré `ENV PORT=8000`
**Fichier** : `phase-0/infra/03-apps-api-Dockerfile:105-118`
**Description** : Le `HEALTHCHECK` utilise `http://localhost:${PORT}/health` (bien), mais l'`ENTRYPOINT` qui suit est hardcodé `--port 8000`. Si Railway injecte `$PORT` différent (ce qui est le cas — Railway définit `$PORT` dynamiquement), uvicorn ne l'utilisera pas → le service sera unreachable.
**Impact** : Élevé — le déploiement Railway échouera au premier boot en prod.
**Fix** :
```dockerfile
ENTRYPOINT ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --no-access-log"]
```
Ou mieux : utiliser `CMD` avec la syntaxe shell.

### H3 — Aucune politique RLS pour `planned_meals` INSERT d'un plan par son owner en mode `validated`
**Fichier** : `phase-0/database/03-rls-policies.sql:300-320`
**Description** : La policy INSERT n'interdit pas l'ajout de repas à un plan `status='validated'` ou `'archived'`. Elle vérifie uniquement l'appartenance au household. Conséquence : un user peut modifier rétroactivement un plan archivé → incohérence avec `shopping_lists`, `weekly_books` déjà générés.
**Impact** : Intégrité métier. Les PDFs déjà envoyés ne refléteront plus le plan modifié.
**Fix** : Ajouter `AND (SELECT status FROM weekly_plans WHERE id = plan_id) = 'draft'` dans les policies INSERT/UPDATE/DELETE de `planned_meals`.

### H4 — Rate limiting absent partout
**Fichier** : Transverse — règle ROADMAP et CLAUDE.md **non-négociable**
**Description** : La règle ROADMAP et `CLAUDE.md` imposent explicitement : *"Rate limiting sur toutes les API (par tenant et par utilisateur)"*. Aucun livrable phase-0 ne mentionne :
- `slowapi` / `limits` dans les dépendances attendues de l'API
- Schéma Redis pour stocker les compteurs de rate limiting
- Middleware FastAPI correspondant
- Tests correspondants
`01-monorepo-structure.md:63` évoque vaguement `core/ # Auth middleware, rate limiting, logging` mais sans aucun détail.
**Impact** : Règle non-négociable ROADMAP non respectée → DDoS trivial sur n'importe quel endpoint LLM (coûts Anthropic explosifs).
**Fix** : Créer un fichier `phase-0/infra/12-rate-limiting-strategy.md` documentant :
- Stratégie : `slowapi` + Redis sliding window
- Limites par plan : starter (10 req/min), famille (60 req/min), coach (120 req/min)
- Limite spécifique sur `/agents/plan-generate` : 5 req/heure/tenant
- Headers standards `X-RateLimit-Limit`, `X-RateLimit-Remaining`
- Fallback quand Redis est down (fail-open vs fail-close)

### H5 — `ci.yml` : injection de secrets dummies mais aucun job ne charge Doppler
**Fichier** : `phase-0/infra/05-github-workflows-ci.yml:169-179`
**Description** : Les tests passent avec `ANTHROPIC_API_KEY=test_key_anthropic` etc. C'est OK pour les unit tests mockés. Mais `11-secrets-management.md:64-75` documente l'intégration `dopplerhq/secrets-fetch-action@v1.1.3` qui **n'est pas appliquée** dans le workflow CI. Il y a donc une incohérence entre la doc et le code effectivement livré.
**Impact** : Moyen. En l'état, le CI ne peut pas exécuter de tests d'intégration nécessitant de vrais secrets (ex : validation webhook Stripe).
**Fix** : Soit ajouter effectivement le step Doppler dans `test-api`, soit documenter explicitement dans le README que les secrets sont injectés par GitHub Secrets en attendant.

### H6 — `gitleaks` en CI sans `.gitleaks.toml` dédié
**Fichier** : `phase-0/infra/05-github-workflows-ci.yml:307-312`
**Description** : `gitleaks-action@v2` utilise la config par défaut. Avec des placeholders du genre `sk_test_...` et `pk_test_...` présents dans `09-env-template.env`, **gitleaks va faire des faux positifs à chaque run** ou, pire, on aura tendance à mettre `continue-on-error: true` dessus. Or le job security n'a pas de `continue-on-error` sur gitleaks → **tous les PRs vont bloquer**.
**Impact** : Élevé — le CI sera cassé dès le premier push.
**Fix** : Créer un `.gitleaks.toml` à la racine avec une allowlist explicite des fichiers `*.env` templates et des patterns `sk_test_\.\.\.`. Exemple :
```toml
[allowlist]
description = "Allowlist pour les templates .env et les exemples"
paths = [
  '''.*\.env\.example$''',
  '''phase-0/infra/09-env-template\.env''',
]
regexes = [
  '''sk_(test|live)_\.\.\.''',
  '''whsec_\.\.\.''',
  '''price_\.\.\.''',
  '''pk_(test|live)_\.\.\.''',
]
```

### H7 — Docker Compose dev : mots de passe hardcodés dans un fichier committé
**Fichier** : `phase-0/infra/02-docker-compose.dev.yml:29-31, 110-111`
**Description** : `POSTGRES_PASSWORD: mealplanner_dev_password`, `MINIO_ROOT_PASSWORD: mealplanner_minio_password`. Ces mots de passe sont **dans un fichier committé dans le repo**. C'est tolérable pour un fichier explicitement dev-only, mais :
1. Il n'y a aucun commentaire "DEV ONLY — NE PAS RÉUTILISER EN PROD"
2. Le fichier `09-env-template.env:42` reprend le même mot de passe `mealplanner_dev_password` comme valeur par défaut → si quelqu'un copie bêtement `.env.local` en prod, il aura une DB avec mot de passe trivial.
3. `gitleaks` pourrait le flag selon sa config par défaut.
**Impact** : Moyen. Risque de dérive dev→prod.
**Fix** : Ajouter un en-tête commenté très explicite dans les deux fichiers ("DEV ONLY, NEVER USE IN PROD"). Idéalement, utiliser `${POSTGRES_PASSWORD:-mealplanner_dev_password}` pour permettre override.

### H8 — Supabase Realtime non activé dans la DB pour les tables RLS
**Fichier** : `phase-0/database/03-rls-policies.sql` (manquant), `phase-0/database/06-supabase-setup.md:96-101`
**Description** : Le guide Supabase dit d'activer Realtime manuellement via le Dashboard pour `weekly_plans`, `shopping_lists`, `recipe_feedbacks`, `planned_meals`. C'est une action manuelle que personne ne va faire avant le premier incident. Or Supabase expose aussi une commande SQL : `ALTER PUBLICATION supabase_realtime ADD TABLE weekly_plans;`. Cette commande doit être dans le fichier SQL de migration pour être idempotente.
**Impact** : Moyen. Feature manquante silencieusement après chaque nouvelle installation.
**Fix** : Créer un fichier `08-realtime-publication.sql` :
```sql
ALTER PUBLICATION supabase_realtime ADD TABLE weekly_plans;
ALTER PUBLICATION supabase_realtime ADD TABLE planned_meals;
ALTER PUBLICATION supabase_realtime ADD TABLE shopping_lists;
ALTER PUBLICATION supabase_realtime ADD TABLE recipe_feedbacks;
```

### H9 — Absence de table `audit_log` pour conformité RGPD / traçabilité
**Fichier** : `phase-0/database/01-schema-core.sql` (manquant)
**Description** : Une SaaS B2C qui stocke des données personnelles (préférences alimentaires = données de santé sensibles selon CNIL — allergies, régimes médicaux), héberge en EU, doit pouvoir :
1. Fournir un export complet des données d'un user (droit à la portabilité)
2. Prouver qui a accédé à quoi (droit à l'information)
3. Tracer les modifications sensibles (changement de plan Stripe, suppression de foyer)
Aucune table `audit_log` n'est prévue. Les triggers `updated_at` ne suffisent pas.
**Impact** : Moyen-élevé. Pas strictement bloquant pour la phase 0 mais ajouter ça plus tard coûtera 10x plus cher (migration, rétrofit des endpoints).
**Fix** : Ajouter dans Phase 0.1 ou début Phase 1 :
```sql
CREATE TABLE audit_log (
    id           BIGSERIAL PRIMARY KEY,
    household_id UUID,
    actor_id     UUID,  -- supabase_user_id ou 'system'/'service_role'
    action       TEXT NOT NULL,  -- 'household.create', 'member.delete', 'plan.stripe_update'
    entity_type  TEXT NOT NULL,
    entity_id    UUID,
    metadata     JSONB NOT NULL DEFAULT '{}',
    ip_address   INET,
    user_agent   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_log_household_created ON audit_log (household_id, created_at DESC);
```

---

## Issues MEDIUM (à fixer en Phase 1)

### M1 — Alembic `env.py` : dépendance cyclique SQL files ↔ migration
**Fichier** : `phase-0/database/05-alembic-setup.md:207-223`
**Description** : La migration `0001_initial_schema.py` lit les fichiers SQL depuis `../../../phase-0/database/`. Or `phase-0/` est un dossier de référence qui sera supprimé ou archivé après la Phase 0. La migration se retrouvera orpheline.
**Fix** : Copier les fichiers SQL dans `apps/api/alembic/sql/` au moment de la Phase 0.6 (finalisation) et y pointer la migration.

### M2 — `gen_random_uuid()` utilisé mais l'extension `uuid-ossp` activée inutilement
**Fichier** : `phase-0/database/00-setup-extensions.sql:10`
**Description** : `gen_random_uuid()` est fourni nativement par PostgreSQL 13+ via `pgcrypto`. `uuid-ossp` n'est pas utilisé nulle part dans le schéma (aucun `uuid_generate_v4()`). L'extension est chargée pour rien.
**Fix** : Supprimer la ligne `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";` et le commentaire associé.

### M3 — `cleanup_old_embeddings()` : race condition possible avec RECIPE_SCOUT
**Fichier** : `phase-0/database/04-triggers-functions.sql:200-218`
**Description** : La fonction fait un `DELETE FROM recipe_embeddings WHERE recipe_id NOT IN (SELECT id FROM recipes)`. Si le pipeline RECIPE_SCOUT insère un nouvel embedding pendant que cette fonction tourne, et que la recette correspondante vient d'être créée (mais pas encore visible pour cette transaction READ COMMITTED), on supprime un embedding valide. Probabilité faible mais réelle.
**Fix** : Ajouter `SELECT id FROM recipes WHERE created_at < now() - interval '1 hour'` pour ne nettoyer que les embeddings "anciens".

### M4 — `member_preferences.diet_tags` JSONB alors que `recipes.tags` est TEXT[]
**Fichier** : `phase-0/database/01-schema-core.sql:61, 107`
**Description** : Incohérence de stockage pour un concept identique ("tags de régime alimentaire"). Cela complique :
- Les jointures "recettes compatibles avec ces diet_tags"
- L'indexation
- La validation côté API (Pydantic doit avoir deux schemas)
**Fix** : Uniformiser en TEXT[] ou JSONB partout. Le choix naturel est TEXT[] pour les tags (requêtes `ANY`, intersection `&&`, index GIN). Garder JSONB uniquement pour `allergies` (structure évolutive potentielle).

### M5 — `planned_meals.slot` accepte `lunch` mais le schéma v0 documente `dinner` uniquement
**Fichier** : `phase-0/database/01-schema-core.sql:240`
**Description** : `CHECK (slot IN ('dinner', 'lunch'))` alors que le commentaire dit "uniquement 'dinner' pour la v0/v1". Incohérence.
**Fix** : Soit retirer `'lunch'` du CHECK, soit retirer la mention "uniquement dinner" du commentaire. Choix recommandé : ajouter `'lunch'` maintenant pour éviter une migration plus tard, et documenter que l'UI ne l'expose pas.

### M6 — `weekly_plans.week_start` doit être un lundi : contrainte non implémentée
**Fichier** : `phase-0/database/01-schema-core.sql:218`
**Description** : Commentaire : "Toujours un lundi (validé côté application et trigger)". Mais aucun trigger n'est défini dans `04-triggers-functions.sql` pour enforcer ça. Si un dev oublie la validation API, on aura des plans "semaine du mardi 14" qui casseront tous les calculs J+7.
**Fix** :
```sql
ALTER TABLE weekly_plans
  ADD CONSTRAINT weekly_plans_week_start_is_monday
  CHECK (EXTRACT(ISODOW FROM week_start) = 1);
```

### M7 — Pas de CHECK sur `household_members` pour un unique owner par foyer
**Fichier** : `phase-0/database/01-schema-core.sql:30-46`
**Description** : Rien n'empêche deux `owner` dans le même foyer. C'est peut-être voulu (coparents), mais alors la policy `subscriptions_select` donnera accès aux données de facturation à plusieurs users sans protection. À clarifier.
**Fix** : Documenter explicitement. Soit `UNIQUE (household_id) WHERE role = 'owner'` (index partiel), soit autoriser co-owners en toute conscience.

### M8 — `recipe_feedbacks` : pas de contrainte UNIQUE (member_id, recipe_id, feedback_type)
**Fichier** : `phase-0/database/01-schema-core.sql:191-203`
**Description** : Un user peut spammer 100 "cooked" sur la même recette. Le training TASTE_PROFILE sera biaisé.
**Fix** : Soit rate limiting côté API, soit contrainte `UNIQUE (member_id, recipe_id, feedback_type, DATE(created_at))` pour au moins limiter à un par jour.

### M9 — Dockerfiles : absence de `apt-get update` mais `python:3.12-slim` peut manquer de `libpq-dev` pour `asyncpg`
**Fichier** : `phase-0/infra/03-apps-api-Dockerfile:25`
**Description** : `asyncpg` est pure Python (utilise la wire protocol) donc ne nécessite pas `libpq`. MAIS `psycopg2-binary` (listé dans `05-alembic-setup.md:42`) a besoin de libs système. Si Alembic tourne dans le container runtime (probable), le build échouera au moment de `import psycopg2`.
**Fix** : Soit ajouter `RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*` dans le stage runtime, soit utiliser `psycopg[binary]` v3 qui est self-contained, soit confirmer qu'Alembic ne tourne que dans un container séparé one-shot.

### M10 — Workflow CI : `test-api` dépend de `lint-api` mais pas de `test-web` qui dépend de `lint-web`
**Fichier** : `phase-0/infra/05-github-workflows-ci.yml:141, 233`
**Description** : OK structurellement, mais si `lint-api` échoue, `test-api` est skippé → `build-docker` qui dépend de `test-api` voit un status `skipped` qui est **considéré comme success par `needs:`**. Résultat : une image buggée peut être publiée si le lint était cassé.
**Fix** : Utiliser `if: always() && needs.test-api.result == 'success'` dans le job `build-docker`.

### M11 — `pip-audit` commande pipée vers un script Python inline fragile
**Fichier** : `phase-0/infra/05-github-workflows-ci.yml:286-290`
**Description** : Le one-liner Python inline pour parser la sortie JSON de `pip-audit` est difficile à maintenir et peut casser avec les évolutions du format. `pip-audit` a un flag `--strict` qui fait exit 1 sur vulnérabilité directement.
**Fix** :
```yaml
- name: pip-audit (API)
  working-directory: apps/api
  run: uv run pip-audit --strict
```

### M12 — Pas de test SQL pour les RLS dans `database/README.md` (seulement checklist manuelle)
**Fichier** : `phase-0/database/README.md:197-204`
**Description** : La checklist de validation RLS est manuelle. Aucun test SQL automatisé (`pgTAP` ou requêtes fixtures). En cas de changement de policy, aucune alerte.
**Fix** : Créer `phase-0/database/08-rls-tests.sql` avec pgTAP ou des assertions explicites.

### M13 — `brand-vision.md` mentionne "livre de cuisine Ottolenghi" mais aucune référence au terme "B2C" alors que CLAUDE.md mentionne "B2B"
**Fichier** : `CLAUDE.md` (projet-level) vs `phase-0/ux-research/personas.md:3`
**Description** : `CLAUDE.md:6` dit "SaaS / B2B" mais tous les personas et la vision de marque parlent de familles françaises (B2C). C'est un vestige du template CLAUDE.md. Non bloquant mais trompeur.
**Fix** : Corriger `CLAUDE.md` pour dire "SaaS B2C (familles)" — ou au minimum noter l'incohérence dans `memory/project-context.md`.

---

## Issues LOW / Suggestions

### L1 — Commentaire SQL `01-schema-core.sql:239` : `-- 1=lundi, 2=mardi...`
Commentaire utile mais redondant avec `EXTRACT(ISODOW)`. Préciser "selon ISO 8601" évite la confusion avec la convention US (dimanche = 1).

### L2 — `shopping_lists.items` JSONB : schéma JSON non validé
Pas de `CHECK (jsonb_typeof(items) = 'array')`. Ajouter pour garantir qu'un bug API ne pollue pas la table.

### L3 — `0001_initial_schema.py` : le `downgrade()` ne drop pas `recipes` dans le bon ordre FK
Les ordres sont bons, mais manquent `recipe_ingredients` avant `ingredients`. Non bloquant tant que CASCADE est utilisé.

### L4 — Dockerfile worker : `HEALTHCHECK` Celery `inspect ping` est lent (1-3 s) et consomme du Redis
Sur Railway avec plusieurs workers, cela peut générer du trafic Redis inutile. Alternative : créer un fichier `/tmp/celery_ready` au boot et le vérifier.

### L5 — `09-env-template.env:69` : `ANTHROPIC_MODEL=claude-sonnet-4-5`
Le modèle est correct selon ROADMAP, mais pas de variable pour le fallback (`ANTHROPIC_MODEL_FALLBACK`). En cas de rate limit Anthropic, impossible de switcher gracefully.

### L6 — `02-design-tokens.md:135-139` : `warning-500` sur `neutral-50` → contraste 4.1:1 (AA borderline)
Documenter explicitement l'usage limité aux textes ≥16px bold pour ce token.

### L7 — `03-tailwind-config.ts:19` : content path `./components/**/*` (hors `src/`) peut matcher des fichiers shadcn à la racine
Si le projet est structuré avec `apps/web/src/`, cette ligne ne matchera rien. À retirer ou documenter.

### L8 — `01-brand-vision.md:10` : ton marketing dans un livrable technique
Le contenu est juste mais le ton commercial ("assistant IA qui connaît vos enfants par leur prénom") peut dériver vers du copywriting non-tech. Cadrer avec une section "implications techniques" à chaque assertion.

### L9 — `README.md` database line 186-189 : "13 tables" — j'en compte 14
Tables : households, household_members, member_preferences, member_taste_vectors, recipes, recipe_embeddings, ingredients, recipe_ingredients, recipe_feedbacks, weekly_plans, planned_meals, shopping_lists, fridge_items, weekly_books, subscriptions = **15 tables**. La checklist est incorrecte.

### L10 — Seed data `07-seed-data.sql:17` : `session_replication_role = replica` désactive **tous** les triggers
Y compris ceux qu'on voudrait garder (`updated_at`). Acceptable pour un seed, mais documenter.

### L11 — `ux-research/personas.md` : aucune donnée brute justifie les chiffres ("80-100€/mois gaspi")
C'est de la Phase 0 discovery — OK. Mais marquer explicitement `[hypothèse non validée]` pour chaque assertion non sourcée.

### L12 — `infra/README.md:186-195` : l'index des livrables ne liste pas `README.md` avec sa propre ligne tout en l'incluant dans la liste. Auto-référence circulaire.

### L13 — Pas de `pnpm-workspace.yaml` dans les livrables (il est juste mentionné)
Créer un fichier `12-pnpm-workspace.yaml` pour compléter.

### L14 — `Makefile` dans infra/README.md : pas de target `migrate` pour Alembic
Ajouter `make migrate` et `make migrate-down` pour l'ergonomie.

### L15 — `ANTHROPIC_MAX_TOKENS=4096` hardcodé dans env template
Faible valeur pour les agents RECIPE_SCOUT qui génèrent des recettes structurées. Recommander `8192` minimum.

---

## Points forts

1. **Isolation multi-tenant SQL**: quasi parfaite. FORCE RLS systématique, `get_current_household_id()` avec `SECURITY DEFINER + search_path` est une bonne pratique rare et bien documentée. L'explication du piège auth.uid() (lignes 10-18 de `03-rls-policies.sql`) montre une vraie maturité.
2. **Documentation de pièges ("Pièges connus")** : le `README.md` de la DB liste 6 pièges réels (dimension vector, auth.uid, Realtime+RLS, pgBouncer, ef_search, FORCE RLS) — excellent pour l'onboarding d'un nouveau dev.
3. **Architecture multi-stage Docker** propre, non-root user, labels OCI standard. Choix de uv (0.5.18 pinned) reproductible.
4. **pgvector + HNSW + dim=384** parfaitement aligné avec la ROADMAP (sentence-transformers/all-MiniLM-L6-v2).
5. **Design tokens** : palette complète HSL avec contraste WCAG documenté pour CHAQUE teinte — rigueur exemplaire. tailwind.config.ts bien synchronisé avec `02-design-tokens.md`.
6. **Stratégie de secrets Doppler** : bonne analyse comparative, plan de rotation documenté, fallback Vercel/Railway natifs si besoin.
7. **Commentaires SQL en français** tous pédagogiques et orientés "pourquoi" — conformes à la règle du CLAUDE.md.
8. **Seed data** : utilise des UUIDs prévisibles (`a1000000-...`) pour faciliter les tests, `ON CONFLICT DO NOTHING` partout, vérification finale avec `ASSERT` dans un bloc DO. Très solide.
9. **Coverage fail-under 80%** appliqué dans le CI — cohérent avec les règles `testing.md`.
10. **Alignement agents IA ↔ tables DB** : la matrice `README.md:273-281` est exactement ce qu'un architecte veut voir.
11. **Branch protection + CODEOWNERS + PR template** documentés et cohérents avec GitFlow simplifié.

---

## Verdict : **GO WITH FIXES** pour Phase 1

La Phase 0 est **solide sur les fondamentaux** (schéma DB, RLS, infra, design system, UX) mais **4 issues CRITIQUES** doivent être corrigées avant d'entamer Phase 1 :

- **C3** (RLS DELETE manquante) et **C4** (récursion INSERT household_members) sont bloquantes fonctionnellement pour l'onboarding.
- **C5** (agrégation `get_household_constraints`) fait courir un risque de bug métier silencieux.
- **H2** (`$PORT` hardcodé Dockerfile) est un boom immédiat au premier déploiement Railway.
- **H4** (rate limiting absent) viole directement une règle non-négociable ROADMAP.

Les issues HIGH restantes (H1, H3, H5–H9) doivent être ajoutées au backlog de début Phase 1 (semaine 1). Les MEDIUM et LOW peuvent être intégrés progressivement.

**Temps estimé pour passer en GO** : 1,5 à 2 jours de travail ciblé (C3, C4, C5, H1, H2, H4, H6, H9). Après cela, la base est prête à absorber Phase 1 (implémentation agents + endpoints FastAPI + premier onboarding UX).

---

## Annexe — Checklist de re-review avant merge Phase 1

- [ ] C2, C3, C4, C5 corrigés et testés avec pgTAP
- [ ] H1 `.dockerignore` créé, buildcontext vérifié < 10 MB
- [ ] H2 Dockerfile `$PORT` propagé, testé avec `docker run -e PORT=9000`
- [ ] H3 policies `planned_meals` limitées à `status='draft'`
- [ ] H4 document `12-rate-limiting-strategy.md` ajouté + tickets de suivi ouverts
- [ ] H6 `.gitleaks.toml` créé, CI passe en vert
- [ ] H8 `08-realtime-publication.sql` ajouté
- [ ] H9 `audit_log` ajouté en Phase 0.6 ou tout début Phase 1
- [ ] L9 compte corrigé (15 tables)
- [ ] M13 cohérence B2C / CLAUDE.md corrigée
