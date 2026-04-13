#!/usr/bin/env bash
# scripts/setup.sh — Script de setup initial Presto (Unix/macOS/Linux)
#
# Usage :
#   bash scripts/setup.sh
#
# Ce script vérifie les prérequis, installe les dépendances et affiche les next steps.
# Il est idempotent : peut être relancé sans problème si une étape a échoué.

set -euo pipefail

# =============================================================================
# Couleurs pour l'affichage
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERREUR]${NC} $1"; exit 1; }

# =============================================================================
# Vérification des prérequis
# =============================================================================
echo ""
echo "Presto — Setup de l'environnement de développement"
echo "============================================================="
echo ""

log_info "Vérification des prérequis..."

# Vérifier uv
if command -v uv &>/dev/null; then
    UV_VERSION=$(uv --version 2>&1 | awk '{print $2}')
    log_success "uv trouvé : $UV_VERSION"
else
    log_error "uv non installé. Installer avec : curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# Vérifier que uv est >= 0.5.18
UV_MIN="0.5.18"
if [[ "$(printf '%s\n' "$UV_MIN" "$UV_VERSION" | sort -V | head -n1)" != "$UV_MIN" ]]; then
    log_warning "uv $UV_VERSION détecté — version minimale recommandée : $UV_MIN"
    log_warning "Mettre à jour avec : uv self update"
fi

# Vérifier Python 3.12
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_success "Python trouvé : $PYTHON_VERSION"
    if [[ "$PYTHON_VERSION" != 3.12* ]]; then
        log_warning "Python 3.12 recommandé (trouvé $PYTHON_VERSION). uv installera Python 3.12 automatiquement."
    fi
else
    log_warning "python3 non trouvé dans PATH — uv installera Python 3.12 automatiquement."
fi

# Vérifier pnpm
if command -v pnpm &>/dev/null; then
    PNPM_VERSION=$(pnpm --version 2>&1)
    log_success "pnpm trouvé : $PNPM_VERSION"
    if [[ "$PNPM_VERSION" != 9* ]]; then
        log_warning "pnpm 9.x recommandé (trouvé $PNPM_VERSION). Mettre à jour : npm install -g pnpm@9"
    fi
else
    log_error "pnpm non installé. Installer avec : npm install -g pnpm@9"
fi

# Vérifier Node.js >= 20
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version 2>&1 | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
    log_success "Node.js trouvé : v$NODE_VERSION"
    if [[ "$NODE_MAJOR" -lt 20 ]]; then
        log_error "Node.js >= 20 requis (trouvé v$NODE_VERSION). Installer depuis https://nodejs.org"
    fi
else
    log_error "Node.js non installé. Installer depuis https://nodejs.org ou via nvm : nvm install 20"
fi

# Vérifier Docker
if command -v docker &>/dev/null; then
    DOCKER_VERSION=$(docker --version 2>&1 | awk '{print $3}' | sed 's/,//')
    log_success "Docker trouvé : $DOCKER_VERSION"
    # Vérifier que Docker Desktop est démarré
    if ! docker info &>/dev/null 2>&1; then
        log_error "Docker est installé mais ne répond pas. Démarrer Docker Desktop."
    fi
else
    log_error "Docker non installé. Installer Docker Desktop depuis https://docker.com/products/docker-desktop"
fi

echo ""
log_info "Tous les prérequis sont satisfaits."
echo ""

# =============================================================================
# Configuration de l'environnement
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Copier le template .env.example en .env.local si inexistant
if [[ ! -f ".env.local" ]]; then
    cp .env.example .env.local
    log_success ".env.local créé depuis .env.example"
    log_warning "IMPORTANT : éditer .env.local avec vos vraies valeurs avant de continuer."
else
    log_info ".env.local existe déjà — non écrasé."
fi

# =============================================================================
# Copie des Dockerfiles (assemblage monorepo — BUG #2 fix)
# =============================================================================
# Les Dockerfiles sont dans phase-0/infra/ comme sources documentaires.
# Le CI GitHub Actions attend apps/api/Dockerfile et apps/worker/Dockerfile.
log_info "Copie des Dockerfiles Phase 0 vers les emplacements attendus par le CI..."

if [[ -f "phase-0/infra/03-apps-api-Dockerfile" ]]; then
    cp "phase-0/infra/03-apps-api-Dockerfile" "apps/api/Dockerfile"
    log_success "apps/api/Dockerfile créé"
else
    log_warning "phase-0/infra/03-apps-api-Dockerfile introuvable — apps/api/Dockerfile non créé"
fi

if [[ -f "phase-0/infra/04-apps-worker-Dockerfile" ]]; then
    cp "phase-0/infra/04-apps-worker-Dockerfile" "apps/worker/Dockerfile"
    log_success "apps/worker/Dockerfile créé"
else
    log_warning "phase-0/infra/04-apps-worker-Dockerfile introuvable — apps/worker/Dockerfile non créé"
fi

# =============================================================================
# Installation des dépendances
# =============================================================================
log_info "Installation des dépendances Python (uv sync)..."
uv sync
log_success "Dépendances Python installées."

log_info "Installation des dépendances JavaScript (pnpm install)..."
pnpm install
log_success "Dépendances JavaScript installées."

# =============================================================================
# Installation des hooks pre-commit
# =============================================================================
log_info "Installation des hooks pre-commit..."
uv run pre-commit install
log_success "Hooks pre-commit installés."

# =============================================================================
# Résumé et next steps
# =============================================================================
echo ""
echo "========================================"
echo "  Setup terminé avec succès !"
echo "========================================"
echo ""
echo "Prochaines étapes :"
echo ""
echo "  1. Editer .env.local avec vos clés API :"
echo "     nano .env.local"
echo "     (voir les commentaires dans .env.example pour savoir où obtenir chaque clé)"
echo ""
echo "  2. Démarrer les services Docker :"
echo "     make dev"
echo ""
echo "  3. Appliquer les migrations (une fois que le backend-developer a créé apps/api/) :"
echo "     make migrate"
echo ""
echo "  4. Lancer l'application :"
echo "     Terminal 1 : uv run uvicorn apps.api.src.main:app --reload --port 8000"
echo "     Terminal 2 : uv run celery -A apps.worker.src.app worker --loglevel=info"
echo "     Terminal 3 : pnpm --filter @mealplanner/web dev"
echo ""
echo "  5. Interfaces locales disponibles après démarrage :"
echo "     API FastAPI  : http://localhost:8000/docs"
echo "     Next.js      : http://localhost:3000"
echo "     MailHog      : http://localhost:8025"
echo "     MinIO        : http://localhost:9001"
echo ""
echo "  Commande utile : make help"
echo ""
