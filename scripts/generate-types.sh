#!/usr/bin/env bash
# scripts/generate-types.sh — Régénère les types TypeScript depuis l'OpenAPI FastAPI
#
# Usage :
#   bash scripts/generate-types.sh
#   # ou
#   make generate-types
#
# Prérequis :
#   - L'API FastAPI doit être démarrée sur localhost:8000
#   - npx doit être disponible (inclus avec Node.js)
#
# Ce script utilise openapi-typescript pour générer automatiquement
# les types TypeScript depuis le schéma OpenAPI exposé par FastAPI.
# Les types générés sont placés dans packages/shared-types/src/index.ts.
# Ne pas éditer ce fichier manuellement — relancer ce script après toute
# modification des schémas Pydantic côté API.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
API_URL="${API_BASE_URL:-http://localhost:8000}"
OUTPUT_FILE="$REPO_ROOT/packages/shared-types/src/index.ts"

echo "Génération des types TypeScript depuis $API_URL/openapi.json..."

# Vérifier que l'API est accessible
if ! curl -sf "$API_URL/openapi.json" > /dev/null; then
    echo "ERREUR : L'API FastAPI n'est pas accessible sur $API_URL"
    echo "Démarrer l'API avec : uv run uvicorn apps.api.src.main:app --reload --port 8000"
    exit 1
fi

# Créer le répertoire de sortie si nécessaire
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Générer les types via openapi-typescript
npx openapi-typescript "$API_URL/openapi.json" --output "$OUTPUT_FILE"

echo "Types TypeScript générés dans : $OUTPUT_FILE"
echo "Penser à commiter les changements si les types ont été modifiés."
