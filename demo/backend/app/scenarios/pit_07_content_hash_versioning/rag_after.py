"""Pit 7 · AFTER — dedup by source_url, keeping highest version / newest published_at.

In an ideal pipeline the ingestion layer would `delete_by_filter(source_url)`
before upsert + content-hash versioning. Here we replicate the fix at the
retrieval tail so the pedagogy is visible even when seed data is messy.
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


def _dedup_by_source(cites: list[CitationDetail], payloads: list[dict]) -> list[CitationDetail]:
    """Keep highest version per source_url; break ties on published_at."""
    best: dict[str, tuple[int, str, CitationDetail]] = {}
    for c, p in zip(cites, payloads, strict=True):
        key = c.source_url or c.source_name
        version = int(p.get("version", 0))
        pub = str(p.get("published_at", ""))
        cur = best.get(key)
        if cur is None or (version, pub) > (cur[0], cur[1]):
            best[key] = (version, pub, c)
    return [v[2] for v in best.values()]


async def _retrieve(query: str) -> list[CitationDetail]:
    with tracing.stage("embed"):
        vec = await embed.embed_one(query)
    if not vec:
        return []
    client = qdrant.get_client()
    with tracing.stage("search_top_k"):
        hits = await client.query_points(
            collection_name="rule_doc",
            query=vec,
            using="dense",
            limit=8,
            with_payload=True,
        )
    cites: list[CitationDetail] = []
    payloads: list[dict] = []
    for pt in hits.points:
        p = pt.payload or {}
        cites.append(
            CitationDetail(
                source_name=p.get("source_name", "rule_doc"),
                source_type="rule_doc",
                source_url=p.get("source_url"),
                chunk_text=p.get("text", ""),
                freshness="current" if int(p.get("version", 0)) >= 2 else "stale",
                relevance_score=float(pt.score or 0.0),
            )
        )
        payloads.append(p)
    with tracing.stage("dedup_by_source_url", before=len(cites)):
        deduped = _dedup_by_source(cites, payloads)
    return deduped[:3]


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "根據 context 回答，引用的每份 rule_doc 都已去重為最新版本。\n\n"
        f"Context:\n{ctx_text or '(none)'}\n\n"
        f"User: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(
        answer_stream=stream,
        citations=cites,
        confidence=max((c.relevance_score for c in cites), default=0.0),
        thumbnails=[],
        handoff=False,
    )
