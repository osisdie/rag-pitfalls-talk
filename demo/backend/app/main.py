"""FastAPI entrypoint.

Boot sequence:
    1. Register lifespan hooks that:
         - ensure rag.py is present (copy from .default on first boot)
         - import rag once so apply_fix reloads work later
         - run Alembic migrations upgrade head (best-effort; log on fail)
         - ensure Qdrant default collections exist
    2. Mount API routers under /api.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat as chat_api
from app.api import llm_config as llm_api
from app.api import sessions as sessions_api
from app.config import get_settings
from app.core import embed, graph, llm, pg, qdrant
from app.core import redis as app_redis
from app.core import reload as rag_reload

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info("rag-pitfalls demo backend starting · project=%s", settings.vertex_project_id)

    # rag.py bootstrap
    try:
        await rag_reload.ensure_live_from_default()
    except Exception as exc:
        log.error("Failed to bootstrap rag.py: %s", exc)

    # Best-effort infra readiness. Services may not be up yet in dev;
    # individual endpoints will surface per-call errors.
    try:
        await qdrant.ensure_all_defaults()
    except Exception as exc:
        log.warning("Qdrant not ready yet: %s", exc)

    yield

    # Teardown
    await embed.close()
    await qdrant.close()
    await graph.close()
    await pg.close()
    await app_redis.close()
    log.info("rag-pitfalls demo backend stopped")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s · %(message)s",
    )


_configure_logging()
app = FastAPI(
    title="RAG Pitfalls · Live Demo",
    version="0.1.0",
    lifespan=lifespan,
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    """Liveness probe for `verify-services.sh`."""
    return {"ok": True, "version": app.version}


app.include_router(chat_api.router, prefix="/api")
app.include_router(llm_api.router, prefix="/api")
app.include_router(sessions_api.router, prefix="/api")
# Phase 2 routers (scenarios, rag_code, seed) register themselves via plugin
# discovery below. Safe if their modules aren't imported yet.
try:
    from app.api import scenarios as scenarios_api
    from app.api import rag_code as rag_code_api
    from app.api import seed as seed_api

    app.include_router(scenarios_api.router, prefix="/api")
    app.include_router(rag_code_api.router, prefix="/api")
    app.include_router(seed_api.router, prefix="/api")
except ImportError:
    log.info("Phase 2 routers not present yet; skipping")

_ = llm  # silence "unused" for startup eagerness
