#!/usr/bin/env bash
# Idempotent GCE firewall: SSH from SSH_SOURCE_CIDR, HTTP/HTTPS from 0.0.0.0/0.
set -euo pipefail

cd "$(dirname "$0")/../.."
source .env.infra

: "${GCP_PROJECT:?}"
: "${SSH_SOURCE_CIDR:=0.0.0.0/0}"

rule() {
  local name="$1"; shift
  if gcloud compute firewall-rules describe "$name" --project="$GCP_PROJECT" >/dev/null 2>&1; then
    echo "== [exists] $name"
  else
    echo "== creating $name"
    gcloud compute firewall-rules create "$name" "$@" --project="$GCP_PROJECT"
  fi
}

rule rag-pitfalls-demo-ssh \
  --direction=INGRESS --action=ALLOW --rules=tcp:22 \
  --target-tags=rag-pitfalls-demo --source-ranges="$SSH_SOURCE_CIDR"

rule rag-pitfalls-demo-http \
  --direction=INGRESS --action=ALLOW --rules=tcp:80,tcp:443 \
  --target-tags=rag-pitfalls-demo --source-ranges=0.0.0.0/0

echo "done"
