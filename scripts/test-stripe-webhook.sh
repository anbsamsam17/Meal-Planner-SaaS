#!/bin/bash
# scripts/test-stripe-webhook.sh
#
# Simule un webhook Stripe checkout.session.completed en local.
# Utile pour tester le flow Stripe sans la CLI Stripe.
#
# ATTENTION : ce script utilise une signature factice ("test_signature").
# Le backend doit désactiver la vérification de signature en mode TEST
# (ENV=development) ou utiliser `stripe listen` pour des signatures valides.
#
# Usage :
#   bash scripts/test-stripe-webhook.sh
#   bash scripts/test-stripe-webhook.sh 8001          # port personnalisé
#   HOUSEHOLD_ID=real-uuid bash scripts/test-stripe-webhook.sh
#
# Méthode recommandée avec signature valide :
#   make stripe-listen
#   # Dans un autre terminal, déclencher un paiement Stripe test

set -euo pipefail

API_PORT="${1:-8001}"
HOUSEHOLD_ID="${HOUSEHOLD_ID:-test-household-uuid}"
API_BASE="http://localhost:${API_PORT}"

echo "Test webhook Stripe → ${API_BASE}/api/v1/webhooks/stripe"
echo "household_id : ${HOUSEHOLD_ID}"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/api/v1/webhooks/stripe" \
  -H "Content-Type: application/json" \
  -H "stripe-signature: test_signature" \
  -d "{
    \"type\": \"checkout.session.completed\",
    \"data\": {
      \"object\": {
        \"id\": \"cs_test_123\",
        \"customer\": \"cus_test_123\",
        \"subscription\": \"sub_test_123\",
        \"metadata\": {
          \"household_id\": \"${HOUSEHOLD_ID}\"
        }
      }
    }
  }")

HTTP_BODY=$(echo "$RESPONSE" | head -n -1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)

echo "HTTP ${HTTP_CODE}"
echo "${HTTP_BODY}" | python3 -m json.tool 2>/dev/null || echo "${HTTP_BODY}"

if [ "$HTTP_CODE" = "200" ]; then
  echo ""
  echo "Webhook traité avec succès."
elif [ "$HTTP_CODE" = "400" ]; then
  echo ""
  echo "Signature invalide (attendu en dev si STRIPE_WEBHOOK_SECRET est configuré)."
  echo "Utiliser 'make stripe-listen' pour des webhooks avec signature valide."
elif [ "$HTTP_CODE" = "503" ]; then
  echo ""
  echo "Stripe non configuré (STRIPE_SECRET_KEY absente). Ajouter dans .env.local."
else
  echo ""
  echo "Erreur inattendue. Vérifier les logs de l'API."
fi
