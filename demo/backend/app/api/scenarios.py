"""GET /api/scenarios, POST /api/scenarios/{pit_id}/activate.

Activation (idempotent):
    1. Look up scenario in registry
    2. Call `scenario.seed(ctx)` to reset + seed scenario-scoped data
    3. Swap rag.py → rag_before.py + importlib.reload
    4. Record version in PG `rag_versions`
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.core import pg
from app.core import reload as rag_reload
from app.models.schemas import ScenarioMeta
from app.scenarios import registry
from app.scenarios.base import (
    SeedContext,
    rag_before_source,
    scenario_dir,
    scenario_meta,
)

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/scenarios", response_model=list[ScenarioMeta])
async def list_scenarios() -> list[ScenarioMeta]:
    return [scenario_meta(s) for s in registry.all()]


@router.get("/scenarios/{pit_id}", response_model=ScenarioMeta)
async def get_scenario(pit_id: str) -> ScenarioMeta:
    sc = registry.get(pit_id)
    if sc is None:
        raise HTTPException(404, f"unknown scenario {pit_id}")
    return scenario_meta(sc)


@router.post("/scenarios/{pit_id}/activate", response_model=ScenarioMeta)
async def activate_scenario(pit_id: str) -> ScenarioMeta:
    sc = registry.get(pit_id)
    if sc is None:
        raise HTTPException(404, f"unknown scenario {pit_id}")

    async def record(label: str, source: str) -> int:
        return await pg.insert_version(pit_id, f"scenario:{pit_id}", label, source)

    ctx = SeedContext(
        scenario_dir=scenario_dir(pit_id),
        rag_version_recorder=record,
    )
    try:
        await sc.seed(ctx)
    except Exception as exc:
        log.exception("seed failed for %s: %s", pit_id, exc)
        raise HTTPException(500, f"seed failed: {exc}")

    # Swap rag.py to the scenario's rag_before.py and reload.
    try:
        source = rag_before_source(pit_id)
    except FileNotFoundError:
        raise HTTPException(500, f"{pit_id}/rag_before.py missing")

    result = await rag_reload.apply_rag_source(
        source,
        scenario_id=pit_id,
        author=f"scenario:{pit_id}",
        label=f"{pit_id} · before (activate)",
    )
    if not result.ok:
        raise HTTPException(500, f"rag reload failed: {result.error}")

    return scenario_meta(sc, current_state="before")
