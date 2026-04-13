#!/bin/bash
# deploy-check.sh — Vérification pré-déploiement Presto
#
# Ce script vérifie que tous les pré-requis de déploiement sont remplis :
# tests backend, typecheck TypeScript, build Next.js, build Docker.
#
# Usage :
#   bash scripts/deploy-check.sh
#
# Pré-requis locaux :
#   - Python + uv installés (pour les tests API)
#   - Node.js + pnpm installés (pour le build web)
#   - Docker installé et running (pour les builds Docker)
#
# En CI (GitHub Actions) : ce script est appelé avant chaque release tag.
# Il quitte avec le code 1 si une étape échoue — bloque le déploiement automatiquement.

set -euo pipefail

# --- Couleurs pour la lisibilité ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Fonctions utilitaires ---
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; EXIT_CODE=1; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
step() { echo -e "\n${YELLOW}$1${NC}"; }

# Traquer les échecs sans quitter immédiatement (set -e est activé mais on override par fonction)
EXIT_CODE=0

echo "=========================================="
echo " Presto — Vérification pré-déploiement"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# ------------------------------------------
# 1. Tests API Python (pytest)
# ------------------------------------------
step "1. Tests API Python..."
if command -v uv &>/dev/null; then
    RESULT=$(uv run pytest apps/api/tests/ -q --tb=no 2>&1 | tail -3)
    echo "$RESULT"
    if echo "$RESULT" | grep -qE "passed|no tests ran"; then
        ok "Tests API OK"
    else
        fail "Tests API échoués — corriger avant déploiement"
    fi
else
    warn "uv non trouvé — tests API ignorés (installer : https://docs.astral.sh/uv/getting-started/installation/)"
fi

# ------------------------------------------
# 2. Tests Worker Python (pytest)
# ------------------------------------------
step "2. Tests Worker Python..."
if command -v uv &>/dev/null; then
    RESULT=$(uv run pytest apps/worker/tests/ -q --tb=no 2>&1 | tail -3)
    echo "$RESULT"
    if echo "$RESULT" | grep -qE "passed|no tests ran"; then
        ok "Tests Worker OK"
    else
        fail "Tests Worker échoués — corriger avant déploiement"
    fi
else
    warn "uv non trouvé — tests Worker ignorés"
fi

# ------------------------------------------
# 3. TypeScript check (apps/web)
# ------------------------------------------
step "3. TypeScript check (apps/web)..."
if command -v pnpm &>/dev/null; then
    RESULT=$(cd apps/web && pnpm typecheck 2>&1 | tail -5)
    echo "$RESULT"
    if echo "$RESULT" | grep -qE "error TS|Error"; then
        fail "Erreurs TypeScript détectées — corriger avant déploiement"
    else
        ok "TypeScript OK (0 erreur)"
    fi
else
    warn "pnpm non trouvé — typecheck ignoré (installer : https://pnpm.io/installation)"
fi

# ------------------------------------------
# 4. Build Next.js
# ------------------------------------------
step "4. Build Next.js (apps/web)..."
if command -v pnpm &>/dev/null; then
    RESULT=$(cd apps/web && pnpm build 2>&1 | tail -5)
    echo "$RESULT"
    if echo "$RESULT" | grep -qE "error|Error|failed|Failed"; then
        fail "Build Next.js échoué — corriger avant déploiement"
    else
        ok "Build Next.js OK"
    fi
else
    warn "pnpm non trouvé — build Next.js ignoré"
fi

# ------------------------------------------
# 5. Docker build — API FastAPI
# ------------------------------------------
step "5. Docker build API (apps/api/Dockerfile)..."
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    RESULT=$(docker build -f apps/api/Dockerfile -t mealplanner-api-test:latest . 2>&1 | tail -3)
    echo "$RESULT"
    if echo "$RESULT" | grep -qE "Successfully built|FINISHED|naming"; then
        ok "Docker build API OK"
        # Nettoyage de l'image de test
        docker rmi mealplanner-api-test:latest &>/dev/null || true
    else
        fail "Docker build API échoué — corriger avant déploiement"
    fi
else
    warn "Docker non disponible — build API ignoré"
fi

# ------------------------------------------
# 6. Docker build — Worker Celery
# ------------------------------------------
step "6. Docker build Worker (apps/worker/Dockerfile)..."
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    RESULT=$(docker build -f apps/worker/Dockerfile -t mealplanner-worker-test:latest . 2>&1 | tail -3)
    echo "$RESULT"
    if echo "$RESULT" | grep -qE "Successfully built|FINISHED|naming"; then
        ok "Docker build Worker OK"
        docker rmi mealplanner-worker-test:latest &>/dev/null || true
    else
        fail "Docker build Worker échoué — corriger avant déploiement"
    fi
else
    warn "Docker non disponible — build Worker ignoré"
fi

# ------------------------------------------
# 7. Vérification variables d'environnement critiques
# ------------------------------------------
step "7. Vérification variables d'environnement critiques..."

# Vérifier que .env.example est à jour (présence des variables obligatoires)
REQUIRED_VARS=(
    "DATABASE_URL"
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY"
    "SUPABASE_SERVICE_ROLE_KEY"
    "SUPABASE_JWT_SECRET"
    "REDIS_URL"
    "GOOGLE_AI_API_KEY"
    "NEXT_PUBLIC_SUPABASE_URL"
    "NEXT_PUBLIC_SUPABASE_ANON_KEY"
    "NEXT_PUBLIC_API_URL"
)

ENV_EXAMPLE=".env.example"
MISSING_VARS=0

if [ -f "$ENV_EXAMPLE" ]; then
    for var in "${REQUIRED_VARS[@]}"; do
        if ! grep -q "^${var}=" "$ENV_EXAMPLE"; then
            warn "Variable manquante dans .env.example : $var"
            MISSING_VARS=$((MISSING_VARS + 1))
        fi
    done

    if [ "$MISSING_VARS" -eq 0 ]; then
        ok ".env.example contient toutes les variables obligatoires"
    else
        warn "$MISSING_VARS variable(s) manquante(s) dans .env.example — mettre à jour avant déploiement"
    fi
else
    warn ".env.example introuvable — créer le fichier depuis .env.example.template"
fi

# ------------------------------------------
# 8. Vérification fichiers de déploiement
# ------------------------------------------
step "8. Vérification fichiers de déploiement..."

DEPLOY_FILES=(
    "railway.toml"
    "apps/web/vercel.json"
    "apps/api/Dockerfile"
    "apps/worker/Dockerfile"
    "docs/deployment.md"
)

for file in "${DEPLOY_FILES[@]}"; do
    if [ -f "$file" ]; then
        ok "$file présent"
    else
        fail "$file manquant — créer avant déploiement"
    fi
done

# ------------------------------------------
# Résumé final
# ------------------------------------------
echo ""
echo "=========================================="
if [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "${GREEN}Vérification terminée — TOUT OK${NC}"
    echo "Le projet est prêt pour le déploiement."
    echo ""
    echo "Prochaines étapes :"
    echo "  1. Railway : déployer presto-api + presto-worker"
    echo "  2. Vercel  : importer apps/web depuis GitHub"
    echo "  3. Supabase : appliquer 02-schema.sql + 04-phase2-schema.sql"
    echo "  4. Stripe  : configurer le webhook /api/v1/webhooks/stripe"
    echo ""
    echo "Voir : docs/deployment.md pour le guide complet"
else
    echo -e "${RED}Vérification terminée — ÉCHECS DÉTECTÉS${NC}"
    echo "Corriger les erreurs ci-dessus avant de déployer."
fi
echo "=========================================="

exit $EXIT_CODE
