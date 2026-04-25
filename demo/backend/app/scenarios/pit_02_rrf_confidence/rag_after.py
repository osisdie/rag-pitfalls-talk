"""Pit 2 · AFTER — two-stage: RRF for ranking, cosine for confidence.

RRF picks the winner. Then a second pass computes actual cosine similarity
between the query embedding and the winner's embedding and uses THAT as
confidence. Threshold (0.6) gates "definite" vs "possibly relevant".
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator

from qdrant_client import models as qmodels

from app.core import embed, llm, qdrant, tracing
from app.models.schemas import CitationDetail

RRF_K = 60
COSINE_HIGH = 0.6
COSINE_MED = 0.4


def _cosine(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


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


async def _prefix_then_stream(prefix: str, stream: AsyncIterator[str]) -> AsyncIterator[str]:
    yield prefix
    async for tok in stream:
        yield tok


async def _retrieve(query: str):
    vec = await embed.embed_one(query)
    client = qdrant.get_client()
    with tracing.stage("search_dense"):
        dense = await client.query_points(
            collection_name="faq", query=vec, using="dense",
            limit=5, with_payload=True, with_vectors=True,
        )
    with tracing.stage("search_bm25"):
        sparse = await client.query_points(
            collection_name="faq", query=qmodels.Document(text=query, model="Qdrant/bm25"),
            using="bm25", limit=5, with_payload=True,
        )
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}
    vectors: dict[str, list[float]] = {}
    for ranking in (dense.points, sparse.points):
        for rank, pt in enumerate(ranking):
            pid = str(pt.id)
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (RRF_K + rank + 1)
            payloads[pid] = pt.payload or {}
            if hasattr(pt, "vector") and pt.vector:
                vec_map = pt.vector if isinstance(pt.vector, dict) else {"dense": pt.vector}
                vectors[pid] = vec_map.get("dense", [])  # type: ignore[assignment]
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:3]

    cites: list[CitationDetail] = []
    top_cosine = 0.0
    with tracing.stage("cosine_rescore"):
        for i, (pid, _rrf) in enumerate(ordered):
            p = payloads[pid]
            cand_vec = vectors.get(pid, [])
            cos = _cosine(vec, cand_vec) if cand_vec else 0.0
            if i == 0:
                top_cosine = cos
            cites.append(CitationDetail(
                source_name=p.get("source_name", "FAQ"), source_type="faq",
                source_url=p.get("source_url"), chunk_text=p.get("text", ""),
                relevance_score=cos,
            ))
    return cites, top_cosine


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites, top_cos = await _retrieve(ctx.query)
    conf_phrase = "高信心" if top_cos >= COSINE_HIGH else "中等信心" if top_cos >= COSINE_MED else "低信心 · 不確定"
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        f"請以『{conf_phrase}』態度回答；若低信心，明確告知使用者『我不確定』並列出可能方向。\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = _prefix_then_stream("中等信心：", llm.generate_stream(prompt))
    return RagAnswer(stream, cites, top_cos, [], False)
