"""Pit 7 · BEFORE — dense retrieval, no dedup.

Both v1 (2022 · "5-7 天") and v2 (2026 · "3 天") live in the collection
with identical source_url. Dense retrieval happily returns both, LLM
synthesises a confused answer ("somewhere between 3 and 7 days").
"""
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


async def _retrieve(query: str) -> list[CitationDetail]:
    with tracing.stage("embed"):
        vec = await embed.embed_one(query)
    if not vec:
        return []
    client = qdrant.get_client()
    with tracing.stage("search_no_dedup"):
        hits = await client.query_points(
            collection_name="rule_doc",
            query=vec,
            using="dense",
            limit=5,
            with_payload=True,
        )
    return [
        CitationDetail(
            source_name=(pt.payload or {}).get("source_name", "rule_doc"),
            source_type="rule_doc",
            source_url=(pt.payload or {}).get("source_url"),
            chunk_text=(pt.payload or {}).get("text", ""),
            relevance_score=float(pt.score or 0.0),
        )
        for pt in hits.points
    ]


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "根據 context 回答，直接引用相關規則。\n\n"
        f"Context:\n{ctx_text or '(none)'}\n\n"
        f"User: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(
        answer_stream=stream,
        citations=cites,
        confidence=max((c.relevance_score for c in cites), default=0.0),
        thumbnails=[],
        handoff=False,
    )
