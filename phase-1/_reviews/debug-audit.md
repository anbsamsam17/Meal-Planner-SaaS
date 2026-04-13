# Debug Audit — Phase 1 MealPlanner
> Date : 2026-04-12 | Auditeur : Claude Debugger | Scope : audit runtime Phase 1 (~150 fichiers)

---

## Bugs CRITICAL (code ne démarre pas)

### BUG #1 — `book_generator` module inexistant référencé dans Celery [CRITICAL]
**Fichier :** `apps/worker/src/app.py` — lignes 83-88 et 144
**Symptôme :** `celery -A apps.worker.src.app worker` démarre mais le Celery Beat schedule tente d'exécuter `src.agents.book_generator.tasks.batch_generate_missing_books` (planifié chaque dimanche). Au premier tick du scheduler, Celery lève `ModuleNotFoundError: No module named 'src.agents.book_generator'` et le beat se crashe.
**Root cause :** Le répertoire `apps/worker/src/agents/book_generator/` n'existe pas. `task_routes` référence 2 tâches book_generator qui ne peuvent pas être importées. Le module n'est pas dans `include=` (qui ne liste que `recipe_scout`), ce qui retarde l'erreur au premier usage au lieu de la lever au démarrage — faux sentiment de sécurité.
**Fix :** Créer le stub `apps/worker/src/agents/book_generator/__init__.py` et `tasks.py` avec des placeholders `@celery_app.task` vides, ou retirer les entrées book_generator de `task_routes` et `beat_schedule` jusqu'à l'implémentation.

---

### BUG #2 — `SPOONACULAR_API_KEY` vs `SPOONACULAR_KEY` : nom de variable incohérent [CRITICAL]
**Fichier :** `apps/api/src/core/config.py` ligne 77 vs `.env.example` ligne 228
**Symptôme :** Au démarrage FastAPI, `Settings()` tente de lire `SPOONACULAR_API_KEY` depuis l'environnement. Le `.env.example` (copié en `.env.local` par les devs) définit `SPOONACULAR_KEY=`. Pydantic Settings v2 ne trouve pas `SPOONACULAR_API_KEY` → `ValidationError` → l'API refuse de démarrer.
**Root cause :** Divergence de nommage entre `config.py` (`SPOONACULAR_API_KEY`) et `.env.example` (`SPOONACULAR_KEY`). La variable est déclarée sans `default` dans Settings donc elle est **obligatoire** — pas de fallback possible.
**Fix :** Unifier sur `SPOONACULAR_API_KEY` dans `.env.example` (ligne 228 : `SPOONACULAR_KEY=` → `SPOONACULAR_API_KEY=`).

---

### BUG #3 — `difficulty` : contrainte CHECK `BETWEEN 1 AND 3` mais agent insère 1-5 [CRITICAL]
**Fichier :** `apps/api/src/db/models/recipe.py` ligne 105 vs `apps/worker/src/agents/recipe_scout/agent.py` lignes 515-517
**Symptôme :** Chaque recette "difficile" ou "très difficile" (difficulty=4 ou 5) provoque une violation de la contrainte PostgreSQL `ck_recipes_recipes_difficulty_check` → `IntegrityError` → recette non insérée + log d'erreur. En batch nocturne : potentiellement 20-30% des recettes françaises (Marmiton classe en "difficile") sont silencieusement perdues.
**Root cause :** Le modèle ORM déclare `CHECK (difficulty BETWEEN 1 AND 3)` (3 niveaux) mais le mapping dans `_insert_recipe()` génère `{"very_easy": 1, "easy": 2, "medium": 3, "hard": 4, "very_hard": 5}` (5 niveaux). Les valeurs 4 et 5 violent la contrainte.
**Fix :** Aligner sur 5 niveaux dans le modèle : `CHECK (difficulty BETWEEN 1 AND 5)` — ou remapper hard→3, very_hard→3 dans l'agent comme fallback immédiat.

---

### BUG #4 — `validate_recipe_quality` async appelée avec `await` depuis un agent asyncio mais bloque l'event loop [CRITICAL/HIGH]
**Fichier :** `apps/worker/src/agents/recipe_scout/agent.py` ligne 398 + `validator.py` ligne 242
**Symptôme :** `validate_recipe_quality()` est `async def` mais utilise `anthropic.Anthropic()` (client **synchrone**) et `client.messages.create()` (appel **bloquant**). Appelée avec `await` depuis `_process_single_recipe()` (contexte async), l'appel réseau Claude bloque l'event loop asyncio pendant 1-10 secondes par recette. Pour un batch de 100 recettes → temps CPU monopolisé, timeouts Redis possibles.
**Root cause :** Le SDK Anthropic a deux clients : `anthropic.Anthropic()` (sync) et `anthropic.AsyncAnthropic()` (async). Le validator utilise le client sync dans une coroutine async.
**Fix :** Remplacer `anthropic.Anthropic` par `anthropic.AsyncAnthropic` et `await client.messages.create(...)` dans `validator.py`.

---

### BUG #5 — `_insert_recipe` n'insère PAS dans `recipe_ingredients` [CRITICAL - DATA LOSS]
**Fichier :** `apps/worker/src/agents/recipe_scout/agent.py` lignes 449-566
**Symptôme :** La méthode `_insert_recipe` documente qu'elle écrit dans 3 tables (`recipes`, `recipe_ingredients`, `recipe_embeddings`) mais le code ne contient que 2 `INSERT INTO` : `recipes` et `recipe_embeddings`. La table `recipe_ingredients` n'est **jamais alimentée**. Les ingrédients normalisés passés en paramètre (`normalized_ingredients: list`) sont calculés, dédupliqués, passés à la fonction... puis ignorés silencieusement.
**Root cause :** L'implémentation est incomplète — le troisième INSERT a été oublié ou reporté sans TODO.
**Fix :** Ajouter l'INSERT dans `recipe_ingredients` après l'INSERT `recipes`, en itérant sur `normalized_ingredients` avec leur `canonical_name`, `quantity`, `unit`, `position`.

---

## Bugs HIGH (code démarre mais casse au 1er usage)

### BUG #A — `server.ts` : `cookies()` synchrone compatible Next.js 14 mais risque Next.js 15
**Fichier :** `apps/web/src/lib/supabase/server.ts` ligne 20
**Symptôme :** `const cookieStore = cookies()` (sans `await`) est correct pour Next.js 14 (déclaré dans `package.json` : `"next": "14.2.18"`). Mais le commentaire dit "Next.js 14" explicitement, indiquant une conscience du risque. Si le projet est mis à jour vers Next.js 15 sans adapter ce fichier → `TypeError: cookies() should be awaited`.
**Fix :** Aucune action immédiate (14.2.18 est installé), mais ajouter un commentaire de garde `// BREAKING CHANGE Next.js 15 : await cookies()` pour sécuriser la future mise à jour.

### BUG #B — `next-pwa` 5.6.0 : `withPWA(config)(nextConfig)` — API correcte mais génère un warning
**Fichier :** `apps/web/next.config.mjs` ligne 82-90
**Symptôme :** `next-pwa` 5.x retourne bien une fonction curryée (`withPWA(pwaOptions)` → function). `pwaConfig(nextConfig)` est syntaxiquement correct. Cependant `next-pwa` 5.6.0 n'est pas officiellement compatible avec Next.js 14 App Router — des warnings sur le service worker peuvent apparaître au build. Non bloquant au démarrage.

### BUG #C — `infra/docker/init-scripts/postgres` manquant
**Fichier :** `docker-compose.dev.yml` ligne 50
**Symptôme :** Le volume `./infra/docker/init-scripts/postgres:/docker-entrypoint-initdb.d:ro` monte un répertoire qui n'existe pas dans le monorepo (`ENOENT`). Docker Compose lève une erreur au `up` : `Bind mount source path does not exist`.
**Fix :** Créer `infra/docker/init-scripts/postgres/.gitkeep` ou retirer le volume si les migrations Alembic remplacent l'init SQL.

### BUG #D — `exc.limit.limit` AttributeError dans le handler 429 (hérité audit v2)
**Fichier :** `apps/api/src/core/rate_limit.py` ligne 149
**Symptôme :** `str(getattr(exc.limit, "limit", "inconnu"))` — l'objet `Limit` de slowapi expose `str(exc.limit)` directement, pas un attribut `.limit`. Le double `.limit.limit` retournera systématiquement `"inconnu"` dans le header `X-RateLimit-Limit`. Non bloquant mais header incorrect.

---

## Bugs MEDIUM

### BUG #M1 — `MemberTasteVector` importé deux fois dans `models/__init__.py` (F811 masqué)
**Fichier :** `apps/api/src/db/models/__init__.py` lignes 14 et 17
**Symptôme :** `from src.db.models.household import MemberTasteVector` (ligne 14) puis `from src.db.models.feedback import MemberTasteVector` (ligne 17, noqa: F811). Le second import écrase le premier. `feedback.py` ré-exporte `MemberTasteVector` depuis `household.py` — donc c'est le même objet, mais mypy peut signaler un conflit de type selon la version.
**Fix :** Retirer la ligne 14 du `__init__.py`, garder uniquement l'import via `feedback.py` (qui est le module "aggregateur" prévu).

### BUG #M2 — CI cache key `apps/api/uv.lock` inexistant (workspace `uv.lock` à la racine)
**Fichier :** `.github/workflows/ci.yml` ligne 119
**Symptôme :** `hashFiles('apps/api/uv.lock')` — dans un workspace uv, le `uv.lock` est à la **racine** du monorepo, pas dans `apps/api/`. Le hash sera toujours vide → le cache ne sera jamais restauré → ralentissement CI (+2-3 min par run) mais pas d'échec.
**Fix :** `hashFiles('uv.lock')` (racine).

### BUG #M3 — `pool_size=10, max_overflow=20` dans agent.py crée 30 connexions par run nocturne
**Fichier :** `apps/worker/src/agents/recipe_scout/agent.py` ligne 130
**Symptôme :** `create_async_engine(self.db_url, pool_size=5)` — 5 connexions OK pour le worker. Mais en parallèle avec l'API (pool_size=10, max_overflow=20 = 30 connexions) sur Supabase Free (60 connexions max) : 30 (API) + 5 (worker) = 35 par processus. En prod avec 2 API workers + 1 Celery worker = 65+ connexions → dépassement possible.
**Fix :** Utiliser `NullPool` pour l'agent Celery (batch nocturne = pas besoin de pool persistant).

---

## Pièges évités (points positifs)

1. **`statement_cache_size=0` présent** dans `session.py` (lignes 61-63) — correctement configuré pour pgBouncer en mode transaction (Supabase). Évite l'erreur `prepared statement "..." already exists`.
2. **Pydantic v2 natif** — `model_config = SettingsConfigDict(...)` utilisé partout, aucun `.dict()` ou `parse_obj()` détecté.
3. **NullPool dans Alembic** — `env.py` utilise `pool.NullPool` (ligne 153) — correct pour les migrations sur Supabase pgBouncer.
4. **`asyncio.run()` + fallback `new_event_loop()`** dans la tâche Celery nightly (tasks.py lignes 272-279) — gère correctement les contextes tests vs production.
5. **Modèles SQLAlchemy 2.0 stricts** — `Mapped[T]` + `mapped_column()` partout, aucun `Column()` legacy détecté.
6. **`volatile-lru` sur Redis** (docker-compose.dev.yml ligne 79) — le fix critique de l'audit v2 est bien présent, protège les messages Celery sans TTL.
7. **Middleware correlation ID** bien implémenté avec `ContextVar` + propagation dans la réponse HTTP.
8. **Next.js 14** avec `cookies()` synchrone — cohérent avec la version déclarée dans `package.json`.
9. **Tool use Anthropic** correctement structuré dans `validator.py` avec `tool_choice: {"type": "auto"}` et extraction via `block.type == "tool_use"`.
10. **RootProviders en `"use client"`** avec ThemeProvider → SupabaseProvider → QueryProvider — nesting correct, aucun hook dans un RSC détecté.

---

## Commandes de validation

### Python
```bash
# Synchronisation des dépendances
uv sync

# Vérification des imports (détecte BUG #1 book_generator)
uv run python -c "from apps.worker.src.app import celery_app; print('OK')"

# Lint
uv run ruff check apps/api/src apps/worker/src

# Types
uv run mypy apps/api/src apps/worker/src

# Tests
uv run pytest apps/api/tests/ apps/worker/tests/ -v

# Vérification contrainte difficulty (BUG #3)
psql "$DATABASE_URL" -c "\d+ recipes" | grep difficulty
```

### Next.js
```bash
pnpm install
pnpm --filter @mealplanner/web tsc --noEmit   # BUG TypeScript
pnpm --filter @mealplanner/web lint
pnpm --filter @mealplanner/web build          # Détecte BUG #2 env manquante
```

### Docker
```bash
# BUG #C : vérifier que le répertoire init-scripts existe
ls infra/docker/init-scripts/postgres || echo "MANQUANT — créer le répertoire"

# Validation compose
docker compose -f docker-compose.dev.yml config

# Démarrage complet
docker compose -f docker-compose.dev.yml up -d

# Vérifier healthchecks (attendre ~60s)
docker compose -f docker-compose.dev.yml ps
```

### Alembic
```bash
# Dry run SQL (vérifie la syntaxe sans toucher la DB)
cd apps/api && uv run alembic upgrade head --sql 2>&1 | head -50

# Application réelle (nécessite BUG #2 corrigé + infra Docker up)
cd apps/api && uv run alembic upgrade head
```

### Celery
```bash
# Vérification imports au démarrage (détecte BUG #1 book_generator)
uv run celery -A apps.worker.src.app inspect registered 2>&1 | head -30

# Worker (doit démarrer sans erreur)
uv run celery -A apps.worker.src.app worker --loglevel=info --queues=default,scraping,embedding,llm

# Beat (crashera au premier tick si BUG #1 non corrigé)
uv run celery -A apps.worker.src.app beat --loglevel=info
```

---

## Résumé des bugs par sévérité

| # | Bug | Fichier | Sévérité | Impact |
|---|-----|---------|----------|--------|
| 1 | `book_generator` module manquant | `worker/src/app.py` | CRITICAL | Beat crashe dimanche 22h |
| 2 | `SPOONACULAR_KEY` vs `SPOONACULAR_API_KEY` | `config.py` + `.env.example` | CRITICAL | API refuse de démarrer |
| 3 | `difficulty BETWEEN 1 AND 3` vs mapping 1-5 | `recipe.py` + `agent.py` | CRITICAL | IntegrityError sur recettes difficiles |
| 4 | `anthropic.Anthropic` sync dans coroutine async | `validator.py` | CRITICAL/HIGH | Event loop bloquée 1-10s par recette |
| 5 | INSERT `recipe_ingredients` manquant | `agent.py` | CRITICAL | Données ingrédients perdues silencieusement |
| A | `cookies()` — note de compatibilité Next 15 | `server.ts` | HIGH | Futur upgrade risqué |
| B | `next-pwa` 5.6.0 + Next 14 App Router | `next.config.mjs` | HIGH | Warnings build service worker |
| C | `init-scripts/postgres` répertoire absent | `docker-compose.dev.yml` | HIGH | `docker compose up` échoue |
| D | `exc.limit.limit` AttributeError handler 429 | `rate_limit.py` | LOW | Header X-RateLimit-Limit toujours "inconnu" |
| M1 | Double import `MemberTasteVector` | `models/__init__.py` | MEDIUM | Confusion mypy |
| M2 | Cache key `uv.lock` au mauvais chemin CI | `ci.yml` | MEDIUM | Cache CI jamais restauré |
| M3 | Pool connexions agent + API = >60 sur Supabase Free | `agent.py` | MEDIUM | Connexions épuisées en prod |

---

## Verdict : FIXES REQUIRED

**5 bugs CRITICAL doivent être corrigés avant le premier `make install && make dev` fonctionnel.**

Priorité absolue (bloquent le démarrage ou causent une perte de données silencieuse) :
1. **BUG #2** (env var) — 2 minutes de fix
2. **BUG #C** (répertoire Docker) — 1 minute de fix  
3. **BUG #1** (book_generator stub) — 15 minutes de fix
4. **BUG #3** (difficulty constraint) — 5 minutes de fix
5. **BUG #4** (AsyncAnthropic) — 10 minutes de fix
6. **BUG #5** (INSERT recipe_ingredients) — 30-45 minutes de fix
