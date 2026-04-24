"""Pit 10 · AFTER — dense + BM25 sparse with entity-bonus and DENSE_FLOOR safeguard.

When the query is short (< 8 chars) we treat it as entity-biased: BM25
agreement earns a rank-fusion bonus, UNLESS dense similarity for the
candidate is below DENSE_FLOOR (0.2) — that's the safety valve that
stops pure-lexical matches on rare tokens from drowning real retrieval.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

from qdrant_client import models as qmodels

from app.core import embed, llm, qdrant, tracing
from app.models.schemas import CitationDetail

DENSE_FLOOR = 0.2
ENTITY_BONUS = 0.15
SHORT_QUERY_MAX_CHARS = 8


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


def _payload_to_cite(payload: dict, score: float, freshness: str | None = None) -> CitationDetail:
    return CitationDetail(
        source_name=payload.get("source_name", "entity"),
        source_type=payload.get("source_type", "entity"),
        source_url=payload.get("source_url"),
        chunk_text=payload.get("text", ""),
        entity_name=payload.get("entity_name"),
        image_url=payload.get("image_url"),
        freshness=freshness,  # type: ignore[arg-type]
        relevance_score=score,
    )


async def _hybrid(query: str) -> tuple[list[CitationDetail], list[str]]:
    is_short = len(query) <= SHORT_QUERY_MAX_CHARS
    with tracing.stage("embed"):
        vec = await embed.embed_one(query)
    if not vec:
        return [], []
    client = qdrant.get_client()

    # Dense pass
    with tracing.stage("search_dense"):
        dense = await client.query_points(
            collection_name="entity",
            query=vec,
            using="dense",
            limit=5,
            with_payload=True,
        )

    # Sparse (BM25) pass — Qdrant computes server-side from the raw query.
    with tracing.stage("search_bm25"):
        sparse = await client.query_points(
            collection_name="entity",
            query=qmodels.Document(text=query, model="Qdrant/bm25"),
            using="bm25",
            limit=5,
            with_payload=True,
        )

    # Merge: RRF across the two rankings, with a small entity bonus for
    # payload entries tagged as employees when the query is short.
    K = 60
    merged: dict[str, float] = {}
    payloads: dict[str, dict] = {}
    dense_scores: dict[str, float] = {}

    for rank, pt in enumerate(dense.points):
        pid = str(pt.id)
        merged[pid] = merged.get(pid, 0.0) + 1.0 / (K + rank + 1)
        payloads[pid] = pt.payload or {}
        dense_scores[pid] = float(pt.score or 0.0)

    for rank, pt in enumerate(sparse.points):
        pid = str(pt.id)
        merged[pid] = merged.get(pid, 0.0) + 1.0 / (K + rank + 1)
        payloads.setdefault(pid, pt.payload or {})

    if is_short:
        for pid, p in payloads.items():
            if p.get("doc_kind") == "employee" and dense_scores.get(pid, 0.0) >= DENSE_FLOOR:
                merged[pid] = merged.get(pid, 0.0) + ENTITY_BONUS

    ordered = sorted(merged.items(), key=lambda kv: kv[1], reverse=True)
    cites: list[CitationDetail] = []
    thumbnails: list[str] = []
    for pid, score in ordered[:3]:
        payload = payloads[pid]
        cite = _payload_to_cite(payload, score, freshness="current")
        cites.append(cite)
        if cite.image_url:
            thumbnails.append(cite.image_url)
    return cites, thumbnails


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites, thumbnails = await _hybrid(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "回答使用者的問題；若問到某人，請優先引用員工目錄資料。\n\n"
        f"Context:\n{ctx_text or '(none)'}\n\n"
        f"User: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(
        answer_stream=stream,
        citations=cites,
        confidence=max((c.relevance_score for c in cites), default=0.0),
        thumbnails=thumbnails,
        handoff=False,
    )
