#!/usr/bin/env bash
# Start VM + bring compose up + health-check + Slack notify.
set -euo pipefail

cd "$(dirname "$0")/../.."
source .env.infra

: "${GCP_PROJECT:?}"; : "${GCP_ZONE:?}"; : "${VM_NAME:?}"

echo "== starting VM $VM_NAME"
gcloud compute instances start "$VM_NAME" --zone="$GCP_ZONE" --project="$GCP_PROJECT" || true

# Wait for SSH
for _ in {1..30}; do
  if gcloud compute ssh "$VM_NAME" --zone="$GCP_ZONE" --project="$GCP_PROJECT" --command='true' 2>/dev/null; then
    break
  fi
  sleep 3
done

echo "== starting compose stack"
gcloud compute ssh "$VM_NAME" --zone="$GCP_ZONE" --project="$GCP_PROJECT" --command="
  set -e
  cd /opt/rag-pitfalls-talk
  if [[ ! -f demo/.env ]]; then
    cp demo/.env.example demo/.env
    echo 'HINT: edit /opt/rag-pitfalls-talk/demo/.env if you need to override anything'
  fi
  cd demo && docker compose up -d
"

IP=$(gcloud compute instances describe "$VM_NAME" --zone="$GCP_ZONE" --project="$GCP_PROJECT" \
  --format='value(networkInterfaces[0].accessConfigs[0].natIP)')

echo "== waiting for Caddy on $IP"
for _ in {1..30}; do
  if curl -fs "http://$IP/health" >/dev/null 2>&1; then
    echo "   backend /health OK"
    break
  fi
  sleep 3
done

MSG="[rag-pitfalls-talk] VM up · http://$IP · Qdrant: http://$IP/qdrant/dashboard · Neo4j: http://$IP/neo4j/browser/"
echo "== $MSG"

# Slack notify — prefer project helper, fall back to direct webhook.
if [[ -f scripts/slack_notify.sh ]]; then
  # shellcheck disable=SC1091
  source scripts/slack_notify.sh && slack_send "$MSG" || true
elif [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
  curl -s -X POST -H 'content-type: application/json' \
    -d "{\"text\":\"$MSG\"}" "$SLACK_WEBHOOK_URL" || true
fi
