"""GET /api/rag/current · POST /api/rag/apply-fix · POST /api/rag/save · GET /api/rag/versions · POST /api/rag/revert/{v}."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.core import pg
from app.core import reload as rag_reload
from app.models.schemas import ApplyFixResult, RagVersion, SaveCodeRequest
from app.scenarios import registry
from app.scenarios.base import rag_after_source

router = APIRouter()
log = logging.getLogger(__name__)


async def _active_scenario_id() -> str | None:
    """Best-effort: last scenario-authored version wins.

    The demo is single-speaker so we can rely on chronological order of
    rag_versions rows to infer "which scenario is currently active".
    """
    row = await pg.latest_version(scenario_id=None)
    if not row:
        return None
    sid = row.get("scenario_id")
    return sid if sid in {s.pit_id for s in registry.all()} else None


@router.get("/rag/current")
async def get_current() -> dict:
    source = rag_reload.read_current_source()
    latest = await pg.latest_version(scenario_id=None)
    return {
        "source": source,
        "version_id": latest["id"] if latest else None,
        "label": latest["label"] if latest else None,
        "scenario_id": latest["scenario_id"] if latest else None,
    }


@router.post("/rag/apply-fix", response_model=ApplyFixResult)
async def apply_fix() -> ApplyFixResult:
    pit_id = await _active_scenario_id()
    if pit_id is None:
        raise HTTPException(400, "no active scenario — activate one first")
    try:
        source = rag_after_source(pit_id)
    except FileNotFoundError:
        raise HTTPException(500, f"{pit_id}/rag_after.py missing")
    return await rag_reload.apply_rag_source(
        source,
        scenario_id=pit_id,
        author=f"scenario:{pit_id}",
        label=f"{pit_id} · after (apply-fix)",
    )


@router.post("/rag/save", response_model=ApplyFixResult)
async def save_code(req: SaveCodeRequest) -> ApplyFixResult:
    pit_id = await _active_scenario_id()
    return await rag_reload.apply_rag_source(
        req.source,
        scenario_id=pit_id,
        author="manual",
        label=req.label,
    )


@router.get("/rag/versions", response_model=list[RagVersion])
async def versions(scenario_id: str | None = None) -> list[RagVersion]:
    rows = await pg.list_versions(scenario_id=scenario_id, limit=10)
    return [
        RagVersion(
            id=r["id"],
            label=r["label"],
            source=r["source"],
            author=r["author"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/rag/revert/{version_id}", response_model=ApplyFixResult)
async def revert(version_id: int) -> ApplyFixResult:
    return await rag_reload.revert_to_version(version_id)
