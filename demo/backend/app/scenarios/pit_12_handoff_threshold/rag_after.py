"""Pit 12 · AFTER — threshold gate routes low-confidence to human handoff."""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator

from app.core import embed, llm, pg as pg_core, qdrant, tracing
from app.models.schemas import CitationDetail

HANDOFF_THRESHOLD = 0.95


@dataclass
class RagContext:
    query: str
    session_id: str
    history: list[dict[str, str]]
    scenario_id: str | None = None


@dataclass
class RagAnswer:
    answer_stream: AsyncIterator[str]
    citations: list[CitationDetail]
    confidence: float
    thumbnails: list[str]
    handoff: bool


async def _queue_handoff(session_id: str, question: str, confidence: float) -> None:
    pool = await pg_core.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO handoff_queue (session_id, question, reason, confidence) VALUES ($1, $2, $3, $4)",
            session_id, question, "low_confidence", confidence,
        )


async def _handoff_stream(msg: str):
    for line in msg.split("\n"):
        yield line + "\n"


async def run_rag(ctx: RagContext) -> RagAnswer:
    vec = await embed.embed_one(ctx.query)
    client = qdrant.get_client()
    with tracing.stage("search"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=3, with_payload=True)
    top = float(hits.points[0].score or 0.0) if hits.points else 0.0
    cites = [CitationDetail(
        source_name=(p.payload or {}).get("source_name", "FAQ"), source_type="faq",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]

    if top < HANDOFF_THRESHOLD:
        with tracing.stage("enqueue_handoff", confidence=top):
            await _queue_handoff(ctx.session_id, ctx.query, top)
        return RagAnswer(
            _handoff_stream(
                f"這題需要個案評估，已為您『轉接』至專人（信心 {top:.2f} < {HANDOFF_THRESHOLD}）。\n"
                "請留電話，客服將於 1 小時內回撥。"
            ),
            cites, top, [], True,
        )

    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, top, [], False)
