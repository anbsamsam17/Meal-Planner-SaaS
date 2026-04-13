# Debug Audit — Phase 0 MealPlanner SaaS
> Date : 2026-04-12 | Auditeur : Claude Debugger | Scope : tous les fichiers exécutables Phase 0

---

## Bugs détectés (par fichier)

---

### 00-setup-extensions.sql

- **[LOW]** Le commentaire ligne 8 dit `gen_random_uuid() (natif PG16)` puis installe `uuid-ossp` "pour compatibilité". Mais si le seul usage dans 01-schema-core.sql est `gen_random_uuid()` (natif, sans uuid-ossp), l'extension est inutile. Pas un bug bloquant, mais génère une fausse dépendance documentée.
  - Symptôme : confusion lors d'une migration qui supprimerait uuid-ossp en pensant qu'elle est unused.
  - Fix : clarifier dans le commentaire que uuid-ossp est optionnelle et indiquer si un outil tiers la requiert explicitement.

---

### 01-schema-core.sql

- **[HIGH]** `subscriptions` a `UNIQUE (household_id)` mais aussi `stripe_sub_id TEXT NOT NULL UNIQUE`. La contrainte UNIQUE sur `household_id` empêche un foyer d'avoir deux abonnements successifs (ex : annulation puis réabonnement crée une nouvelle ligne → conflit). En pratique Stripe peut créer un nouveau `stripe_sub_id` après annulation. L'upsert ou la suppression de l'ancienne ligne doit être géré côté webhook, sans quoi l'INSERT échouera silencieusement côté FastAPI.
  - Symptôme : `duplicate key value violates unique constraint "subscriptions_household_id_key"` au réabonnement.
  - Fix : soit retirer `UNIQUE (household_id)` et gérer le "plan actif" via un filtre `WHERE status = 'active'`, soit documenter que le webhook doit faire un `ON CONFLICT (household_id) DO UPDATE`.

- **[MEDIUM]** `weekly_plans.week_start DATE` — le commentaire dit "toujours un lundi, validé côté application et trigger", mais aucun trigger ni contrainte CHECK ne l'enforce en base. Si l'application a un bug et insère un mercredi, la donnée corrompue passe silencieusement.
  - Symptôme : plans avec week_start au mauvais jour, groupements UI cassés.
  - Fix : ajouter `CHECK (EXTRACT(DOW FROM week_start) = 1)` (DOW=1 = lundi en PostgreSQL).

- **[MEDIUM]** `recipe_ingredients` a comme PK `(recipe_id, ingredient_id)`. Cela interdit d'avoir le même ingrédient deux fois dans une recette (ex : "beurre" à l'étape 1 et "beurre fondu" à l'étape 3). La colonne `notes` permet de différencier mais la contrainte bloque l'insert.
  - Symptôme : impossible d'ajouter un ingrédient en double préparation dans une recette.
  - Fix : utiliser un `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` et une contrainte `UNIQUE (recipe_id, ingredient_id, notes)` ou supprimer la contrainte et gérer la déduplication applicativement.

- **[LOW]** `member_preferences.budget_pref CHECK (budget_pref IN ('économique', 'moyen', 'premium'))` — valeurs avec accents dans un CHECK. Fonctionne en UTF-8 mais peut poser des problèmes dans des outils CLI ou migrations Alembic si l'encoding de la connexion n'est pas UTF-8.
  - Fix : utiliser des valeurs ASCII (`low`, `medium`, `premium`) ou s'assurer que `client_encoding=UTF8` est forcé dans la DATABASE_URL.

---

### 02-indexes.sql

- **[MEDIUM]** `COMMENT ON INDEX recipes_slug_key` — cet index s'appelle `recipes_slug_key` (nom PostgreSQL par défaut pour les contraintes UNIQUE). Si le nom interne de la contrainte générée est différent selon la version PG ou l'ordre de création, ce COMMENT échouera avec `ERROR: index "recipes_slug_key" does not exist`.
  - Symptôme : erreur à l'exécution du fichier si PostgreSQL a nommé la contrainte autrement.
  - Fix : utiliser `COMMENT ON CONSTRAINT recipes_slug_key ON recipes IS '...'` ou nommer explicitement la contrainte dans 01-schema-core.sql : `CONSTRAINT recipes_slug_key UNIQUE (slug)`.

- **[LOW]** Aucun index CONCURRENTLY dans le fichier, mais le commentaire d'en-tête dit "CONCURRENTLY préférables en production". En réalité, `CREATE INDEX CONCURRENTLY` ne peut pas s'exécuter dans une transaction. Si ces scripts sont exécutés via Alembic dans une transaction implicite, tous les CONCURRENTLY échoueront. Aucun CONCURRENTLY n'est utilisé ici, donc pas de bug immédiat, mais le commentaire crée une fausse attente.
  - Fix : documenter dans le header que les CONCURRENTLY devront être ajoutés manuellement via un script de migration hors-transaction pour les bases de données en production avec données existantes.

---

### 03-rls-policies.sql

- **[CRITICAL]** `household_members_update` a une clause `USING` mais **pas de `WITH CHECK`**. Sans `WITH CHECK`, un utilisateur malveillant peut faire un UPDATE qui déplace un membre vers un autre `household_id` (il vérifie qu'il a accès en lecture via USING, mais l'écriture n'est pas revalidée). Il pourrait s'approprier des membres d'autres foyers.
  - Symptôme : escalade de privilèges inter-tenant possible via UPDATE sur household_members.
  - Fix : ajouter `WITH CHECK (household_id = get_current_household_id())` identique à la clause USING.

- **[CRITICAL]** `member_preferences_update` a une clause `USING` mais **pas de `WITH CHECK`**. Un membre pourrait faire un UPDATE de ses préférences en changeant le `member_id` pour pointer vers un membre d'un autre foyer — si la contrainte FK ne le bloque pas et que le sujet de l'UPDATE est dans son foyer mais la cible ne l'est pas.
  - Symptôme : pollution des préférences d'un membre d'un autre foyer via UPDATE.
  - Fix : ajouter `WITH CHECK (member_id IN (SELECT id FROM household_members WHERE household_id = get_current_household_id()))`.

- **[HIGH]** `fridge_items_update` a une clause `USING` mais **pas de `WITH CHECK`**. Un utilisateur peut lire un fridge_item de son foyer et faire un UPDATE en changeant le `household_id` pour celui d'un autre foyer (si le FK l'autorise).
  - Symptôme : exfiltration de données de frigo entre tenants.
  - Fix : ajouter `WITH CHECK (household_id = get_current_household_id())`.

- **[HIGH]** `planned_meals_update` manque de `WITH CHECK`. Même risque : UPDATE peut déplacer un `plan_id` vers un plan d'un autre foyer.
  - Fix : ajouter `WITH CHECK (plan_id IN (SELECT id FROM weekly_plans WHERE household_id = get_current_household_id()))`.

- **[MEDIUM]** `get_current_household_id()` est créée dans `04-triggers-functions.sql` et utilisée dans `03-rls-policies.sql`. Le header de 03 dit "04 avant 03" mais l'ordre des fichiers numérotés (03 avant 04) est trompeur. Si un développeur exécute les scripts dans l'ordre numérique naturel, il obtiendra `ERROR: function get_current_household_id() does not exist`.
  - Fix : renommer pour que l'ordre reflète l'exécution réelle (ex : `03-triggers-functions.sql`, `04-rls-policies.sql`) ou ajouter un script d'orchestration `run-all.sh` qui impose l'ordre correct.

- **[LOW]** `households_insert` a `WITH CHECK (true)` — tout utilisateur authentifié peut créer autant de foyers qu'il veut. Pas de limite. Un attaquant peut créer des milliers de foyers vides.
  - Fix : cette politique est acceptable en phase 0 si la création de foyer passe par l'API qui rate-limite, mais il faut documenter que le rate-limiting API est la seule protection ici.

---

### 04-triggers-functions.sql

- **[MEDIUM]** `get_household_constraints()` utilise `MIN(mp.budget_pref)` pour trouver le budget le plus "économique". `MIN()` sur TEXT retourne la valeur lexicographiquement inférieure, pas la plus économique. L'ordre lexicographique de `['économique', 'moyen', 'premium']` est : `'moyen' < 'premium' < 'économique'` (tri unicode, 'é' > 'p' > 'm'). Résultat : `MIN()` retourne `'moyen'` quand un membre a `'économique'` et un autre `'premium'`, au lieu de `'économique'`.
  - Symptôme : la contrainte budget n'est pas respectée, des recettes premium sont proposées à des foyers économiques.
  - Fix : utiliser `CASE WHEN 'économique' = ANY(ARRAY_AGG(mp.budget_pref)) THEN 'économique' WHEN 'moyen' = ANY(...) THEN 'moyen' ELSE 'premium' END` ou mapper sur des entiers (`économique=1, moyen=2, premium=3`) et utiliser `MIN()` sur l'entier.

- **[MEDIUM]** `cleanup_old_embeddings()` n'a pas `SET search_path TO ''` contrairement à `get_current_household_id()`. Comme elle est appelée par une tâche Celery (pas dans un contexte RLS), c'est moins critique, mais incohérent avec la politique de sécurité du projet.
  - Fix : ajouter `SET search_path TO ''` et utiliser `public.recipe_embeddings` et `public.recipes` explicitement.

- **[LOW]** `validate_recipe_quality()` est un trigger `BEFORE INSERT OR UPDATE`. Elle bloque aussi les UPDATE de champs non liés à `quality_score` (ex : `UPDATE recipes SET photo_url = '...'`). Si la recette avait `quality_score = 0.5` au moment de l'insertion (impossible avec le trigger, mais via `session_replication_role = replica` comme dans le seed), toute mise à jour ultérieure sera bloquée.
  - Fix : ajouter la condition `IF TG_OP = 'INSERT' OR NEW.quality_score <> OLD.quality_score THEN` pour ne vérifier le score que sur INSERT ou si le score change.

- **[INFO]** `trigger_set_updated_at()` n'a pas `SET search_path TO ''`. Pour un trigger SECURITY DEFINER qui n'accède pas à d'autres tables, c'est bénin, mais bonne pratique à appliquer systématiquement.

---

### 07-seed-data.sql

- **[HIGH]** `SET session_replication_role = replica` désactive **tous** les triggers, y compris les triggers d'intégrité référentielle et les triggers `updated_at`. Si un développeur ajoute accidentellement une recette avec `quality_score < 0.6` dans le seed (erreur de frappe), elle passera sans erreur. La vérification finale `ASSERT` ne vérifie pas la qualité des recettes insérées.
  - Symptôme : données de seed corrompues silencieusement si quality_score est mal saisi.
  - Fix : ne désactiver les triggers que si nécessaire (ici, pour les embeddings factices) via `ALTER TABLE recipe_embeddings DISABLE TRIGGER ALL` ciblé, plutôt que désactiver session entière.

- **[MEDIUM]** `ON CONFLICT DO NOTHING` sur `households` et `household_members` sans spécifier la contrainte de conflit. PostgreSQL accepte la syntaxe mais c'est une mauvaise pratique — si le schéma change et qu'une nouvelle contrainte UNIQUE est ajoutée, le `DO NOTHING` peut masquer un conflit inattendu.
  - Fix : utiliser `ON CONFLICT (id) DO NOTHING` ou `ON CONFLICT ON CONSTRAINT households_pkey DO NOTHING` de façon explicite.

- **[LOW]** Les embeddings factices utilisent `array_fill(0.001::float4, ARRAY[384])` — tous identiques. Cela signifie que toutes les recettes seed ont la même similarité cosine de 1.0 entre elles. Les tests de recommandation sembleront fonctionner mais retourneront n'importe quelle recette avec le même score.
  - Symptôme : tests d'intégration de recommandation non discriminants — faux positifs.
  - Fix : générer des vecteurs légèrement différents (`0.001`, `0.002`, `0.003`) ou documenter que les tests de recommandation nécessitent de vrais embeddings.

---

### 02-docker-compose.dev.yml

- **[HIGH]** `minio` healthcheck utilise `CMD celery...` — **NON**, c'est le MinIO healthcheck : `CMD mc ready local`. Le problème est que `mc` n'est pas installé dans l'image `minio/minio:latest` — `mc` est le client MinIO, dans l'image `minio/mc`. Le healthcheck échouera systématiquement, ce qui empêchera `minio-init` de démarrer (il attend `service_healthy`).
  - Symptôme : `minio-init` ne démarre jamais, les buckets ne sont pas créés, l'API ne peut pas uploader de PDFs.
  - Fix : remplacer par `CMD ["curl", "-f", "http://localhost:9000/minio/health/live"]` ou `CMD ["curl", "-f", "http://localhost:9000/minio/health/ready"]` — MinIO expose ces endpoints nativement.

- **[MEDIUM]** `init-scripts/postgres` est monté depuis `./init-scripts/postgres` (chemin relatif au fichier docker-compose). Si docker-compose est lancé depuis un répertoire différent, le mount échoue silencieusement ou avec une erreur de volume. De plus, le dossier `init-scripts/` n'existe pas dans l'arborescence `phase-0/infra/` auditée.
  - Symptôme : pgvector non activé, schéma non créé au démarrage du container.
  - Fix : soit créer le répertoire et les scripts d'init, soit supprimer ce mount et indiquer que les migrations sont gérées par Alembic post-démarrage.

- **[LOW]** `mailhog/mailhog:latest` — tag `latest` non épinglé. L'image mailhog n'est plus maintenue depuis 2021. Risque de changements breaking si l'image est repullée.
  - Fix : utiliser `mailhog/mailhog:v1.0.1` (dernière version stable) ou migrer vers `axllent/mailpit` (alternative maintenue).

- **[INFO]** `redis` est configuré avec `--maxmemory-policy allkeys-lru` et `--appendonly yes`. Ces deux options sont en tension : AOF garantit la persistence (ne pas perdre les tâches Celery), mais `allkeys-lru` peut évincer des clés Celery non encore consommées. En dev c'est acceptable mais à documenter pour la production.

---

### 03-apps-api-Dockerfile

- **[MEDIUM]** Le healthcheck utilise une variable shell `${PORT}` dans la forme `CMD` Python string :
  ```
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1
  ```
  La syntaxe `HEALTHCHECK CMD` en shell form (sans `[]`) interprète les variables d'environnement. Mais ici, la forme est ambigüe — si Docker l'interprète comme exec form, `${PORT}` ne sera pas substitué. Tester avec `docker inspect` pour confirmer que le port est bien résolu à 8000.
  - Fix : utiliser la shell form explicite ou hardcoder le port : `CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]`.

- **[MEDIUM]** `ENTRYPOINT ["uvicorn", ..., "--port", "8000", ...]` — le port est hardcodé à 8000 dans l'ENTRYPOINT mais la variable d'env `PORT=8000` est définie. Si Railway injecte `PORT=3000`, uvicorn continuera d'écouter sur 8000 et le healthcheck Railway échouera.
  - Fix : utiliser un script d'entrée shell qui lit `$PORT` : `ENTRYPOINT ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers 2 --no-access-log"]`.

- **[LOW]** `--workers 2` est hardcodé dans l'ENTRYPOINT. Uvicorn avec workers multiples ne supporte pas correctement le hot-reload. En production, 2 workers peuvent être insuffisants ou excessifs selon la RAM Railway. Rendre configurable via `$WEB_CONCURRENCY`.

---

### 04-apps-worker-Dockerfile

- **[HIGH]** L'ENTRYPOINT Celery n'a pas de signal handler explicite. Celery en mode container doit recevoir SIGTERM et le propager aux workers enfants avant de s'arrêter. Sans `--pidfile` ni trap SIGTERM dans un wrapper, Railway/Kubernetes peut tuer le container en plein traitement d'une tâche longue (scraping, génération PDF) sans que la tâche soit marquée comme échec ou réessayée.
  - Symptôme : tâches perdues silencieusement lors des déploiements Railway.
  - Fix : ajouter `--max-tasks-per-child=100` pour le recyclage mémoire, et s'assurer que la tâche Celery est configurée avec `acks_late=True` + `reject_on_worker_lost=True` pour la reprise automatique.

- **[MEDIUM]** Le healthcheck Celery `celery -A src.app inspect ping -d "celery@$(hostname)" --timeout 10` — `$(hostname)` dans un `CMD ["..."]` exec form n'est pas interprété par le shell. Docker exec form ne passe pas par `/bin/sh`, donc `$(hostname)` sera littéral et la commande échouera.
  - Symptôme : container Celery toujours `unhealthy` même quand il fonctionne.
  - Fix : utiliser la shell form : `CMD celery -A src.app inspect ping -d "celery@$$(hostname)" --timeout 10 || exit 1` ou `CMD ["sh", "-c", "celery -A src.app inspect ping -d celery@$(hostname) --timeout 10 || exit 1"]`.

---

### 05-github-workflows-ci.yml

- **[HIGH]** `build-docker` référence `file: apps/api/Dockerfile` et `file: apps/worker/Dockerfile` mais les Dockerfiles ont pour contexte `.` (racine du repo). Les Dockerfiles utilisent `COPY apps/api/src ./src` — ce chemin est relatif au contexte de build (`.`). Si le `context: .` est bien la racine du monorepo, ça devrait fonctionner. Cependant, les fichiers Dockerfiles dans le repo sont nommés `03-apps-api-Dockerfile` et `04-apps-worker-Dockerfile`, pas `Dockerfile`. Le workflow référence `apps/api/Dockerfile` — ce chemin n'existera **jamais** si les fichiers ne sont pas copiés/renommés au bon endroit.
  - Symptôme : `ERROR: failed to solve: failed to read dockerfile: open apps/api/Dockerfile: no such file or directory`.
  - Fix : soit nommer les Dockerfiles `apps/api/Dockerfile` et `apps/worker/Dockerfile` dans l'arborescence réelle, soit corriger les chemins `file:` dans le workflow.

- **[MEDIUM]** Le job `security` lance `pip-audit` sans installer les dépendances Python d'abord (`uv sync` est absent avant `pip-audit`). `pip-audit` dans le contexte `uv run` peut nécessiter que l'environnement venv existe.
  - Symptôme : `pip-audit: command not found` ou `No Python packages found`.
  - Fix : ajouter un step `run: uv sync --frozen` avant le step `pip-audit` dans le job `security`, ou vérifier que `pip-audit` est dans les dev-dependencies du `pyproject.toml`.

- **[MEDIUM]** Les permissions du workflow sont par défaut (non déclarées au niveau root). Seul le job `build-docker` déclare `permissions: contents: read / packages: write`. Les autres jobs héritent des permissions par défaut GitHub Actions qui incluent `contents: write` — plus large que nécessaire.
  - Fix : ajouter au niveau root du workflow : `permissions: contents: read` et surcharger par job si besoin.

- **[LOW]** `concurrency.cancel-in-progress: true` annule le run précédent sur la même branche. Sur `main`, si un deploy CI est en cours et qu'un hotfix est pushé, le deploy de la version précédente sera annulé au milieu, potentiellement laissant Railway dans un état intermédiaire.
  - Fix : exclure `main` du `cancel-in-progress` : `cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`.

---

### 09-env-template.env

- **[HIGH]** `STRIPE_SECRET_KEY=sk_test_...` et `STRIPE_WEBHOOK_SECRET=whsec_...` — des valeurs placeholder commençant par `sk_test_` et `whsec_` qui ont le **format exact** des vraies clés Stripe. Gitleaks peut ne pas les détecter comme faux positifs (ils correspondent au pattern). Un développeur qui ne lit pas le commentaire pourrait les copier et les utiliser.
  - Fix : utiliser des valeurs clairement fictives : `STRIPE_SECRET_KEY=sk_test_REPLACE_ME` et `STRIPE_WEBHOOK_SECRET=whsec_REPLACE_ME`.

- **[MEDIUM]** `NEXT_PUBLIC_SUPABASE_URL` et `NEXT_PUBLIC_SUPABASE_ANON_KEY` sont définis, mais `SUPABASE_URL` et `SUPABASE_ANON_KEY` sont aussi présents (sans prefix). Le code devra choisir lequel utiliser côté serveur (FastAPI vs Next.js). Aucun commentaire n'indique lequel est utilisé par quel service — risque de confusion et de valeurs désynchronisées.
  - Fix : clarifier dans le commentaire que `SUPABASE_URL` est pour FastAPI backend et `NEXT_PUBLIC_SUPABASE_URL` pour Next.js client, et qu'elles doivent avoir la même valeur.

- **[LOW]** `SENTRY_TRACES_SAMPLE_RATE=1.0` — valeur de production qui capture 100% des traces. En production, cela épuisera rapidement le quota Sentry et génèrera des coûts.
  - Fix : changer la valeur par défaut à `0.1` et ajouter un commentaire : `# 1.0 en dev, 0.1 en prod`.

- **[INFO]** Aucune variable pour `CELERY_BROKER_URL` — le worker Celery utilise probablement `REDIS_URL` comme broker mais ce n'est pas explicite dans le template. Si Celery est configuré pour lire `CELERY_BROKER_URL` et que seul `REDIS_URL` est défini, le worker ne démarrera pas.
  - Fix : ajouter `CELERY_BROKER_URL=redis://localhost:6379/0` et `CELERY_RESULT_BACKEND=redis://localhost:6379/0`.

---

### 03-tailwind-config.ts

- **[HIGH]** `theme.screens`, `theme.fontFamily`, `theme.fontSize`, `theme.spacing`, `theme.borderRadius` sont définis dans `theme` (pas dans `theme.extend`). Cela **écrase complètement** les valeurs par défaut Tailwind — aucun autre breakpoint, font, taille ou espacement Tailwind natif ne sera disponible. Par exemple, `max-w-screen-xl` sera cassé car les breakpoints natifs Tailwind (`2xl: 1400px` shadcn/ui) ne seront plus là.
  - Symptôme : classes Tailwind natives comme `container`, `max-w-*`, `text-gray-*` (gray non défini dans la palette custom) seront invalides — erreurs silencieuses en CSS (classes ignorées).
  - Fix : déplacer `screens`, `fontFamily`, `fontSize`, `spacing`, `borderRadius` dans `theme.extend` pour fusionner avec les valeurs par défaut plutôt que les remplacer — sauf si le remplacement complet est intentionnel et documenté.

- **[MEDIUM]** Le content paths ne couvre que `./src/app/**`, `./src/components/**`, `./src/lib/**`, `./src/hooks/**`, `./components/**`. Si des composants shadcn/ui sont dans `./components/ui/` (hors `src`), ils sont couverts. Mais les packages du monorepo (`../../packages/**`) ne sont pas couverts. Si un package partagé émet des classes Tailwind, elles seront purgées en production.
  - Fix : ajouter `"../../packages/**/*.{js,ts,jsx,tsx}"` si le monorepo a des packages partagés avec des composants.

- **[LOW]** Le plugin `require("@tailwindcss/typography")` et `require("@tailwindcss/forms")` utilisent `require()` dans un fichier `.ts` avec `import type` en haut. Cela mélange CJS et ESM. Selon la config `tsconfig.json` du projet, cela peut provoquer une erreur TypeScript (`Cannot find module` ou `require is not defined`).
  - Fix : utiliser `import typography from '@tailwindcss/typography'; import forms from '@tailwindcss/forms';` et les référencer dans `plugins: [typography, forms({ strategy: 'class' })]`.

- **[INFO]** Pas de path monorepo pour les packages partagés (`../../packages/**/*`) — voir point MEDIUM ci-dessus. En monorepo avec `apps/web` et `packages/ui`, c'est un piège classique.

---

## Pièges classiques évités (félicitations)

- `SECURITY DEFINER` + `SET search_path TO ''` sur `get_current_household_id()` — protection injection search_path correcte
- `FORCE ROW LEVEL SECURITY` sur toutes les tables tenant-scoped — défense en profondeur correcte
- Embeddings dans une table séparée `recipe_embeddings` — excellente décision de performance
- `HNSW` avec `vector_cosine_ops` — choix correct pour la similarité cosine
- Index partiels sur `weekly_plans` (draft uniquement) et `weekly_books` (non-notifiés) — optimisation pertinente
- `STABLE` + cache sur `get_current_household_id()` — évite la répétition de sous-requête par row
- Vecteur à `0.001` au lieu de `0.0` pour éviter la division par zéro en cosine — correct
- Multi-stage Dockerfile avec `--no-install-project` pour le cache des deps — best practice Docker
- `ENTRYPOINT` en exec form (tableau JSON) pour la propagation des signaux sur l'API — correct
- `concurrency` GitHub Actions avec `cancel-in-progress` — évite les congestions CI
- `pnpm --frozen-lockfile` et `uv sync --frozen` — builds reproductibles

---

## Pièges classiques présents

| # | Piège | Fichier | Criticité |
|---|-------|---------|-----------|
| 1 | UPDATE policies sans WITH CHECK → risque cross-tenant | 03-rls-policies.sql | CRITICAL |
| 2 | MIN(TEXT) pour ordre sémantique → budget_pref mal agrégé | 04-triggers-functions.sql | MEDIUM |
| 3 | theme vs theme.extend → écrasement Tailwind natif | 03-tailwind-config.ts | HIGH |
| 4 | $(hostname) en exec form → healthcheck Celery mort | 04-apps-worker-Dockerfile | MEDIUM |
| 5 | MinIO healthcheck avec mc absent de l'image | 02-docker-compose.dev.yml | HIGH |
| 6 | Dockerfile path/nom incorrect dans CI | 05-github-workflows-ci.yml | HIGH |
| 7 | Port hardcodé en ENTRYPOINT vs variable $PORT | 03-apps-api-Dockerfile | MEDIUM |

---

## Commandes de test recommandées

```bash
# 1. Valider le SQL (PostgreSQL requis avec pgvector)
psql -U mealplanner -d mealplanner_dev -f phase-0/database/00-setup-extensions.sql
psql -U mealplanner -d mealplanner_dev -f phase-0/database/04-triggers-functions.sql
psql -U mealplanner -d mealplanner_dev -f phase-0/database/01-schema-core.sql
psql -U mealplanner -d mealplanner_dev -f phase-0/database/02-indexes.sql
psql -U mealplanner -d mealplanner_dev -f phase-0/database/03-rls-policies.sql
psql -U mealplanner -d mealplanner_dev -f phase-0/database/07-seed-data.sql

# 2. Vérifier les WITH CHECK manquants (requête psql)
SELECT polname, polcmd, polwithcheck
FROM pg_policy
WHERE polwithcheck IS NULL
  AND polcmd IN ('w', 'a')  -- UPDATE et INSERT
ORDER BY polrelid, polname;

# 3. Valider le Tailwind TypeScript
npx tsc --noEmit --strict phase-0/design-system/03-tailwind-config.ts

# 4. Builder les images Docker (depuis la racine du monorepo)
docker build -f apps/api/Dockerfile -t mealplanner-api:test . --progress=plain
docker build -f apps/worker/Dockerfile -t mealplanner-worker:test . --progress=plain

# 5. Tester le docker-compose dev
docker compose -f phase-0/infra/02-docker-compose.dev.yml up -d
docker compose -f phase-0/infra/02-docker-compose.dev.yml ps
# Vérifier que minio est healthy avant minio-init :
docker inspect mealplanner_minio | grep -A5 '"Health"'

# 6. Valider le workflow GitHub Actions (dry-run)
# Installer act : https://github.com/nektos/act
act push --dry-run

# 7. Tester le healthcheck Celery (bug $(hostname))
docker run --rm mealplanner-worker:test \
  sh -c 'celery -A src.app inspect ping -d "celery@$(hostname)" --timeout 5 || echo FAIL'

# 8. Vérifier le budget_pref MIN() bug
psql -c "SELECT MIN(val) FROM (VALUES ('économique'), ('moyen'), ('premium')) AS t(val);"
# Résultat attendu : 'moyen' (bug) au lieu de 'économique'
```

---

## Verdict : FIXES REQUIRED

**Bloquants avant premier déploiement :**
1. `WITH CHECK` manquants sur 4 policies UPDATE (faille sécurité cross-tenant)
2. Healthcheck MinIO cassé (`mc` absent de l'image) → minio-init jamais lancé
3. Healthcheck Celery cassé (`$(hostname)` en exec form) → container toujours unhealthy
4. Dockerfile paths incorrects dans le workflow CI → build-docker échoue au premier push main
5. `theme` vs `theme.extend` dans Tailwind → classes natives Tailwind cassées

**Non bloquants mais à corriger avant Phase 1 :**
- `MIN(budget_pref)` sémantiquement incorrect
- Port hardcodé dans ENTRYPOINT API
- SIGTERM non géré dans le worker Celery
- `week_start` sans contrainte CHECK DOW=1
- Ordre d'exécution des scripts SQL (04 avant 03) non reflété dans la numérotation
