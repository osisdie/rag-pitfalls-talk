"""Pit 6 · BEFORE — timeless vector search returns latest version always."""
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


async def _single_chunk(text: str) -> AsyncIterator[str]:
    yield text


async def _retrieve(query: str):
    vec = await embed.embed_one(query)
    client = qdrant.get_client()
    with tracing.stage("search_timeless"):
        hits = await client.query_points(
            collection_name="rule_doc",
            query=vec,
            using="dense",
            limit=5,
            with_payload=True,
        )

    # Naive timeless behavior: prefer the latest known doc revision regardless
    # of the user's as-of intent.
    latest = None
    latest_ver = -1
    for pt in hits.points:
        p = pt.payload or {}
        ver = int(p.get("version", 0) or 0)
        if ver >= latest_ver:
            latest_ver = ver
            latest = pt
    points = [latest] if latest is not None else list(hits.points[:1])

    return [
        CitationDetail(
            source_name=(p.payload or {}).get("source_name", "rule_doc"),
            source_type="rule_doc",
            source_url=(p.payload or {}).get("source_url"),
            chunk_text=(p.payload or {}).get("text", ""),
            relevance_score=float(p.score or 0.0),
        )
        for p in points
    ]


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    answer = "依最新版本（v2）規則，付款期限為 60 天。"
    with tracing.stage("llm", model=llm.get_config().model):
        stream = _single_chunk(answer)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
