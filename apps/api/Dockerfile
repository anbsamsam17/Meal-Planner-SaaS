# Dockerfile — apps/api (FastAPI)
#
# Architecture multi-stage :
#   Stage 1 (builder) : installe les dépendances Python avec uv dans un venv isolé
#   Stage 2 (runtime) : copie uniquement le venv et le code source — image finale légère
#
# Pourquoi multi-stage :
#   - L'image finale ne contient pas uv, pip, ni les headers de compilation C
#   - Réduit la surface d'attaque (moins d'outils système installés)
#   - Image runtime ~200 MB vs ~600 MB si tout est dans un seul stage
#
# Pourquoi non-root :
#   - Principe du moindre privilège : un process compromis ne peut pas modifier
#     les fichiers système ni installer des paquets
#   - Requis par certains scanners de sécurité (Trivy, Snyk) et politiques Kubernetes
#
# Pourquoi uv :
#   - 10-100x plus rapide que pip pour la résolution et l'installation des dépendances
#   - Lock file déterministe (uv.lock) — builds reproductibles en CI
#
# FIX Phase 1 (review 2026-04-12) : BUG #4 — Dockerfile cassait la résolution uv workspace.
# Le build context DOIT être la racine du monorepo (context: . dans docker-compose + CI).
# Sans le pyproject.toml racine, "uv sync --frozen" échoue avec "workspace root not found".
# Structure corrigée : copie d'abord le workspace root, puis le sous-pyproject.

# =============================================================================
# Stage 1 : builder
# Base : python:3.12-slim pour avoir les outils de build (gcc pour les extensions C)
# IMPORTANT : le build context doit être la RACINE du monorepo, pas apps/api/
# =============================================================================
FROM python:3.12-slim AS builder

# Métadonnées OCI standard
LABEL org.opencontainers.image.title="MealPlanner API Builder"
LABEL org.opencontainers.image.description="Stage de build — FastAPI backend"
LABEL org.opencontainers.image.source="https://github.com/mealplanner-saas/mealplanner-saas"

# Variables d'environnement pour uv et Python
# UV_COMPILE_BYTECODE : précompile les .pyc pour un démarrage plus rapide
# UV_LINK_MODE=copy   : copie les fichiers au lieu de créer des symlinks (portable entre stages)
# PYTHONDONTWRITEBYTECODE=1 : évite les .pyc dans le répertoire source
# PYTHONUNBUFFERED=1  : logs en temps réel sans buffering
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installation de uv depuis son image officielle (version pinée pour reproductibilité)
COPY --from=ghcr.io/astral-sh/uv:0.5.18 /uv /usr/local/bin/uv

# Répertoire de travail = racine du workspace uv
WORKDIR /workspace

# -------------------------------------------------------------------------
# FIX Phase 1 (review 2026-04-12) : BUG #4 — Copie du workspace root en premier.
# Sans pyproject.toml racine + uv.lock racine, uv sync --frozen ne peut pas
# résoudre le workspace et échoue avec "workspace member not found".
# Ordre : 1) root pyproject + lock, 2) packages/ (si existant), 3) sub-pyproject
# -------------------------------------------------------------------------

# Étape 1 : fichiers racine du workspace (déclenchent invalidation cache uniquement si lock change)
COPY pyproject.toml uv.lock ./

# Étape 2 : packages/ partagés (packages/db quand il sera créé par backend-developer)
# Le COPY avec wildcard ne plante pas si packages/ ne contient que shared-types (TypeScript)
COPY packages/ ./packages/

# Étape 3 : pyproject.toml du sous-projet api (sans le code source)
COPY apps/api/pyproject.toml ./apps/api/

# Synchronisation des dépendances uniquement (pas le code source — optimisation cache Docker)
# --frozen : utilise exactement les versions du lock file (builds reproductibles)
# --no-dev : exclut les dépendances de développement de l'image de production
# --package mealplanner-api : cible uniquement le package api dans le workspace
RUN uv sync --frozen --no-dev --package mealplanner-api

# Étape 4 : code source + migrations Alembic (invalidation cache si code change)
COPY apps/api/src/ ./apps/api/src/
COPY apps/api/alembic/ ./apps/api/alembic/
COPY apps/api/alembic.ini ./apps/api/

# =============================================================================
# Stage 2 : runtime
# Base : python:3.12-slim (sans outils de build)
# Résultat : image minimale, non-root, avec seulement le nécessaire
# =============================================================================
FROM python:3.12-slim AS runtime

# Métadonnées OCI standard (labels recommandés par la spec OCI Image Format)
LABEL org.opencontainers.image.title="MealPlanner API"
LABEL org.opencontainers.image.description="FastAPI backend — MealPlanner SaaS"
LABEL org.opencontainers.image.vendor="MealPlanner SaaS"
LABEL org.opencontainers.image.source="https://github.com/mealplanner-saas/mealplanner-saas"
LABEL org.opencontainers.image.licenses="UNLICENSED"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Ajoute le venv au PATH pour que `python` et `uvicorn` soient trouvés directement
    PATH="/app/.venv/bin:$PATH" \
    # PYTHONPATH inclut /app/apps/api pour que "from src.core.config" fonctionne
    PYTHONPATH="/app/apps/api" \
    # Port d'écoute uvicorn (surchargeable via env var Railway/Docker)
    PORT=8000

# Créer un utilisateur non-root dédié à l'application
# -m : crée le home directory, -u 1000 : UID fixe pour la cohérence entre stages
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copier le venv compilé depuis le builder (sans uv ni outils de build)
COPY --from=builder --chown=appuser:appuser /workspace/.venv /app/.venv

# Copier le code source applicatif + migrations depuis le workspace builder
COPY --from=builder --chown=appuser:appuser /workspace/apps/api /app/apps/api

# Basculer vers l'utilisateur non-root avant d'exposer le port
USER appuser

# Exposer le port (documentation — Railway utilise la variable $PORT)
EXPOSE 8000

# Healthcheck : vérifie que l'API répond sur /health
# --interval=30s : check toutes les 30 secondes
# --timeout=5s   : timeout de 5 secondes par check (réduit vs 10s pour détecter plus vite)
# --retries=3    : 3 échecs consécutifs = container unhealthy
# --start-period=40s : délai de grâce au démarrage (chargement modèles, connexion DB)
# FIX #1 (review 2026-04-12) : shell form (sans crochets) pour interpoler ${PORT:-8000}.
# L'exec form (tableau JSON) ne passe pas par /bin/sh → ${PORT} resterait littéral.
HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --retries=3 \
    --start-period=40s \
    CMD curl -fsS "http://localhost:${PORT:-8000}/api/v1/health" || exit 1

# Uvicorn en mode production :
# --host 0.0.0.0   : écoute sur toutes les interfaces (requis dans Docker)
# --port ${PORT:-8000} : lit la variable Railway injectée dynamiquement (défaut 8000)
# --workers ${WEB_CONCURRENCY:-2} : paramétrable sans rebuild d'image
# --no-access-log  : les accès logs sont gérés par le middleware FastAPI (JSON structuré)
# Note : pas de --reload en production — uniquement en dev avec uvicorn --reload
#
# FIX #1 (review 2026-04-12) : ENTRYPOINT en exec form figé sur --port 8000 échouait au deploy
# Railway qui injecte $PORT dynamiquement. Passage en CMD shell form pour interpoler ${PORT:-8000}.
# WEB_CONCURRENCY permet de surcharger le nombre de workers sans rebuild (Railway env var).
#
# FIX Phase 1 (review 2026-04-12) : BUG #4 — module path mis à jour pour refléter la nouvelle
# structure de workspace. Le PYTHONPATH=/app permet l'import "apps.api.src.main".
CMD cd /app/apps/api && /app/.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --no-access-log
