"""Pit 19 · BEFORE — only external image_url cached, now 404s in production."""
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
        # BAD: only external URL; when it 404s the browser shows a broken thumb.
        if p.get("image_url"):
            thumbnails.append(p["image_url"])
        cites.append(CitationDetail(
            source_name=p.get("source_name", "FAQ"), source_type="faq",
            source_url=p.get("source_url"), chunk_text=p.get("text", ""),
            image_url=p.get("image_url"),
            relevance_score=float(pt.score or 0.0),
        ))
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "請在回答開頭標註『⚠️ 外部圖片 URL · 可能 404』。\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), thumbnails, False)
