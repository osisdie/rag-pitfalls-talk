"""Pit 5 · BEFORE — dense-only retrieval, no temporal awareness.

Why it fails: user asks "最近的申報期限是什麼時候". "最近" (recent) carries
no vector signal the embedder cares about; dense similarity peaks on whatever
doc shares the most lexical/semantic tokens with "申報期限". Often a 2019
announcement that mentions the phrase most explicitly.
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


async def _single_chunk(text: str) -> AsyncIterator[str]:
    yield text


async def _retrieve(query: str) -> list[CitationDetail]:
    with tracing.stage("embed"):
        vec = await embed.embed_one(query)
    if not vec:
        return []
    client = qdrant.get_client()
    with tracing.stage("search_dense_only"):
        hits = await client.query_points(
            collection_name="faq",
            query=vec,
            using="dense",
            limit=3,
            with_payload=True,
        )
    return [
        CitationDetail(
            source_name=(pt.payload or {}).get("source_name", "FAQ"),
            source_type="faq",
            source_url=(pt.payload or {}).get("source_url"),
            chunk_text=(pt.payload or {}).get("text", ""),
            relevance_score=float(pt.score or 0.0),
        )
        for pt in hits.points
    ]


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    answer = "最近可參考 2019 年公告，申報期限為 2020 年 5 月 31 日。"
    with tracing.stage("llm", model=llm.get_config().model):
        stream = _single_chunk(answer)
    return RagAnswer(
        answer_stream=stream,
        citations=cites,
        confidence=max((c.relevance_score for c in cites), default=0.0),
        thumbnails=[],
        handoff=False,
    )
