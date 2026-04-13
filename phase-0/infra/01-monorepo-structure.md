# Architecture Monorepo — MealPlanner SaaS

> Ce document décrit la structure complète du monorepo et justifie chaque choix.
> Dernière mise à jour : Phase 0

---

## Arborescence complète

```
mealplanner-saas/
│
├── apps/
│   ├── web/                          # Next.js 14 (App Router, TypeScript, Tailwind, PWA)
│   │   ├── app/
│   │   │   ├── (auth)/               # Groupe de routes publiques : login, magic-link
│   │   │   ├── (dashboard)/          # Groupe de routes protégées (Supabase Auth)
│   │   │   │   ├── planner/          # Planificateur hebdomadaire
│   │   │   │   ├── recipes/          # Bibliothèque de recettes
│   │   │   │   ├── shopping/         # Liste de courses
│   │   │   │   └── settings/         # Profil famille, abonnement
│   │   │   ├── api/                  # Route Handlers Next.js (proxy léger vers FastAPI)
│   │   │   ├── layout.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── ui/                   # Composants atomiques (shadcn/ui)
│   │   │   ├── features/             # Composants métier
│   │   │   └── providers/            # Contexts React (auth, theme, posthog)
│   │   ├── hooks/                    # Custom hooks
│   │   ├── lib/                      # Clients API, helpers
│   │   ├── public/
│   │   │   ├── manifest.json         # PWA manifest
│   │   │   └── sw.js                 # Service Worker (next-pwa)
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   └── e2e/                  # Playwright
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   │
│   ├── api/                          # FastAPI — API REST principale
│   │   ├── src/
│   │   │   ├── main.py               # Point d'entrée FastAPI (lifespan, middleware)
│   │   │   ├── config.py             # Settings Pydantic BaseSettings (lit les env vars)
│   │   │   ├── database.py           # Pool asyncpg + SQLAlchemy async
│   │   │   ├── routers/              # Un fichier par domaine métier
│   │   │   │   ├── recipes.py
│   │   │   │   ├── planner.py
│   │   │   │   ├── cart.py
│   │   │   │   ├── auth.py
│   │   │   │   └── webhooks.py       # Stripe webhooks
│   │   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── schemas/              # Pydantic v2 schemas (request/response)
│   │   │   ├── services/             # Logique métier (pas de SQL dans les routers)
│   │   │   ├── agents/               # Agents IA LangGraph
│   │   │   │   ├── recipe_scout.py
│   │   │   │   ├── taste_profile.py
│   │   │   │   ├── weekly_planner.py
│   │   │   │   ├── cart_builder.py
│   │   │   │   ├── book_generator.py
│   │   │   │   └── retention_loop.py
│   │   │   ├── core/                 # Auth middleware, rate limiting, logging
│   │   │   └── utils/                # Helpers partagés
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── conftest.py           # Fixtures pytest (DB de test, Redis mock)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml            # Géré par uv
│   │   └── uv.lock
│   │
│   └── worker/                       # Celery workers (tâches asynchrones)
│       ├── src/
│       │   ├── app.py                # Celery app instance + config
│       │   ├── tasks/
│       │   │   ├── scraping.py       # RECIPE_SCOUT tasks
│       │   │   ├── pdf_generation.py # BOOK_GENERATOR tasks
│       │   │   ├── embeddings.py     # Batch vectorisation
│       │   │   └── retention.py      # RETENTION_LOOP tasks
│       │   └── schedules.py          # Celery Beat : tâches planifiées
│       ├── Dockerfile
│       └── pyproject.toml            # Partage les mêmes deps que api/ (uv workspace)
│
├── packages/
│   └── shared-types/                 # Types TypeScript générés depuis OpenAPI
│       ├── src/
│       │   └── index.ts              # Types auto-générés (ne pas éditer à la main)
│       ├── scripts/
│       │   └── generate.sh           # openapi-typescript --input http://localhost:8000/openapi.json
│       └── package.json
│
├── infra/
│   ├── docker/
│   │   ├── docker-compose.dev.yml    # Dev local (voir livrable 02)
│   │   └── docker-compose.test.yml   # Tests CI (postgres + redis éphémères)
│   └── k8s/                          # Kubernetes — Phase 5 uniquement (placeholder)
│       └── .gitkeep
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # CI principale (voir livrable 05)
│   │   ├── deploy-staging.yml        # Auto-deploy sur push main
│   │   └── security.yml              # Scan hebdomadaire gitleaks + pip-audit
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS                    # Reviewers obligatoires par path
│
├── scripts/
│   ├── memory.sh                     # Chargement contexte Claude CLI
│   ├── memory.ps1                    # Équivalent PowerShell
│   ├── setup-dev.sh                  # Bootstrap complet environnement dev
│   └── generate-types.sh             # Regénère shared-types depuis OpenAPI
│
├── docs/
│   ├── adr/                          # Architecture Decision Records
│   │   └── 001-python-backend.md
│   └── agents/                       # README par agent IA (règle ROADMAP §10)
│
├── memory/                           # Contexte Claude (voir CLAUDE.md)
├── phase-0/                          # Livrables Phase 0 (ce dossier)
│
├── CLAUDE.md                         # Instructions Claude Code
├── ROADMAP.md                        # Source de vérité produit
├── .env.example                      # Template vars d'env (voir livrable 09)
├── .gitignore
├── pnpm-workspace.yaml               # Configuration pnpm workspaces
├── package.json                      # Root package.json (scripts globaux)
└── Makefile                          # Commandes unifiées make dev, make test, etc.
```

---

## Justifications des choix

### pnpm workspaces (pas npm, pas yarn)

**Pourquoi pnpm :** Déduplication physique des node_modules (hoisting intelligent),
`--frozen-lockfile` fiable en CI, vitesse d'installation 2-3x supérieure à npm.

**Pourquoi pas Turborepo :** En Phase 0 avec un seul développeur, la complexité de
Turborepo (cache distribué, pipeline de build) n'apporte pas encore de valeur.
Turborepo sera ajouté en Phase 3 quand le temps de CI dépassera 10 minutes.

**Configuration `pnpm-workspace.yaml` :**
```yaml
packages:
  - 'apps/web'
  - 'packages/*'
```
Note : `apps/api` et `apps/worker` sont des projets Python — exclus des workspaces JS.

### uv (pas poetry, pas pip)

**Pourquoi uv :** Résolution de dépendances 10-100x plus rapide que pip/poetry
(implémenté en Rust). Support natif des workspaces Python. Lock file déterministe.
`uv sync` remplace `pip install -r requirements.txt` et `poetry install` en une commande.

**Pourquoi pas poetry :** poetry est plus lent, le format `pyproject.toml` de uv est
identique (PEP 621 compliant), et uv gère les environnements virtuels automatiquement.

**Pourquoi pas pip + requirements.txt :** Pas de lock file natif, pas de résolution
des conflits de dépendances, pas de gestion des environnements virtuels.

**Workspace uv :** `apps/api` et `apps/worker` partagent les mêmes dépendances Python
via un workspace uv à la racine — évite la duplication de `fastapi`, `pydantic`, etc.

### Monorepo (pas polyrepo)

**Pourquoi monorepo :** Les agents Python (api + worker) partagent des modèles Pydantic,
des helpers DB, et des schémas. Un polyrepo forcerait à publier des packages internes.
La génération de `shared-types` TypeScript depuis l'OpenAPI FastAPI est triviale en monorepo.

**Séparation api / worker :** Deux Dockerfiles distincts malgré le code partagé.
Permet de scaler le worker indépendamment de l'API (Railway services séparés).
Le worker n'expose pas de port HTTP — sécurité améliorée.

### Structure apps/api/src/ (pas à plat)

Le répertoire `src/` évite les conflits entre le code applicatif et les fichiers de
configuration à la racine (`pyproject.toml`, `Dockerfile`, tests). Convention Python
recommandée pour les projets de taille moyenne.

---

## Flux de données simplifié

```
Browser (Next.js PWA)
    │
    ├── HTTPS → api.mealplanner.fr (Railway)
    │               │
    │               ├── PostgreSQL / pgvector (Supabase)
    │               ├── Redis (Railway plugin)
    │               └── Celery task → worker service (Railway)
    │                                       │
    │                                       ├── Anthropic API
    │                                       ├── Stability AI
    │                                       └── Cloudflare R2 (PDF output)
    │
    └── WebSocket (Supabase Realtime) → liste de courses partagée
```
