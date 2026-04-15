#!/bin/bash
# auto-format.sh — PostToolUse hook (matcher: Edit|Write)
# Formate automatiquement les fichiers après modification.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

EXT="${FILE_PATH##*.}"

case "$EXT" in
    ts|tsx|js|jsx|json|css|scss|html|md)
        if command -v npx &>/dev/null; then
            npx prettier --write "$FILE_PATH" 2>/dev/null
        fi
        ;;
    py)
        if command -v ruff &>/dev/null; then
            ruff format "$FILE_PATH" 2>/dev/null
            ruff check --fix "$FILE_PATH" 2>/dev/null
        fi
        ;;
esac

exit 0
