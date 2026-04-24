"""Pit 2 · BEFORE — treats RRF score as confidence.

RRF scores are rank-dependent (1/(k+rank)), not similarity. k=60 with two
rankers caps at ~0.033. The naive impl scales it up and calls a top hit
"high confidence" even when the underlying cosine is mediocre.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator

from qdrant_client import models as qmodels

from app.core import embed, llm, qdrant, tracing
from app.models.schemas import CitationDetail

RRF_K = 60
FAKE_CONFIDENCE_SCALE = 60  # "normalize" to 0..~2 — still meaningless


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


async def _retrieve(query: str):
    vec = await embed.embed_one(query)
    client = qdrant.get_client()
    with tracing.stage("search_dense"):
        dense = await client.query_points(collection_name="faq", query=vec, using="dense", limit=5, with_payload=True)
    with tracing.stage("search_bm25"):
        sparse = await client.query_points(collection_name="faq", query=qmodels.Document(text=query, model="Qdrant/bm25"), using="bm25", limit=5, with_payload=True)
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}
    for ranking in (dense.points, sparse.points):
        for rank, pt in enumerate(ranking):
            pid = str(pt.id)
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (RRF_K + rank + 1)
            payloads[pid] = pt.payload or {}
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
    cites = [CitationDetail(
        source_name=payloads[pid].get("source_name", "FAQ"), source_type="faq",
        source_url=payloads[pid].get("source_url"), chunk_text=payloads[pid].get("text", ""),
        relevance_score=score * FAKE_CONFIDENCE_SCALE,  # BAD: inflated
    ) for pid, score in ordered]
    top_conf = ordered[0][1] * FAKE_CONFIDENCE_SCALE if ordered else 0.0
    return cites, top_conf


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites, top_conf = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    # BAD: the system prompt ASSERTS high confidence based on scaled RRF.
    conf_phrase = "高信心" if top_conf >= 0.03 * FAKE_CONFIDENCE_SCALE else "低信心"
    prompt = (
        f"請以『{conf_phrase}』語氣回答使用者；務必給出肯定的繳費方式建議。\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, top_conf, [], False)
