#!/usr/bin/env bash
set -euo pipefail

: "${CF_API_TOKEN:?Defina CF_API_TOKEN}"
: "${CF_ACCOUNT_ID:?Defina CF_ACCOUNT_ID}"
: "${CF_ZONE_ID:?Defina CF_ZONE_ID}"
: "${CF_HOSTNAME:?Defina CF_HOSTNAME}"

TUNNEL_NAME="${TUNNEL_NAME:-isabel}"

echo "Criando Tunnel $TUNNEL_NAME..."

RESP=$(curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/cfd_tunnel" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{\"name\":\"${TUNNEL_NAME}\",\"config_src\":\"cloudflare\"}")

echo "$RESP" | jq .

TUNNEL_ID=$(echo "$RESP" | jq -r '.result.id // empty')
if [ -z "$TUNNEL_ID" ]; then
  echo "Falha ao criar tunnel"
  exit 1
fi

echo "Tunnel ID: $TUNNEL_ID"

TOKEN_RESP=$(curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/token" \
  -H "Authorization: Bearer ${CF_API_TOKEN}")

TOKEN=$(echo "$TOKEN_RESP" | jq -r '.result // empty')
echo "CLOUDFLARE_TUNNEL_TOKEN=$TOKEN"

curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{\"type\":\"CNAME\",\"name\":\"${CF_HOSTNAME}\",\"content\":\"${TUNNEL_ID}.cfargotunnel.com\",\"proxied\":true}" | jq .

echo "Pronto. Adicione o token no .env e suba o cloudflared."
