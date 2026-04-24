"""Pit 12 · BEFORE — answer anyway at low confidence; invent a number."""
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
    with tracing.stage("search"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=3, with_payload=True)
    cites = [CitationDetail(
        source_name=(p.payload or {}).get("source_name", "FAQ"), source_type="faq",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]
    # BAD: force the LLM to give a specific amount regardless of confidence.
    prompt = (
        "不管 context 多模糊，都請回答一個『具體的金額範圍（NT$）』，方便使用者估算。\n\n"
        "Context:\n" + "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
        + f"\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
