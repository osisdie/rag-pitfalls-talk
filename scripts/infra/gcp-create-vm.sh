#!/usr/bin/env bash
# One-time VM creation: reserves a static IP, creates VM with startup script, tags for firewall.
set -euo pipefail

cd "$(dirname "$0")/../.."
source .env.infra

: "${GCP_PROJECT:?set GCP_PROJECT in .env.infra}"
: "${GCP_ZONE:?set GCP_ZONE in .env.infra}"
: "${VM_NAME:?set VM_NAME in .env.infra}"
: "${MACHINE_TYPE:=e2-standard-4}"
: "${DISK_SIZE_GB:=50}"
: "${STATIC_IP_NAME:=${VM_NAME}-ip}"

region="${GCP_ZONE%-*}"   # us-central1-a → us-central1

echo "== [1/3] reserving static IP $STATIC_IP_NAME in $region"
gcloud compute addresses describe "$STATIC_IP_NAME" --region="$region" --project="$GCP_PROJECT" \
  >/dev/null 2>&1 || \
  gcloud compute addresses create "$STATIC_IP_NAME" --region="$region" --project="$GCP_PROJECT"
ADDRESS=$(gcloud compute addresses describe "$STATIC_IP_NAME" --region="$region" --project="$GCP_PROJECT" --format='value(address)')
echo "   IP: $ADDRESS"

echo "== [2/3] creating VM $VM_NAME ($MACHINE_TYPE) in $GCP_ZONE"
gcloud compute instances create "$VM_NAME" \
  --project="$GCP_PROJECT" \
  --zone="$GCP_ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size="${DISK_SIZE_GB}GB" \
  --boot-disk-type=pd-balanced \
  --address="$ADDRESS" \
  --tags=rag-pitfalls-demo \
  --metadata-from-file=startup-script=scripts/infra/vm-bootstrap.sh \
  --scopes=cloud-platform

echo "== [3/3] waiting for SSH (~60 s)..."
for _ in {1..30}; do
  if gcloud compute ssh "$VM_NAME" --zone="$GCP_ZONE" --project="$GCP_PROJECT" --command='true' 2>/dev/null; then
    echo "   SSH OK"
    break
  fi
  sleep 3
done

echo
echo "VM created:  $ADDRESS"
echo "Next:       ./scripts/infra/gcp-start-vm.sh   # brings compose up"
echo "SSH:        gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --project=$GCP_PROJECT"
