#!/usr/bin/env bash
# Bring compose down + shutdown VM + Slack notify (cost saved).
set -euo pipefail

cd "$(dirname "$0")/../.."
source .env.infra

: "${GCP_PROJECT:?}"; : "${GCP_ZONE:?}"; : "${VM_NAME:?}"

echo "== stopping compose stack"
gcloud compute ssh "$VM_NAME" --zone="$GCP_ZONE" --project="$GCP_PROJECT" --command="
  cd /opt/rag-pitfalls-talk/demo && docker compose down
" || echo "   (compose already down, continuing)"

echo "== stopping VM"
gcloud compute instances stop "$VM_NAME" --zone="$GCP_ZONE" --project="$GCP_PROJECT"

MSG="[rag-pitfalls-talk] VM stopped · ~\$0.005/hr standby (disk only)"
echo "== $MSG"

if [[ -f scripts/slack_notify.sh ]]; then
  # shellcheck disable=SC1091
  source scripts/slack_notify.sh && slack_send "$MSG" || true
elif [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
  curl -s -X POST -H 'content-type: application/json' -d "{\"text\":\"$MSG\"}" "$SLACK_WEBHOOK_URL" || true
fi
