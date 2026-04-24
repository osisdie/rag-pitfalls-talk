# GCP infra for the live demo

One-VM, compose-on-boot, stopped-by-default. Typical cost: **≈ US$0.56 per talk day**,
**≈ US$3.60/month standby** (static IP + disk only).

## Required IAM roles (grant to the `gcloud` principal running these scripts)

| Role | Why |
|------|-----|
| `roles/compute.instanceAdmin.v1` | create / start / stop / delete VMs |
| `roles/compute.networkAdmin` | reserve static IP, add firewall rules |
| `roles/iam.serviceAccountUser` | attach the Vertex-AI SA to the VM |
| `roles/aiplatform.user` | let the VM call Vertex AI Gemini |
| `roles/iap.tunnelResourceAccessor` | (optional) if you want SSH via IAP |

Grant with:
```bash
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="user:you@example.com" \
  --role="roles/compute.instanceAdmin.v1"
# …repeat for the other roles
```

## Environment

All scripts read `.env.infra` at repo root (gitignored). Starter template:

```bash
# Required — fill in, do NOT commit
GCP_PROJECT=your-gcp-project-id                 # copy from ./.env VERTEX_PROJECT_ID
GCP_ZONE=us-central1-a                          # derived from DEFAULT_VERTEX_AI_LOCATION
VM_NAME=rag-pitfalls-demo
MACHINE_TYPE=e2-standard-4                      # 4 vCPU / 16 GB RAM — needed for BGE-M3
DISK_SIZE_GB=50
STATIC_IP_NAME=rag-pitfalls-demo-ip

# Optional
SSH_SOURCE_CIDR=0.0.0.0/0                       # recommend your-public-ip/32
HOSTNAME=                                        # leave blank for http://IP; set to domain for Let's Encrypt
REPO_URL=https://github.com/YOUR_ORG/rag-pitfalls-talk
REPO_BRANCH=main
SLACK_WEBHOOK_URL=                               # falls back to root .env's
```

## Lifecycle

```bash
# One-time (per GCP project):
./scripts/verify-gcp.sh                  # SA active, Vertex API enabled
./scripts/infra/firewall-rules.sh        # allow 22 from SSH_SOURCE_CIDR; 80/443 from 0.0.0.0/0
./scripts/infra/gcp-create-vm.sh         # creates VM, reserves static IP, runs bootstrap

# Every talk day:
./scripts/infra/gcp-start-vm.sh          # start VM, start compose, wait for health, Slack notify with IP/creds
# ... speaker runs 1-hour talk ...
./scripts/infra/gcp-stop-vm.sh           # compose down, shutdown VM, Slack notify cost saved

# End-of-campaign:
./scripts/infra/gcp-delete-vm.sh         # release static IP, delete VM + disk
```

## Security notes

- SSH is intentionally open to `SSH_SOURCE_CIDR` — set to `your-ip/32` after first boot.
- Neo4j Browser + Qdrant dashboard are proxied by Caddy. For public VM, copy
  `demo/caddy/Caddyfile.prod.example` → `Caddyfile`, set a real domain, and
  generate a bcrypt hash with `docker run --rm caddy:2 caddy hash-password`.
- Rotate the Neo4j password via `NEO4J_PASSWORD` env var in `demo/.env` between talks.
- The Vertex SA key in `service-account-key.json` is **host-mounted** into the
  container and gitignored. Preferred: attach an SA to the VM and let ADC auto-discover.
