# Makefile — Presto
#
# Commandes unifiées pour l'environnement de développement.
# Usage : make <target>
# Liste des targets : make help
#
# Ports configurables via variables d'env (surchargeables au lancement) :
#   API_PORT=8001 make dev
#   DB_PORT=5433  (port hôte Docker → évite conflit avec PG local sur 5432)

# Port de l'API FastAPI (8001 si le port 8000 est déjà occupé sur votre machine)
API_PORT ?= 8001
# Port PostgreSQL hôte (le container Docker expose 5433:5432 pour éviter les conflits)
DB_PORT  ?= 5433

.PHONY: install dev dev-stop dev-logs db-up db-down migrate seed \
        test test-api test-web lint lint-api lint-web \
        format build-api build-worker generate-types clean help \
        scout generate-pdf stripe-listen

# =============================================================================
# INSTALLATION
# =============================================================================

## Installe toutes les dépendances Python et JavaScript
install:
	uv sync
	pnpm install
	@echo ""
	@echo "Installation terminée. Prochaines étapes :"
	@echo "  1. cp .env.example .env.local && nano .env.local"
	@echo "  2. make dev"
	@echo "  3. make migrate"

## Installe les hooks pre-commit (ruff, prettier, gitleaks)
install-hooks:
	uv run pre-commit install
	@echo "Hooks pre-commit installés."

# =============================================================================
# DÉMARRAGE DE L'ENVIRONNEMENT
# =============================================================================

## Démarre les services Docker (postgres, redis, mailhog, minio)
dev:
	docker compose -f docker-compose.dev.yml up -d
	@echo ""
	@echo "Services Docker démarrés :"
	@echo "  PostgreSQL : localhost:$(DB_PORT)  (container expose $(DB_PORT):5432)"
	@echo "  Redis      : localhost:6379"
	@echo "  MailHog    : http://localhost:8025"
	@echo "  MinIO API  : http://localhost:9000"
	@echo "  MinIO UI   : http://localhost:9001"
	@echo ""
	@echo "Lancer ensuite dans 3 terminaux séparés :"
	@echo "  Terminal 1 : uv run uvicorn apps.api.src.main:app --reload --port $(API_PORT)"
	@echo "  Terminal 2 : uv run celery -A apps.worker.src.app worker --loglevel=info"
	@echo "  Terminal 3 : pnpm --filter @mealplanner/web dev"

## Arrête tous les services Docker
dev-stop:
	docker compose -f docker-compose.dev.yml down

## Arrête les services Docker et supprime les volumes (reset complet)
dev-reset:
	docker compose -f docker-compose.dev.yml down -v
	@echo "Services arrêtés et volumes supprimés."

## Affiche les logs des services Docker en temps réel
dev-logs:
	docker compose -f docker-compose.dev.yml logs -f

## Affiche le statut des services Docker
dev-status:
	docker compose -f docker-compose.dev.yml ps

# =============================================================================
# BASE DE DONNÉES
# =============================================================================

## Démarre uniquement postgres et redis (sans mailhog ni minio)
db-up:
	docker compose -f docker-compose.dev.yml up -d postgres redis
	@echo "PostgreSQL et Redis démarrés."

## Arrête postgres et redis
db-down:
	docker compose -f docker-compose.dev.yml stop postgres redis

## Applique les migrations Alembic (base de données locale)
## Utilise DATABASE_URL de .env.local si défini, sinon construit depuis DB_PORT
migrate:
	cd apps/api && DATABASE_URL="postgresql+asyncpg://mealplanner:mealplanner_dev_password@localhost:$(DB_PORT)/mealplanner_dev" uv run alembic upgrade head

## Revient à la migration précédente
migrate-down:
	cd apps/api && DATABASE_URL="postgresql+asyncpg://mealplanner:mealplanner_dev_password@localhost:$(DB_PORT)/mealplanner_dev" uv run alembic downgrade -1

## Génère une nouvelle migration Alembic (usage : make migration MSG="ajout table recettes")
migration:
	cd apps/api && DATABASE_URL="postgresql+asyncpg://mealplanner:mealplanner_dev_password@localhost:$(DB_PORT)/mealplanner_dev" uv run alembic revision --autogenerate -m "$(MSG)"

## Alimente la base de données avec des données de test
seed:
	cd apps/api && DATABASE_URL="postgresql+asyncpg://mealplanner:mealplanner_dev_password@localhost:$(DB_PORT)/mealplanner_dev" uv run python -m src.scripts.seed

# =============================================================================
# TESTS
# =============================================================================

## Lance tous les tests (Python + JavaScript)
test: test-api test-web

## Lance les tests Python (pytest avec coverage)
test-api:
	uv run pytest apps/api/tests/ \
		--cov=apps/api/src \
		--cov-report=term-missing \
		--cov-fail-under=80 \
		-v

## Lance les tests Next.js (vitest)
test-web:
	pnpm --filter @mealplanner/web test

## Lance les tests e2e Playwright
test-e2e:
	pnpm --filter @mealplanner/web test:e2e

## Lance les tests de charge k6 (Locust — Phase pre-release)
test-load:
	@echo "TODO : configurer k6 ou Locust pour les tests de charge"

# =============================================================================
# QUALITÉ DU CODE
# =============================================================================

## Lint tout le code Python et JavaScript
lint: lint-api lint-web

## Lint Python : ruff check + mypy
lint-api:
	uv run ruff check apps/api/src apps/worker/src
	uv run mypy apps/api/src apps/worker/src

## Lint JavaScript/TypeScript : ESLint + TypeScript check
lint-web:
	pnpm --filter @mealplanner/web lint
	pnpm --filter @mealplanner/web tsc --noEmit

## Formate tout le code Python et JavaScript
format: format-api format-web

## Formate le code Python avec ruff format
format-api:
	uv run ruff format apps/api/src apps/worker/src
	uv run ruff check --fix apps/api/src apps/worker/src

## Formate le code JavaScript/TypeScript avec prettier (via pnpm)
format-web:
	pnpm --filter @mealplanner/web format

## Audit des CVE dans les dépendances Python
audit-python:
	cd apps/api && uv run pip-audit

## Audit des CVE dans les dépendances JavaScript
audit-js:
	pnpm audit --audit-level=high

# =============================================================================
# BUILD DOCKER
# =============================================================================

## Build l'image Docker de l'API FastAPI (depuis la racine — contexte = .)
build-api:
	docker build -f apps/api/Dockerfile -t mealplanner-api:local .
	@echo "Image mealplanner-api:local construite."

## Build l'image Docker du Worker Celery
build-worker:
	docker build -f apps/worker/Dockerfile -t mealplanner-worker:local .
	@echo "Image mealplanner-worker:local construite."

## Build les deux images Docker
build: build-api build-worker

# =============================================================================
# PHASE 2 — FEATURES PREMIUM
# =============================================================================

## Lance le scraping RECIPE_SCOUT en mode manuel (10 recettes Marmiton, sans Celery)
scout:
	DATABASE_URL="postgresql+asyncpg://mealplanner:mealplanner_dev_password@localhost:$(DB_PORT)/mealplanner_dev" \
	  uv run python -m apps.worker.src.scripts.run_scout_manual

## Lance la génération d'un PDF de test (API doit être démarrée sur API_PORT)
generate-pdf:
	curl -s -X POST http://localhost:$(API_PORT)/api/v1/admin/generate-test-pdf \
	  -H "Content-Type: application/json" | python3 -m json.tool || \
	  echo "Erreur : vérifier que l'API est démarrée sur le port $(API_PORT)"

## Stripe webhook forwarding vers l'API locale (nécessite Stripe CLI installé)
## Installation CLI : https://stripe.com/docs/stripe-cli
stripe-listen:
	stripe listen --forward-to http://localhost:$(API_PORT)/api/v1/webhooks/stripe

# =============================================================================
# TYPES TYPESCRIPT
# =============================================================================

## Régénère les types TypeScript depuis l'OpenAPI FastAPI
## Prérequis : l'API doit être démarrée sur localhost:8000
generate-types:
	bash scripts/generate-types.sh

# =============================================================================
# NETTOYAGE
# =============================================================================

## Supprime tous les artefacts de build et caches
clean:
	docker compose -f docker-compose.dev.yml down -v
	find . -type d -name __pycache__ -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	@echo "Nettoyage terminé."

# =============================================================================
# AIDE
# =============================================================================

## Affiche l'aide et la liste des targets disponibles
help:
	@echo ""
	@echo "Presto — Commandes Make"
	@echo "=================================="
	@echo ""
	@grep -E '^## .+' $(MAKEFILE_LIST) | sed 's/## //' | while IFS= read -r line; do \
		target=$$(grep -B1 "^## $$line$$" $(MAKEFILE_LIST) | head -1 | sed 's/:.*//'); \
		printf "  \033[36m%-20s\033[0m %s\n" "$$target" "$$line"; \
	done
	@echo ""
	@echo "Exemple d'utilisation rapide :"
	@echo "  make install   # Installation initiale"
	@echo "  make dev       # Démarre les services Docker"
	@echo "  make migrate   # Applique les migrations"
	@echo "  make test      # Lance tous les tests"
