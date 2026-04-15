#!/bin/bash
# post-edit-check.sh — PostToolUse hook (matcher: Edit|Write)
# Après chaque modification de fichier code, rappelle de vérifier.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
EXT="${FILE_PATH##*.}"

# Ne pas rappeler pour les fichiers non-code
case "$EXT" in
    md|json|yaml|yml|toml|txt|csv|sh|bat|ps1|lock)
        exit 0
        ;;
esac

if [ -n "$FILE_PATH" ]; then
    # Adapter le rappel selon le type de fichier
    case "$FILE_PATH" in
        *apps/api/*|*apps/worker/*|*packages/db/*)
            echo "[post-edit-check] Fichier Python modifié: $FILE_PATH — Pense à lancer 'make test-api' et 'make lint-api'"
            ;;
        *apps/web/*)
            echo "[post-edit-check] Fichier frontend modifié: $FILE_PATH — Pense à lancer 'make test-web' et 'make lint-web'"
            ;;
        *)
            echo "[post-edit-check] Fichier modifié: $FILE_PATH — Vérifie les tests et le linting"
            ;;
    esac
fi

exit 0
