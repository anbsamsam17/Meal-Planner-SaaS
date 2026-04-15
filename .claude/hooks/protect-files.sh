#!/bin/bash
# protect-files.sh — PreToolUse hook (matcher: Edit|Write)
# Bloque les modifications sur les fichiers sensibles.
# Exit 0 = autorisé, Exit 2 = bloqué (stderr envoyé à Claude)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

PROTECTED_PATTERNS=(
    ".env"
    ".env.local"
    ".env.production"
    "secrets/"
    "pnpm-lock.yaml"
    "uv.lock"
    ".pre-commit-config.yaml"
    "docker-compose.dev.yml"
    "railway.toml"
    "apps/web/vercel.json"
    "infra/"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
    if [[ "$FILE_PATH" == *"$pattern"* ]]; then
        echo "BLOQUE: Impossible de modifier '$FILE_PATH' — fichier protégé ('$pattern')" >&2
        echo "Demande une autorisation explicite à l'utilisateur avant de modifier ce fichier." >&2
        exit 2
    fi
done

exit 0
