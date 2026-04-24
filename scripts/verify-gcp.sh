#!/usr/bin/env bash
# Pre-flight sanity: gcloud auth, project, Vertex API enabled, quota.
set -euo pipefail

cd "$(dirname "$0")/.."
source .env.infra 2>/dev/null || true

FAIL=0
row() { printf '  %-30s %s\n' "$1" "$2"; }
ok()  { row "$1" "✅ $2"; }
bad() { row "$1" "❌ $2"; FAIL=$((FAIL+1)); }

echo "== verify-gcp =="

if account=$(gcloud config get-value account 2>/dev/null); then
  ok "gcloud account" "$account"
else
  bad "gcloud account" "not logged in — run 'gcloud auth login'"
fi

: "${GCP_PROJECT:?set GCP_PROJECT in .env.infra}"
if gcloud projects describe "$GCP_PROJECT" >/dev/null 2>&1; then
  ok "project" "$GCP_PROJECT"
else
  bad "project" "$GCP_PROJECT — cannot describe"
fi

enabled=$(gcloud services list --enabled --project="$GCP_PROJECT" --format='value(config.name)' 2>/dev/null || true)
for svc in compute.googleapis.com aiplatform.googleapis.com; do
  if grep -q "^$svc$" <<<"$enabled"; then
    ok "$svc" "enabled"
  else
    bad "$svc" "not enabled — run 'gcloud services enable $svc --project=$GCP_PROJECT'"
  fi
done

region="${GCP_ZONE%-*}"
if quota=$(gcloud compute regions describe "$region" --project="$GCP_PROJECT" \
    --format='value(quotas[metric=CPUS].limit)' 2>/dev/null) && [[ -n "$quota" ]]; then
  ok "compute quota (CPUS) in $region" "$quota"
else
  row "compute quota" "(skipped)"
fi

echo
if [[ $FAIL -gt 0 ]]; then
  echo "FAIL ($FAIL checks failed)"
  exit 1
fi
echo "OK"
