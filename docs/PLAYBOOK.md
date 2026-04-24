# Playbook · 1-hour Live Talk

Companion to `scripts/infra/`. Keep this file open on the speaker's laptop
during the talk — every command is copy-pasteable.

## Overview

```
T-24h   ← dry rehearsal on the real VM
T-2h    ← start VM, warm caches, post IP+creds to Slack
T-0     ← on-stage flow: intro → 4 hero demos → Q&A → close
T+after ← stop VM, archive demo highlights, cost check
```

All `BASE_URL` values default to your VM's public IP. Swap to `http://localhost`
for local rehearsal.

---

## T-24h · Dry rehearsal

Goal: every hero demo works end-to-end on the actual VM, once.

```bash
# Local host
cp .env.infra.example .env.infra    # fill in GCP project/zone
./scripts/verify-gcp.sh             # SA, Vertex API, quota
./scripts/infra/firewall-rules.sh   # one-time

./scripts/infra/gcp-create-vm.sh    # only the first time ever
./scripts/infra/gcp-start-vm.sh     # Slack will post the IP

export BASE_URL="http://<VM-IP>"
./scripts/verify-services.sh        # health of all 8 services
./scripts/seed-all.sh               # seeds every scenario idempotently
./scripts/verify-scenarios.sh --all # activate → ask → apply-fix → ask for all 20

./scripts/infra/gcp-stop-vm.sh      # save cost until T-2h
```

If `verify-scenarios.sh --all` fails:
1. Check which pit — log tells you.
2. Most common: embedder container still cold (BGE-M3 takes ~2 min first load).
3. Second most common: Vertex quota — check `gcloud services list --enabled`.

**Don't skip this step.** "It worked on my laptop" is where demos die on stage.

---

## T-2h · Warm-up

```bash
./scripts/infra/gcp-start-vm.sh
export BASE_URL="http://<VM-IP>"

# Pre-warm caches so the first audience question isn't a 3-second cold start.
for q in "hello" "營業時間" "誰是張主任"; do
  curl -sN -X POST "$BASE_URL/api/chat" -H 'content-type: application/json' \
    -d "{\"message\":\"$q\"}" > /dev/null
done

# Pre-activate the hero scenarios so their Qdrant collections + Neo4j episodes
# are loaded. This also records their rag_before.py in rag_versions.
for pit in pit_05_temporal_parser pit_07_content_hash_versioning \
           pit_10_entity_disambiguation pit_20_eval_framework; do
  curl -s -X POST "$BASE_URL/api/scenarios/$pit/activate"
done
```

Open the dashboard — `http://<VM-IP>` — in the browser you'll present from.
Confirm all 4 panels render (chat, code, Qdrant, Neo4j).

Post IP + admin creds to a private Slack DM as a failsafe.

---

## T-0 · On-stage flow

Total: 57 min talk + 10 min Q&A + 2 min hiring = 69 min (per `rag_pitfalls_talk.md`).
Hero demos go in the **Section 3 pit walkthroughs** — don't try to demo all 20.

### Demo A · Pit 5 · Relative time (Bucket 2, ~3 min)

1. Top-bar → Scenario dropdown → `Bucket 2 · pit_05_temporal_parser`
   (auto-seeds Qdrant `faq` collection, pre-fills probing question).
2. Send: **「最近的申報期限是什麼時候」**
   → Expect: `2019`-adjacent answer, `conf ~0.42`, freshness badge grey
3. Point at Code Panel — "this is the naive `temporal_search`".
4. Click **Apply Fix** → green banner "applied · vN".
5. New session (top-right in chat) → same question again.
   → Expect: `2026` answer, `conf ~0.7`, freshness = **current**.
   Audience reaction: "oh that's a whole different answer."

### Demo B · Pit 7 · Content-hash versioning (Bucket 2, ~3 min)

1. Scenario → `pit_07_content_hash_versioning`
2. Open Qdrant panel → collection `rule_doc` → scroll; note **two** docs with
   same `source_url` (v1: "5-7 天", v2: "3 天").
3. Send: **「理賠天數是多久」**
   → Expect: confused answer mixing both timelines.
4. **Apply Fix** → retrieval-side dedup by `source_url` + version.
5. Ask again → clean "3 天" answer, v2 cited as **current**.
6. Educational beat: "the *real* fix is at ingestion time, but this retrieval-
   side patch ships today without re-ingesting anything."

### Demo C · Pit 10 · Entity disambiguation (Bucket 3, ~3 min)

1. Scenario → `pit_10_entity_disambiguation`
2. Send: **「誰是張主任」**
   → Expect: generic "director" definition → "this is what dense-only gives you."
3. Point at Code Panel → show `DENSE_FLOOR = 0.2`, `ENTITY_BONUS = 0.15`.
4. **Apply Fix** → new session → same question.
   → Expect: employee record + **photo thumbnail** (SVG avatar).
5. Beat: "short queries need BM25, but BM25 without the dense-floor gate
   would put random lexical matches up top. Both guards matter."

### Demo D · Pit 20 · Eval framework (Bucket 6, ~4 min — signature pit)

1. Scenario → `pit_20_eval_framework`
2. Send: **「run golden benchmark」**
   → Expect: "🛠 Manual vibe check · Ship it!" — audience laughs.
3. **Apply Fix** → ask again.
   → Expect: bar chart across 4 RAGAS metrics, per-question diagnostic,
   CI gate decision (PASS/FAIL).
4. Closing beat: "this is the meta-pit. Without it, you never know if the
   other 19 fixes actually helped."

### Remaining 16 (Section 3 walkthroughs, code-only, ~25 min)

For each of pits 1, 2, 3, 4, 6, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19:
1. Scenario dropdown → select the pit (seeds on activate).
2. Show the Code Panel — just the diff between `rag_before.py` and `rag_after.py`.
3. ~1.5 min explanation. Don't run the full demo — that's what the audience
   can do after the talk.

### Q&A (10 min)

If an audience member asks "can you show me pit 17 live?", activate it and go.
All 20 scenarios are fully seeded and ready.

---

## T+after · Teardown

```bash
./scripts/infra/gcp-stop-vm.sh
```

Slack notification confirms `~$0.005/hr standby` cost. VM + static IP + disk
stay around so you can re-do the talk next week with zero config.

Full teardown (end-of-campaign):

```bash
./scripts/infra/gcp-delete-vm.sh
```

---

## Fallback chain if the VM dies mid-talk

| Failure | Fallback |
|---|---|
| Vertex quota exceeded | `/api/llm` → swap to `gemini-2.5-flash-lite` (lower quota). Slide 5 explains Gemini model tiers. |
| Embedder OOM | `docker compose restart embedder` on the VM. BGE-M3 re-loads in ~90 s; filler talk track. |
| Network gone | Pre-recorded hero-demo videos in `docs/videos/` (speaker's own recording, optional). |
| Qdrant corrupt | `./scripts/seed-all.sh` re-seeds all scenarios. |
| Whole stack panics | `docker compose down && docker compose up -d` on the VM. ~60 s. Ask Q&A first to buy time. |

Keep a browser tab open to `/health` during the talk — green `{"ok":true}` is
your "nothing broke yet" indicator.
