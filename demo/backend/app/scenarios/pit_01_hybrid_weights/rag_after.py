"""Pit 1 · AFTER — RRF (Reciprocal Rank Fusion) over rank lists.

RRF only cares about *ranks*, not scores. That makes it scale-free across
any two (or more) retrieval systems. `score(d) = sum over systems s of
1/(k + rank_s(d))`; k=60 is the Cormack et al. (2009) default.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

from qdrant_client import models as qmodels

from app.core import embed, llm, qdrant, tracing
from app.models.schemas import CitationDetail

RRF_K = 60


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


def _rrf_merge(rankings: list[list[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


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
    dense_ids = [str(p.id) for p in dense.points]
    sparse_ids = [str(p.id) for p in sparse.points]
    with tracing.stage("rrf_merge", k=RRF_K):
        merged = _rrf_merge([dense_ids, sparse_ids])
    payloads = {str(p.id): (p.payload or {}) for p in dense.points + sparse.points}
    cites = []
    for pid, score in merged[:3]:
        p = payloads.get(pid, {})
        cites.append(CitationDetail(
            source_name=p.get("source_name", "FAQ"),
            source_type="faq",
            source_url=p.get("source_url"),
            chunk_text=p.get("text", ""),
            relevance_score=score,
        ))
    return cites


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
