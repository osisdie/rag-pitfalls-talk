"""POST /api/seed/reset (all) and POST /api/seed/{pit_id} (one)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.core import pg
from app.scenarios import registry
from app.scenarios.base import SeedContext, scenario_dir

router = APIRouter()
log = logging.getLogger(__name__)


async def _make_ctx(pit_id: str) -> SeedContext:
    async def record(label: str, source: str) -> int:
        return await pg.insert_version(pit_id, f"scenario:{pit_id}", label, source)

    return SeedContext(scenario_dir=scenario_dir(pit_id), rag_version_recorder=record)


@router.post("/seed/{pit_id}")
async def seed_one(pit_id: str) -> dict:
    sc = registry.get(pit_id)
    if sc is None:
        raise HTTPException(404, f"unknown scenario {pit_id}")
    ctx = await _make_ctx(pit_id)
    try:
        await sc.seed(ctx)
    except Exception as exc:
        log.exception("seed_one %s failed", pit_id)
        raise HTTPException(500, str(exc))
    return {"ok": True, "pit_id": pit_id}


@router.post("/seed/reset")
async def seed_all() -> dict:
    results: dict[str, str] = {}
    for sc in registry.all():
        ctx = await _make_ctx(sc.pit_id)
        try:
            await sc.seed(ctx)
            results[sc.pit_id] = "ok"
        except Exception as exc:
            log.exception("seed_all %s failed", sc.pit_id)
            results[sc.pit_id] = f"error: {exc}"
    return {"results": results}
