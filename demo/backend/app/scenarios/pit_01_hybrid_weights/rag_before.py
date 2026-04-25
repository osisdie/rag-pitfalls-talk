"""Pit 1 · BEFORE — `score = alpha*dense + (1-alpha)*sparse` with mismatched scales.

Dense cosine lives in [-1, 1]; BM25 is unbounded positive. Linear blending
lets BM25 dominate when any term matches, so a generic customer-service
doc that happens to share a token becomes the top hit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

from qdrant_client import models as qmodels

from app.core import embed, llm, qdrant, tracing
from app.models.schemas import CitationDetail

ALPHA = 0.3  # "tuned" weight — still wrong


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
    vec = await embed.embed_one(query)
    if not vec:
        return []
    client = qdrant.get_client()
    with tracing.stage("search_dense"):
        dense = await client.query_points(
            collection_name="faq", query=vec, using="dense", limit=5, with_payload=True
        )
    with tracing.stage("search_bm25"):
        sparse = await client.query_points(
            collection_name="faq",
            query=qmodels.Document(text=query, model="Qdrant/bm25"),
            using="bm25", limit=5, with_payload=True,
        )
    # Linear blend WITHOUT normalising. BM25 scale >> cosine scale → BM25 wins.
    merged: dict[str, tuple[float, dict]] = {}
    for pt in dense.points:
        pid = str(pt.id)
        merged[pid] = (ALPHA * float(pt.score or 0.0), pt.payload or {})
    for pt in sparse.points:
        pid = str(pt.id)
        prev = merged.get(pid, (0.0, pt.payload or {}))
        merged[pid] = (prev[0] + (1 - ALPHA) * float(pt.score or 0.0), prev[1])
    ordered = sorted(merged.items(), key=lambda kv: kv[1][0], reverse=True)[:3]
    return [
        CitationDetail(
            source_name=p.get("source_name", "FAQ"),
            source_type="faq",
            source_url=p.get("source_url"),
            chunk_text=p.get("text", ""),
            relevance_score=score,
        )
        for _, (score, p) in ordered
    ]


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "先提供可聯絡『客服』的建議，再補充其餘資訊。\n\n"
        f"Context:\n{ctx_text}\n\n"
        f"User: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
