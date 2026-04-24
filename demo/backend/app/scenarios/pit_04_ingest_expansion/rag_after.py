"""Pit 4 · AFTER — pre-expanded variants, linked by canonical_id.

At ingest the LLM generates 3-5 phrasings per canonical FAQ and indexes
them all with a shared `canonical_id`. Retrieval matches any variant;
dedup collapses siblings back to one citation. Zero runtime LLM cost.
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


async def _retrieve(query: str):
    vec = await embed.embed_one(query)
    client = qdrant.get_client()
    with tracing.stage("search_variants"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=6, with_payload=True)

    # Collapse variants back to canonical: keep best-scoring per canonical_id.
    best: dict[str, tuple[float, dict]] = {}
    for pt in hits.points:
        p = pt.payload or {}
        key = p.get("canonical_id") or p.get("source_url") or p.get("source_name", "")
        score = float(pt.score or 0.0)
        if key not in best or score > best[key][0]:
            best[key] = (score, p)
    ordered = sorted(best.values(), key=lambda kv: kv[0], reverse=True)[:3]
    return [CitationDetail(
        source_name=p.get("source_name", "FAQ"), source_type="faq",
        source_url=p.get("source_url"), chunk_text=p.get("text", ""),
        freshness="current", relevance_score=score,
    ) for score, p in ordered]


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "請在回答開頭標註『✅ ingest-time variant · 無 runtime HyDE』，依 context 回答。\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
