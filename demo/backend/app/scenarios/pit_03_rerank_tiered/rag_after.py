"""Pit 3 · AFTER — tiered rerank: dense → top-5 → CE only on 5.

p50/p95 drops by ~4× because CE only runs on the promising short-list.
Trace events make the improvement visible in the Timeline panel.
"""
from __future__ import annotations
import asyncio
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


async def _ce_rerank(query: str, cands: list[dict]) -> list[tuple[dict, float]]:
    scored = []
    for c in cands:
        await asyncio.sleep(0.05)  # same per-pair cost
        score = sum(1 for ch in query if ch in c.get("text", "")) / max(1, len(query))
        scored.append((c, score))
    return sorted(scored, key=lambda x: x[1], reverse=True)


async def _retrieve(query: str):
    vec = await embed.embed_one(query)
    client = qdrant.get_client()
    with tracing.stage("search_top20"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=20, with_payload=True)
    with tracing.stage("dense_rescore_top5"):
        dense_top5 = [(p.payload or {}) for p in hits.points[:5]]
    with tracing.stage("cross_encoder_on_5", n=5):
        ranked = await _ce_rerank(query, dense_top5)
    cites = [CitationDetail(
        source_name=c.get("source_name", "FAQ"), source_type="faq",
        source_url=c.get("source_url"), chunk_text=c.get("text", ""),
        relevance_score=score,
    ) for c, score in ranked[:3]]
    return cites


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "回答時請在開頭標註『✅ tiered · dense→5→CE』以示範改進。\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
