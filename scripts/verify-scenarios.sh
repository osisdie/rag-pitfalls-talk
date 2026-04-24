#!/usr/bin/env bash
# Automates: activate → ask → grep expected_before → apply-fix → ask → grep expected_after.
# Runs against the live compose stack.
#
# Usage:
#   ./scripts/verify-scenarios.sh                  # hero 4 only
#   ./scripts/verify-scenarios.sh --all            # every registered scenario
#   BASE_URL=https://vm-ip ./scripts/verify-scenarios.sh  # remote VM
set -euo pipefail

BASE="${BASE_URL:-http://localhost}"
MODE="hero"
if [[ "${1:-}" == "--all" ]]; then MODE="all"; fi

HERO=(pit_05_temporal_parser pit_07_content_hash_versioning pit_10_entity_disambiguation pit_20_eval_framework)

get_scenarios() {
  if [[ "$MODE" == "all" ]]; then
    curl -s "$BASE/api/scenarios" | python3 -c 'import sys,json; [print(s["pit_id"]) for s in json.load(sys.stdin)]'
  else
    printf '%s\n' "${HERO[@]}"
  fi
}

ask() {
  local msg="$1" sid="$2" scid="$3"
  curl -sN -X POST "$BASE/api/chat" \
    -H 'content-type: application/json' \
    -d "$(python3 -c "import json; print(json.dumps({'message': '$msg', 'session_id': '$sid' if '$sid' else None, 'scenario_id': '$scid'}))")" \
  | awk '
    /^data: / {
      sub(/^data: /, ""); line=$0
      if (state=="done") next
      if (event=="done") { print line; state="done" }
      if (event=="token") {
        # accumulate token chunks for grep
        # format: {"text":"..."}
        if (match(line, /"text":"[^"]*"/)) {
          t = substr(line, RSTART+8, RLENGTH-9)
          gsub(/\\n/, "\n", t); gsub(/\\"/, "\"", t)
          printf "%s", t
        }
      }
      next
    }
    /^event: / { event=$2 }
  '
  echo
}

FAIL=0
for pit in $(get_scenarios); do
  echo
  echo "== $pit =="

  # Look up expected substrings from the scenario metadata.
  meta=$(curl -s "$BASE/api/scenarios/$pit")
  before=$(echo "$meta" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["expected_before_substr"])')
  after=$(echo "$meta" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["expected_after_substr"])')
  probe=$(echo "$meta" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["probing_question"])')

  # Activate
  curl -s -X POST "$BASE/api/scenarios/$pit/activate" >/dev/null

  # Ask (before)
  sid=$(curl -s -X POST "$BASE/api/sessions/new?scenario_id=$pit" | python3 -c 'import sys,json; print(json.load(sys.stdin)["session_id"])')
  out_before=$(ask "$probe" "$sid" "$pit")
  if echo "$out_before" | grep -q "$before"; then
    echo "  ✓ before  matched '$before'"
  else
    echo "  ✗ before  expected '$before'"
    echo "    got: $(echo "$out_before" | head -c 200)…"
    FAIL=$((FAIL + 1))
  fi

  # Apply fix
  curl -s -X POST "$BASE/api/rag/apply-fix" >/dev/null

  # Ask (after) — new session so no memory contamination
  sid=$(curl -s -X POST "$BASE/api/sessions/new?scenario_id=$pit" | python3 -c 'import sys,json; print(json.load(sys.stdin)["session_id"])')
  out_after=$(ask "$probe" "$sid" "$pit")
  if echo "$out_after" | grep -q "$after"; then
    echo "  ✓ after   matched '$after'"
  else
    echo "  ✗ after   expected '$after'"
    echo "    got: $(echo "$out_after" | head -c 200)…"
    FAIL=$((FAIL + 1))
  fi
done

echo
if [[ $FAIL -gt 0 ]]; then
  echo "FAIL ($FAIL checks failed)"
  exit 1
fi
echo "OK"
