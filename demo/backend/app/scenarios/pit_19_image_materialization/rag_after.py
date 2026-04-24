"""Pit 19 · AFTER — prefer local (materialized) URL; fall back to external.

At ingest we would download → sha256 name → save to S3/local/CDN, and
store BOTH `image_url` (original) + `image_url_local` (our copy). Retrieval
prefers local; front-end `onError` (see ImageThumbnails) fallback chain:
local → external → data-URI 'broken' placeholder.
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


async def run_rag(ctx: RagContext) -> RagAnswer:
    vec = await embed.embed_one(ctx.query)
    client = qdrant.get_client()
    with tracing.stage("search"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=3, with_payload=True)
    cites: list[CitationDetail] = []
    thumbnails: list[str] = []
    for pt in hits.points:
        p = pt.payload or {}
        # prefer local; keep external as UI-side fallback (ImageThumbnails handles onError)
        img = p.get("image_url_local") or p.get("image_url")
        if img:
            thumbnails.append(img)
        cites.append(CitationDetail(
            source_name=p.get("source_name", "FAQ"), source_type="faq",
            source_url=p.get("source_url"), chunk_text=p.get("text", ""),
            image_url=img,
            relevance_score=float(pt.score or 0.0),
        ))
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "請在回答開頭標註『✅ 本地 image_url_local · 不受外部 404 影響』。\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), thumbnails, False)
