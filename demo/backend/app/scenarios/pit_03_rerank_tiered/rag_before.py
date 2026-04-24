"""Pit 3 · BEFORE — cross-encoder over top-20.

Simulated CE latency (sleep 50 ms per pair × 20 pairs = 1 s) kills p95.
In real stacks this is an actual cross-encoder forward pass.
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


async def _cross_encoder_rerank(query: str, cands: list[dict]) -> list[tuple[dict, float]]:
    # Simulated CE — in production this is a full forward pass per (query, doc) pair.
    scored = []
    for c in cands:
        await asyncio.sleep(0.05)  # ~50 ms per pair
        # Fake score: count of query chars in doc text, normalised
        score = sum(1 for ch in query if ch in c.get("text", "")) / max(1, len(query))
        scored.append((c, score))
    return sorted(scored, key=lambda x: x[1], reverse=True)


async def _retrieve(query: str):
    vec = await embed.embed_one(query)
    client = qdrant.get_client()
    with tracing.stage("search_top20"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=20, with_payload=True)
    candidates = [p.payload or {} for p in hits.points]
    with tracing.stage("cross_encoder_all", n=len(candidates)):
        ranked = await _cross_encoder_rerank(query, candidates)
    cites = [CitationDetail(
        source_name=c.get("source_name", "FAQ"), source_type="faq",
        source_url=c.get("source_url"), chunk_text=c.get("text", ""),
        relevance_score=score,
    ) for c, score in ranked[:3]]
    return cites


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    # Tell the LLM to report the high-latency problem so the audience sees it.
    prompt = (
        "回答時請在開頭標註『⚠️ 高延遲 · high-latency path』以示範本 scenario 的問題。\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
