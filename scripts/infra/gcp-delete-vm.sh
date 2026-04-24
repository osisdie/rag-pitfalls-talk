#!/usr/bin/env bash
# Full teardown: delete VM + disk + release static IP.
set -euo pipefail

cd "$(dirname "$0")/../.."
source .env.infra

: "${GCP_PROJECT:?}"; : "${GCP_ZONE:?}"; : "${VM_NAME:?}"
: "${STATIC_IP_NAME:=${VM_NAME}-ip}"
region="${GCP_ZONE%-*}"

read -r -p "This will DELETE $VM_NAME and release the static IP. Type 'yes' to continue: " CONFIRM
[[ "$CONFIRM" == "yes" ]] || { echo "aborted"; exit 1; }

gcloud compute instances delete "$VM_NAME" --zone="$GCP_ZONE" --project="$GCP_PROJECT" --delete-disks=all --quiet
gcloud compute addresses delete "$STATIC_IP_NAME" --region="$region" --project="$GCP_PROJECT" --quiet || true

echo "teardown complete"
