"""POST /api/sessions/new, DELETE /api/sessions/{id}, GET /api/sessions/{id}/messages."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core import pg
from app.core import redis as app_redis
from app.models.schemas import ChatMessage

router = APIRouter()


@router.post("/sessions/new")
async def create_session(scenario_id: str | None = None) -> dict:
    sid = await pg.create_session(scenario_id=scenario_id)
    return {"session_id": sid}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    await app_redis.clear_memory(session_id)
    await pg.delete_session(session_id)
    return {"ok": True}


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessage])
async def list_messages(session_id: str, limit: int = 50) -> list[ChatMessage]:
    if not await pg.session_exists(session_id):
        raise HTTPException(404, detail="session not found")
    rows = await pg.list_messages(session_id, limit=limit)
    return [
        ChatMessage(role=r["role"], content=r["content"], created_at=r["created_at"])
        for r in rows
    ]
