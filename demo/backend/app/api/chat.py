"""POST /api/chat — SSE streaming chat endpoint.

Protocol:
    event: token   data: {"text": "..."}       # tokens as they arrive
    event: done    data: {...ChatResponse...}  # final metadata envelope
    event: error   data: {"error": "..."}      # any stream-fatal error

Dual-write memory (Redis hot + PG cold) mirrors Agentory-CS.
"""
from __future__ import annotations

import json
import logging
import sys
import uuid

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core import pg
from app.core import redis as app_redis
from app.core import tracing
from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter()
log = logging.getLogger(__name__)


def _get_rag_module():
    """Resolve the LIVE rag module lazily so importlib.reload changes take effect."""
    if "app.core.rag" not in sys.modules:
        __import__("app.core.rag")
    return sys.modules["app.core.rag"]


@router.post("/chat")
async def chat(req: ChatRequest):
    tracing.start()

    session_id = req.session_id or await pg.create_session(scenario_id=req.scenario_id)
    if not await pg.session_exists(session_id):
        session_id = await pg.create_session(scenario_id=req.scenario_id)

    history = await app_redis.get_history(session_id)

    rag = _get_rag_module()
    ctx = rag.RagContext(
        query=req.message,
        session_id=session_id,
        history=history,
        scenario_id=req.scenario_id,
    )

    try:
        answer = await rag.run_rag(ctx)
    except Exception as exc:
        log.exception("run_rag failed: %s", exc)

        async def _error_gen():
            yield {"event": "error", "data": json.dumps({"error": str(exc)})}

        return EventSourceResponse(_error_gen())

    # Persist user turn now; assistant turn after stream completes.
    await app_redis.push_turn(session_id, "user", req.message)
    user_mid = await pg.append_message(session_id, "user", req.message)

    async def event_generator():
        collected: list[str] = []
        try:
            async for token in answer.answer_stream:
                collected.append(token)
                yield {"event": "token", "data": json.dumps({"text": token})}
        except Exception as exc:
            log.exception("stream iteration failed: %s", exc)
            yield {"event": "error", "data": json.dumps({"error": str(exc)})}
            return

        full_text = "".join(collected)
        await app_redis.push_turn(session_id, "assistant", full_text)
        assistant_mid = await pg.append_message(
            session_id,
            "assistant",
            full_text,
            citations=[c.model_dump(mode="json") for c in answer.citations],
            confidence=answer.confidence,
            handoff=answer.handoff,
        )

        latest = await pg.latest_version(scenario_id=req.scenario_id)
        resp = ChatResponse(
            answer=full_text,
            session_id=session_id,
            message_id=assistant_mid,
            citations=answer.citations,
            confidence=answer.confidence,
            thumbnails=answer.thumbnails,
            handoff=answer.handoff,
            timeline=tracing.events(),
            rag_version_id=latest["id"] if latest else None,
            scenario_id=req.scenario_id,
        )
        yield {"event": "done", "data": resp.model_dump_json()}
        _ = user_mid  # keep for future feedback correlation

    return EventSourceResponse(event_generator())
