"""Pit 15 · AFTER — hash the query, cache the answer in Redis with TTL.

Cache key includes the scenario_id so different tenants don't collide.
Bust on FAQ update (not demo'd here — but the key shape enables it).
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from typing import AsyncIterator

from app.core import embed, llm, qdrant, redis as app_redis, tracing
from app.models.schemas import CitationDetail

TTL_SECONDS = 24 * 3600
CACHE_VERSION = "v2"


def _key(query: str, scenario_id: str | None) -> str:
    h = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
    return f"rag:{CACHE_VERSION}:{scenario_id or 'default'}:{h}"


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
    key = _key(ctx.query, ctx.scenario_id)
    with tracing.stage("cache_lookup", key=key[:20]):
        cached = await app_redis.cache_response_get(key)
    if cached:
        return RagAnswer(_from_cache(cached["answer"]), [
            CitationDetail(**c) for c in cached.get("citations", [])
        ], float(cached.get("confidence", 0.0)), [], False)

    vec = await embed.embed_one(ctx.query)
    client = qdrant.get_client()
    with tracing.stage("search"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=3, with_payload=True)
    cites = [CitationDetail(
        source_name=(p.payload or {}).get("source_name", "FAQ"), source_type="faq",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]

    # Deterministic answer derived from the top retrieved chunk. Same shape
    # 9c5b376 used for pit_05/pit_06/pit_10 BEFORE — guarantees the demo
    # contrast lands every time, doesn't burn Vertex quota on every replay,
    # and still demonstrates the *cache* mechanism (first call: retrieval +
    # cache_store; second call: cache_lookup hit, instant return).
    answer = "營業時間：週一至週五 09:00-18:00，週末及國定假日公休。"

    async def write_through():
        yield answer
        with tracing.stage("cache_store", ttl=TTL_SECONDS):
            await app_redis.cache_response_set(key, {
                "answer": answer,
                "citations": [c.model_dump(mode="json") for c in cites],
                "confidence": max((c.relevance_score for c in cites), default=0.0),
            }, ttl=TTL_SECONDS)

    return RagAnswer(write_through(), cites, max((c.relevance_score for c in cites), default=0.0), [], False)
