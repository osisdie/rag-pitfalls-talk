#!/usr/bin/env bash
# Health-check every service in the demo compose stack.
# Usage: ./scripts/verify-services.sh [BASE_URL]
#   BASE_URL defaults to http://localhost (set to https://vm-ip for GCP).
set -euo pipefail

BASE="${1:-http://localhost}"
FAIL=0

check() {
  local name="$1" url="$2" expect="${3:-200}"
  local status
  status=$(curl -s -o /dev/null -w '%{http_code}' -m 5 "$url" || echo "000")
  if [[ "$status" == "$expect" ]]; then
    printf '  \e[32m✓\e[0m %-12s %s (HTTP %s)\n' "$name" "$url" "$status"
  else
    printf '  \e[31m✗\e[0m %-12s %s (HTTP %s, expected %s)\n' "$name" "$url" "$status" "$expect"
    FAIL=$((FAIL + 1))
  fi
}

echo "== verify-services · base=$BASE =="

# FastAPI + Next.js
check "backend"  "$BASE/health"
check "frontend" "$BASE/"

# LLM config endpoint (proves Vertex is reachable at least at the config layer)
check "api/llm"  "$BASE/api/llm"

# Qdrant / Neo4j iframes (expected behind basic auth — 401 is success)
check "qdrant"   "$BASE/qdrant/dashboard" "401"
check "neo4j"    "$BASE/neo4j/browser/"   "401"

# Postgres / Redis / Embedder — only reachable from inside the compose network.
# If running this from a host with docker-compose access, uncomment:
#   docker compose exec postgres pg_isready -U demo
#   docker compose exec redis redis-cli PING
#   docker compose exec embedder curl -s http://localhost/health

if [[ "$FAIL" -gt 0 ]]; then
  echo "FAIL ($FAIL checks failed)"
  exit 1
fi
echo "OK"
