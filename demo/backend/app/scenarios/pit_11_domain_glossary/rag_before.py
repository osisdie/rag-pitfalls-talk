"""Pit 11 · BEFORE — raw embed, no alias expansion."""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator
from app.core import embed, llm, qdrant, tracing
from app.models.schemas import CitationDetail


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


async def run_rag(ctx: RagContext) -> RagAnswer:
    vec = await embed.embed_one(ctx.query)
    client = qdrant.get_client()
    with tracing.stage("raw_embed_search"):
        hits = await client.query_points(collection_name="rule_doc", query=vec, using="dense", limit=3, with_payload=True)
    top = float(hits.points[0].score or 0.0) if hits.points else 0.0
    cites = [CitationDetail(
        source_name=(p.payload or {}).get("source_name", "rule_doc"), source_type="rule_doc",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]
    low_conf = top < 0.55
    prompt = (
        ("若信心太低，請直接回答『抱歉，找不到相符資料』。\n\n" if low_conf else "")
        + f"Context:\n" + "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
        + f"\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, top, [], False)
