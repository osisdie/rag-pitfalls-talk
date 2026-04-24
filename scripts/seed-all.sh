#!/usr/bin/env bash
# Idempotent: POST /api/seed/reset — re-seeds every registered scenario.
set -euo pipefail

BASE="${BASE_URL:-http://localhost}"
echo "== seed-all · base=$BASE"

resp=$(curl -fs -X POST "$BASE/api/seed/reset" || echo '{}')
python3 - <<PY
import json, sys
d = json.loads('''$resp''')
results = d.get("results", {})
if not results:
    print("no scenarios registered or server not reachable"); sys.exit(1)
fails = [k for k, v in results.items() if not str(v).startswith("ok")]
for k, v in sorted(results.items()):
    print(f"  {'✓' if str(v).startswith('ok') else '✗'}  {k}  {v}")
sys.exit(1 if fails else 0)
PY
