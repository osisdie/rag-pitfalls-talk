"""Pit 16 · AFTER — three independent cache layers:

    1. Embedding cache   — @lru_cache (process-lifetime, survives FAQ bust)
    2. Response cache    — Redis setex, 24h, scoped by scenario
    3. Image cache       — CDN (noted; not seeded in demo)

When FAQ updates, only layer 2 is busted. Layer 1 (embeddings) stays warm
because embeddings don't depend on FAQ answers — they depend on the query.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import AsyncIterator

from app.core import embed as embed_core, llm, qdrant, redis as app_redis, tracing
from app.models.schemas import CitationDetail

# Layer 1: naive in-proc cache of query → embedding (lru_cache cannot be
# async, so we wrap). In production use an async-aware cache like aiocache.
_embed_memo: dict[str, list[float]] = {}


async def _embed_cached(q: str) -> list[float]:
    if q in _embed_memo:
        return _embed_memo[q]
    v = await embed_core.embed_one(q)
    _embed_memo[q] = v
    return v


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


async def _from_cache(text: str):
    yield text


async def run_rag(ctx: RagContext) -> RagAnswer:
    rkey = f"layered:{ctx.scenario_id or 'default'}:{hashlib.sha256(ctx.query.encode()).hexdigest()[:16]}"
    with tracing.stage("layer2_response_cache"):
        cached = await app_redis.cache_response_get(rkey)
    if cached:
        return RagAnswer(_from_cache(cached["answer"]), [], float(cached.get("confidence", 0.0)), [], False)

    with tracing.stage("layer1_embed_cache", hit=ctx.query in _embed_memo):
        vec = await _embed_cached(ctx.query)
    client = qdrant.get_client()
    with tracing.stage("search"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=3, with_payload=True)
    cites = [CitationDetail(
        source_name=(p.payload or {}).get("source_name", "FAQ"), source_type="faq",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "回答時請在開頭標註『✅ layers: embed@lru + response@redis:24h + images@cdn』。\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    collected: list[str] = []

    async def passthrough():
        async for tok in llm.generate_stream(prompt):
            collected.append(tok)
            yield tok
        await app_redis.cache_response_set(rkey, {
            "answer": "".join(collected),
            "confidence": max((c.relevance_score for c in cites), default=0.0),
        }, ttl=86400)

    return RagAnswer(passthrough(), cites, max((c.relevance_score for c in cites), default=0.0), [], False)
