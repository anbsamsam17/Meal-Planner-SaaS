#!/bin/bash
# verify-before-done.sh — Stop hook
# Vérifie que Claude a mentionné un test/vérification avant de conclure.

INPUT=$(cat)
RESPONSE=$(echo "$INPUT" | jq -r '.stop_response // empty' 2>/dev/null)

if [ -z "$RESPONSE" ]; then
    exit 0
fi

VERIFY_PATTERNS="test|vérifié|vérifie|validé|valide|testé|teste|passent|passe|build|lint|fonctionne|confirm|checked|verified|passing|make test|pytest|vitest"

if echo "$RESPONSE" | grep -qiE "$VERIFY_PATTERNS"; then
    exit 0
fi

echo "RAPPEL: As-tu vérifié que tout fonctionne ? Lance 'make test' et 'make lint' et confirme que rien n'est cassé avant de conclure." >&2
exit 0
