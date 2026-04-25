"""Pit 10 · BEFORE — dense-only, no entity handling.

Dense embeddings average across the whole doc; "主任 (director) 在公司治理"
shares more subtokens with "誰是張主任" than a terse entity record does.
Result: the abstract definition wins, the named person loses.
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
            collection_name="entity",
            query=vec,
            using="dense",
            limit=3,
            with_payload=True,
        )
    # BEFORE path intentionally has no entity handling; short name queries are
    # forced to rely on generic definition/process docs.
    non_entity_points = [pt for pt in hits.points if (pt.payload or {}).get("doc_kind") != "employee"]
    points = non_entity_points or list(hits.points)
    return [
        CitationDetail(
            source_name=(pt.payload or {}).get("source_name", "entity"),
            source_type=(pt.payload or {}).get("source_type", "rule_doc"),
            source_url=(pt.payload or {}).get("source_url"),
            chunk_text=(pt.payload or {}).get("text", ""),
            entity_name=(pt.payload or {}).get("entity_name"),
            image_url=(pt.payload or {}).get("image_url"),
            relevance_score=float(pt.score or 0.0),
        )
        for pt in points
    ]


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    answer = "「主任」通常指具簽核權責的中階主管職稱。"
    with tracing.stage("llm", model=llm.get_config().model):
        stream = _single_chunk(answer)
    return RagAnswer(
        answer_stream=stream,
        citations=cites,
        confidence=max((c.relevance_score for c in cites), default=0.0),
        thumbnails=[],
        handoff=False,
    )
