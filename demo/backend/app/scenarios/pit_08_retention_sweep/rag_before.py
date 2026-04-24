"""Pit 8 · BEFORE — archived docs still searchable, noisy results."""
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


async def _retrieve(query: str):
    vec = await embed.embed_one(query)
    client = qdrant.get_client()
    with tracing.stage("search_no_retention"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=3, with_payload=True)
    return [CitationDetail(
        source_name=(p.payload or {}).get("source_name", "FAQ"), source_type="faq",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
