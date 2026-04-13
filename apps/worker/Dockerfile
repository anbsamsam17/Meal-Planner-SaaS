# Dockerfile — apps/worker (Celery)
#
# Ce Dockerfile suit la même architecture multi-stage que apps/api/Dockerfile.
# La base est identique pour partager le cache Docker des couches communes.
#
# Différences clés vs api :
#   - ENTRYPOINT : celery worker (pas uvicorn)
#   - Pas de port exposé (le worker ne reçoit pas de requêtes HTTP)
#   - Concurrency Celery : 4 workers par défaut (ajustable via CELERY_CONCURRENCY)
#   - Variables Celery importantes définies ici pour le tuning
#   - Playwright + Chromium installés pour le scraping JS-rendered
#
# FIX Phase 1 (review 2026-04-12) : BUG #4 — Dockerfile cassait la résolution uv workspace.
# Même correction que apps/api/Dockerfile : copie du workspace root en premier.
# Le build context DOIT être la racine du monorepo (context: . dans docker-compose + CI).

# =============================================================================
# Stage 1 : builder (identique au builder api — partage le cache si même base)
# IMPORTANT : le build context doit être la RACINE du monorepo, pas apps/worker/
# =============================================================================
FROM python:3.12-slim AS builder

LABEL org.opencontainers.image.title="MealPlanner Worker Builder"
LABEL org.opencontainers.image.description="Stage de build — Celery worker"

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Même version uv que le Dockerfile api — garantit des builds identiques
COPY --from=ghcr.io/astral-sh/uv:0.5.18 /uv /usr/local/bin/uv

# Répertoire de travail = racine du workspace uv
WORKDIR /workspace

# -------------------------------------------------------------------------
# FIX Phase 1 (review 2026-04-12) : BUG #4 — Copie du workspace root en premier.
# L'ancien Dockerfile copiait apps/worker/pyproject.toml + apps/worker/uv.lock
# (qui n'existe pas — le lock est UNIQUEMENT à la racine dans un uv workspace).
# Sans pyproject.toml racine, uv sync échoue avec "workspace root not found".
# -------------------------------------------------------------------------

# Étape 1 : fichiers racine du workspace
COPY pyproject.toml uv.lock ./

# Étape 2 : packages/ partagés (packages/db quand il sera créé par backend-developer)
COPY packages/ ./packages/

# Étape 3 : pyproject.toml du sous-projet worker (sans le code source)
COPY apps/worker/pyproject.toml ./apps/worker/

# Synchronisation des dépendances worker uniquement
# --package mealplanner-worker : cible uniquement le package worker dans le workspace
RUN uv sync --frozen --no-dev --package mealplanner-worker

# Étape 4 : code source (invalidation cache si code change)
COPY apps/worker/src/ ./apps/worker/src/

# =============================================================================
# Stage 2 : runtime Celery
# =============================================================================
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="MealPlanner Worker"
LABEL org.opencontainers.image.description="Celery worker — MealPlanner SaaS"
LABEL org.opencontainers.image.vendor="MealPlanner SaaS"
LABEL org.opencontainers.image.source="https://github.com/mealplanner-saas/mealplanner-saas"
LABEL org.opencontainers.image.licenses="UNLICENSED"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    # PYTHONPATH pointe vers /app pour que les imports "apps.worker.src.*" fonctionnent
    PYTHONPATH="/app" \
    # Nombre de processus Celery par container (ajuster selon RAM Railway)
    # 4 est un bon point de départ pour des tâches I/O bound (appels API)
    CELERY_CONCURRENCY=4 \
    # Prefetch multiplier à 1 : chaque worker prend une tâche à la fois
    # Évite qu'un worker monopolise la queue pendant une tâche longue (scraping)
    CELERY_PREFETCH_MULTIPLIER=1 \
    # Log level par défaut (surchargeable via env var)
    CELERY_LOG_LEVEL=INFO \
    # Répertoire Playwright — défini AVANT l'install pour que le cache soit accessible
    # par l'utilisateur appuser (évite le problème root cache → appuser unreadable)
    # FIX Phase 1 (review 2026-04-12) : M12 code-review — Playwright installé en root
    # mais cache stocké dans ~/.cache/ms-playwright → inaccessible après USER appuser.
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

# Dépendances système WeasyPrint (Phase 2 — génération PDF hebdomadaire)
# WeasyPrint utilise cairo + pango + gdk-pixbuf pour le rendu HTML→PDF.
# Ces paquets doivent être installés AVANT l'installation de WeasyPrint via pip.
# shared-mime-info est requis pour la détection des types MIME dans les PDFs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Créer l'utilisateur non-root (même convention que api)
RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /workspace/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /workspace/apps/worker /app/apps/worker

# Installation de Playwright et ses dépendances système.
# Playwright est requis par RECIPE_SCOUT pour les pages JavaScript-rendered.
# L'install se fait en root (avant USER appuser) car --with-deps installe des paquets système.
# Seul Chromium est installé (Firefox et WebKit non nécessaires pour le scraping).
#
# FIX Phase 1 (review 2026-04-12) : M12 code-review — chown sur /opt/playwright
# pour que appuser puisse lire le cache Chromium après le basculement USER appuser.
RUN /app/.venv/bin/playwright install chromium --with-deps \
    && chown -R appuser:appuser /opt/playwright

USER appuser

# Healthcheck pour Celery : vérifie que le worker répond à un ping Celery
# Utilise la commande inspect ping native de Celery
# --start-period=60s : le worker prend plus de temps à démarrer (charge des modèles)
#
# FIX #4 (review 2026-04-12) : l'exec form (tableau JSON) ne passe pas par /bin/sh —
# $(hostname) était interprété littéralement → container toujours "unhealthy".
# Passage en shell form (sans crochets) : le shell interprète $(hostname) correctement.
HEALTHCHECK \
    --interval=30s \
    --timeout=20s \
    --retries=3 \
    --start-period=60s \
    CMD celery -A apps.worker.src.app inspect ping -d "celery@$(hostname)" --timeout 10 || exit 1

# ENTRYPOINT Celery :
# -A apps.worker.src.app : module contenant l'instance Celery
# worker                 : mode worker (vs beat pour le scheduler)
# --loglevel=INFO        : niveau de log (loguru + structlog capturent les logs Celery)
# --concurrency=4        : surchargé par la variable CELERY_CONCURRENCY
# --prefetch-multiplier=1 : surchargé par CELERY_PREFETCH_MULTIPLIER
# --without-gossip       : désactive le gossip inter-workers (économie Redis)
# --without-mingle       : désactive la sync au démarrage (démarrage plus rapide)
# Note : Celery Beat (tâches planifiées) tourne dans un container séparé en prod
#        pour éviter les doubles exécutions. En dev, on peut activer --beat ici.
#
# FIX Phase 1 (review 2026-04-12) : BUG #4 — module path mis à jour pour refléter la nouvelle
# structure de workspace. PYTHONPATH=/app permet l'import "apps.worker.src.app".
ENTRYPOINT [ \
    "celery", "-A", "apps.worker.src.app", "worker", \
    "--loglevel=INFO", \
    "--concurrency=4", \
    "--prefetch-multiplier=1", \
    "--without-gossip", \
    "--without-mingle" \
]
