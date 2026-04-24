#!/usr/bin/env bash
# Runs once on first VM boot via GCE startup-script metadata. Idempotent.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git gnupg lsb-release

# Docker Engine + compose plugin
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Clone repo (if REPO_URL metadata present)
REPO_URL=$(curl -sS --fail -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/repo-url 2>/dev/null || true)
REPO_BRANCH=$(curl -sS --fail -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/repo-branch 2>/dev/null || echo main)
if [[ -n "$REPO_URL" && ! -d /opt/rag-pitfalls-talk ]]; then
  git clone --branch "$REPO_BRANCH" "$REPO_URL" /opt/rag-pitfalls-talk
fi

# Pre-pull large images so the first 'compose up' is fast.
if [[ -f /opt/rag-pitfalls-talk/demo/docker-compose.yml ]]; then
  cd /opt/rag-pitfalls-talk/demo
  docker compose pull embedder qdrant neo4j postgres redis caddy || true
fi

echo "bootstrap complete"
