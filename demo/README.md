# Live Demo Stack

> Interactive 4-panel companion to the repo's 20 pitfall files.
> **Pick a scenario → watch the wrong answer → click *Apply Fix* → watch the right answer.**

## Panels

| Panel | What it shows |
|---|---|
| 💬 Chat | QA against the live RAG stack, with citations, confidence, typing animation, image thumbnails |
| 📝 rag.py | The retrieval code that just answered your question — one click swaps `bad → good` |
| 📐 Qdrant | Stock Qdrant dashboard iframe (collections, points, scroll filters live) |
| 🕸 Neo4j | Stock Neo4j Browser iframe (Graphiti episodes for temporal demos) |

## Quick start (local dev)

```bash
cd demo
cp .env.example .env
mkdir -p .secrets && cp ../service-account-key.json .secrets/   # your Vertex SA key
docker compose up -d
# open http://localhost
```

Default admin creds for Qdrant / Neo4j UIs (behind `/qdrant/*` and `/neo4j/*`):
`admin` / `rag-pitfalls-demo` — rotate before any public deployment.

## Services

| Service | Purpose |
|---|---|
| `caddy` | TLS + reverse proxy + basic auth for admin UIs |
| `frontend` | Next.js 15 dashboard (React 19, Tailwind) |
| `backend` | FastAPI · hot-reloadable `rag.py`, SSE chat, scenario controls |
| `embedder` | HF Text Embeddings Inference serving BGE-M3 (dense) |
| `qdrant` | Vector store · dense + BM25 sparse (server-side) |
| `neo4j` | Graphiti knowledge graph (only pits 5/6/8 seed it) |
| `postgres` | Chat sessions, message audit, `rag_versions` |
| `redis` | Last-5-turn hot memory + response cache |

## Environment

All real secrets live in `demo/.env` (gitignored). The repo-root `.env`
already carries `VERTEX_PROJECT_ID`, `DEFAULT_VERTEX_AI_LOCATION`, etc.;
copy those into `demo/.env` or just symlink:

```bash
ln -s ../.env .env
```

## Smoke test

```bash
curl http://localhost/health                     # 200 {ok:true}
curl http://localhost/api/llm                    # current LLM config
curl -N -X POST http://localhost/api/chat \
  -H 'content-type: application/json' \
  -d '{"message":"hello"}'                        # SSE stream
```

See the top-level `scripts/verify-services.sh` for the full check.

## Hot reload of `rag.py` — the neat trick

`backend/app/core/rag.py` is mutable at runtime. When you click **Apply
Fix**, the backend:

1. Reads `rag_after.py` from the active scenario
2. AST-parses it (fail fast, no disk write on syntax error)
3. Writes atomically (tmp + rename) to `rag.py`
4. Calls `importlib.reload(sys.modules["app.core.rag"])`
5. Records the swap in `rag_versions` (capped at 10 per scenario)

The `/api/chat` handler resolves the rag module **lazily per request**
(`sys.modules.get(...)`), so the next question you send runs through the
freshly-swapped code. No process restart, no container bounce.

If the reload raises `ImportError` (e.g. missing dep, broken def), the
backend auto-rolls-back to the last good source.
