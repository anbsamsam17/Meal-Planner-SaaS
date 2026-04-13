# Phase 0 — Infrastructure Foundation

> Vue d'ensemble des livrables Phase 0.0 : Infrastructure Foundation.
> Lire ce fichier en premier avant d'exécuter quoi que ce soit.

---

## Pre-requis locaux

Installer ces outils avant de commencer :

| Outil | Version | Installation |
|-------|---------|--------------|
| Node.js | 20.x LTS | https://nodejs.org ou `nvm install 20` |
| pnpm | 9.x | `npm install -g pnpm@9` |
| Python | 3.12.x | https://python.org ou `pyenv install 3.12` |
| uv | 0.5.18+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker Desktop | 4.x+ | https://docker.com/products/docker-desktop |
| Doppler CLI | latest | `brew install dopplerhq/cli/doppler` |
| GitHub CLI | 2.x+ | `brew install gh` |

---

## Ordre d'exécution — Phase 0

### Etape 1 — Provisioning des comptes (manuel)

Lire et exécuter dans l'ordre : `00-provisioning-checklist.md`

Durée estimée : 2-3 heures (majoritairement de l'attente DNS et des créations de compte)

```
Doppler → GitHub → Supabase → Railway → Vercel → Cloudflare R2 →
Sentry → PostHog → Anthropic → Spoonacular → Edamam → Stability AI →
Resend → Stripe → Flagsmith
```

### Etape 2 — Structure du monorepo

Lire : `01-monorepo-structure.md`

Créer la structure de dossiers dans le repo GitHub :

```bash
# À la racine du repo cloné localement
mkdir -p apps/web apps/api/src apps/api/tests apps/worker/src apps/worker/tests
mkdir -p packages/shared-types/src packages/shared-types/scripts
mkdir -p infra/docker infra/k8s docs/adr docs/agents
mkdir -p .github/workflows scripts

# Créer les fichiers placeholder
touch infra/k8s/.gitkeep
touch .github/CODEOWNERS
```

### Etape 3 — Environnement de dev local

Copier et configurer les variables :

```bash
cp phase-0/infra/09-env-template.env .env.local
# Editer .env.local avec les vraies valeurs récupérées à l'étape 1
```

Démarrer les services locaux :

```bash
# Copier le docker-compose dans le bon dossier
cp phase-0/infra/02-docker-compose.dev.yml infra/docker/docker-compose.dev.yml

# Démarrer tous les services (postgres, redis, mailhog, minio)
docker compose -f infra/docker/docker-compose.dev.yml up -d

# Vérifier que tout est healthy
docker compose -f infra/docker/docker-compose.dev.yml ps
```

### Etape 4 — Dockerfiles de production

<!-- FIX #2 (review 2026-04-12) : les Dockerfiles dans phase-0/infra/ sont les fichiers sources.
     Le CI (.github/workflows/ci.yml) référence apps/api/Dockerfile et apps/worker/Dockerfile.
     Ces chemins DOIVENT exister dans le monorepo assemblé — voir la note d'assemblage ci-dessous. -->

> **IMPORTANT — Assemblage monorepo :** Les fichiers `03-apps-api-Dockerfile` et
> `04-apps-worker-Dockerfile` sont les sources documentaires Phase 0. Avant de pousser
> sur `main`, ils doivent être copiés aux emplacements attendus par le CI :
> - `phase-0/infra/03-apps-api-Dockerfile` → `apps/api/Dockerfile`
> - `phase-0/infra/04-apps-worker-Dockerfile` → `apps/worker/Dockerfile`
>
> Sans cette étape, le job `build-docker` du CI échoue avec :
> `ERROR: failed to solve: failed to read dockerfile: open apps/api/Dockerfile: no such file or directory`

```bash
# Copier les Dockerfiles dans les bons emplacements (assemblage monorepo obligatoire)
cp phase-0/infra/03-apps-api-Dockerfile apps/api/Dockerfile
cp phase-0/infra/04-apps-worker-Dockerfile apps/worker/Dockerfile

# Tester le build local de l'API (depuis la racine du monorepo — contexte = .)
docker build -f apps/api/Dockerfile -t mealplanner-api:local .

# Tester le build local du Worker
docker build -f apps/worker/Dockerfile -t mealplanner-worker:local .
```

### Etape 5 — CI/CD GitHub Actions

```bash
# Copier le workflow CI
cp phase-0/infra/05-github-workflows-ci.yml .github/workflows/ci.yml

# Configurer les secrets GitHub nécessaires au CI :
gh secret set DOPPLER_TOKEN_STAGING --body "..."
gh secret set DOPPLER_TOKEN_PROD --body "..."
gh secret set SENTRY_AUTH_TOKEN --body "..."
gh secret set SENTRY_ORG --body "mealplanner-saas"
# GITHUB_TOKEN est automatique — pas besoin de le configurer
```

### Etape 6 — Protection des branches

Lire `06-github-branch-protection.md` et configurer manuellement dans GitHub :
Settings > Branches > Branch protection rules

### Etape 7 — Vercel

Lire `07-vercel-setup.md` et configurer le projet Next.js sur Vercel.

### Etape 8 — Railway

Lire `08-railway-setup.md` et configurer les services Python sur Railway.

---

## Commandes utiles (Makefile)

Créer un `Makefile` à la racine du repo avec ces targets :

```makefile
# Makefile — MealPlanner SaaS

.PHONY: dev dev-stop dev-logs test-api test-web lint build help

# Démarrer l'environnement de développement local
dev:
	docker compose -f infra/docker/docker-compose.dev.yml up -d
	@echo "Services démarrés. MailHog: http://localhost:8025 | MinIO: http://localhost:9001"

# Arrêter tous les services Docker
dev-stop:
	docker compose -f infra/docker/docker-compose.dev.yml down

# Voir les logs des services Docker
dev-logs:
	docker compose -f infra/docker/docker-compose.dev.yml logs -f

# Lancer les tests API avec Doppler
test-api:
	cd apps/api && doppler run -- uv run pytest tests/ --cov=src --cov-fail-under=80 -v

# Lancer les tests web
test-web:
	cd apps/web && pnpm test

# Lint Python
lint-api:
	cd apps/api && uv run ruff check src/ && uv run mypy src/

# Lint TypeScript
lint-web:
	cd apps/web && pnpm lint && pnpm tsc --noEmit

# Build Docker API
build-api:
	docker build -f apps/api/Dockerfile -t mealplanner-api:local .

# Build Docker Worker
build-worker:
	docker build -f apps/worker/Dockerfile -t mealplanner-worker:local .

# Régénérer les types TypeScript depuis OpenAPI
generate-types:
	bash scripts/generate-types.sh

# Aide
help:
	@echo "Commandes disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
```

---

## Index des livrables

| Fichier | Description | Type |
|---------|-------------|------|
| `00-provisioning-checklist.md` | Comptes tiers à créer | Documentation |
| `01-monorepo-structure.md` | Architecture du monorepo | Documentation |
| `02-docker-compose.dev.yml` | Env dev local | Fichier executable |
| `03-apps-api-Dockerfile` | Dockerfile FastAPI | Fichier executable |
| `04-apps-worker-Dockerfile` | Dockerfile Celery | Fichier executable |
| `05-github-workflows-ci.yml` | Pipeline CI | Fichier executable |
| `06-github-branch-protection.md` | Règles branches GitHub | Documentation |
| `07-vercel-setup.md` | Config Vercel | Documentation |
| `08-railway-setup.md` | Config Railway | Documentation |
| `09-env-template.env` | Template .env.example | Fichier executable |
| `10-monitoring-setup.md` | Plan Sentry + PostHog | Documentation |
| `11-secrets-management.md` | Stratégie Doppler | Documentation |
| `12-rate-limiting-design.md` | Rate limiting 5 niveaux — slowapi + Redis | Documentation |
| `13-pdf-generation-strategy.md` | Stratégie génération PDF BOOK_GENERATOR | Documentation |
| `README.md` | Ce fichier | Documentation |

---

## Budget Phase 0 (rappel)

Objectif : < 100 €/mois, quasi 100 % sur plans gratuits.

| Poste | Coût estimé |
|-------|-------------|
| Railway (api + worker + worker-beat + Redis) | ~15-30 $ |
| Anthropic API (agents IA batch) | ~20-50 $ |
| Stability AI (photos PDF) | ~10 $ |
| Tout le reste | 0 € |
| **Total** | **~45-90 $/mois** |

---

## Corrections post-review (2026-04-12)

Suite à l'audit code-review / debug-audit / performance-audit du 2026-04-12,
les bugs suivants ont été corrigés dans les fichiers infra Phase 0.

| Bug | Criticité | Fichier modifié | Fix appliqué |
|-----|-----------|-----------------|--------------|
| #1 — `$PORT` hardcodé ENTRYPOINT API | CRITICAL | `03-apps-api-Dockerfile` | `CMD` shell form + `${PORT:-8000}` + `${WEB_CONCURRENCY:-2}` |
| #2 — Chemins Dockerfiles CI non documentés | CRITICAL | `README.md` | Note assemblage monorepo obligatoire |
| #3 — MinIO healthcheck `mc` absent | HIGH | `02-docker-compose.dev.yml` | `curl -f http://localhost:9000/minio/health/live` |
| #4 — Worker healthcheck `$(hostname)` exec form | HIGH | `04-apps-worker-Dockerfile` | Passage en shell form |
| #5 — Redis `allkeys-lru` perte Celery | HIGH | `02-docker-compose.dev.yml` | `volatile-lru` — clés sans TTL préservées |
| #6 — RAM API Railway 512 MB OOM | HIGH | `08-railway-setup.md` | Sizing documenté : 1 GB minimum api + worker |
| #7 — Pas de distinction `/health` vs `/ready` | MEDIUM | `08-railway-setup.md` | Sections 7 et 7b ajoutées + exemple code |
| #8 — GHA : `cancel-in-progress` sur main + pip-audit sans sync | MEDIUM | `05-github-workflows-ci.yml` | `cancel-in-progress` conditionnel + `uv sync` ajouté |

### Commandes de validation post-fix

```bash
# BUG #3 : MinIO healthcheck — doit passer de "unhealthy" à "healthy"
docker compose -f phase-0/infra/02-docker-compose.dev.yml up -d minio
docker inspect mealplanner_minio --format '{{.State.Health.Status}}'
# Attendu : "healthy" (après ~30s)

# BUG #5 : Redis volatile-lru — vérifier la config active
docker compose -f phase-0/infra/02-docker-compose.dev.yml up -d redis
docker exec mealplanner_redis redis-cli CONFIG GET maxmemory-policy
# Attendu : "volatile-lru"

# BUG #1 + #4 : Dockerfiles — valider la syntaxe (après assemblage monorepo)
docker build -f apps/api/Dockerfile -t mealplanner-api:test . --no-cache 2>&1 | tail -5
docker build -f apps/worker/Dockerfile -t mealplanner-worker:test . --no-cache 2>&1 | tail -5

# BUG #4 : Worker healthcheck shell form — vérifier que $(hostname) est bien interpolé
docker run --rm mealplanner-worker:test \
  sh -c 'echo "hostname=$(hostname)" && celery -A src.app inspect ping -d "celery@$(hostname)" --timeout 5 || echo FAIL'

# BUG #8 : Syntaxe CI — validation YAML
docker run --rm -v "$(pwd):/repo" ghcr.io/rhysd/actionlint:latest /repo/.github/workflows/ci.yml

# BUG #2 : Vérifier que les Dockerfiles sont au bon endroit après assemblage
ls -la apps/api/Dockerfile apps/worker/Dockerfile
```
