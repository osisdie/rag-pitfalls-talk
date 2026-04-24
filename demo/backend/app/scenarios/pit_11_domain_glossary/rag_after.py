"""Pit 11 · AFTER — glossary expansion + RRF across variants."""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator
from app.core import embed, llm, qdrant, tracing
from app.models.schemas import CitationDetail

# Maps informal term → canonical + aliases. Real systems pull this from DB.
GLOSSARY = {
    "遞延負債": ["遞延所得稅負債", "DTL", "deferred tax liability"],
    "預付費用": ["遞延費用", "prepaid expenses"],
}

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


def _variants(q: str) -> list[str]:
    out = [q]
    for term, aliases in GLOSSARY.items():
        if term in q:
            out.extend(f"{q} {a}" for a in aliases)
    return out


async def run_rag(ctx: RagContext) -> RagAnswer:
    with tracing.stage("glossary_expand", n=len(_variants(ctx.query))):
        variants = _variants(ctx.query)
    client = qdrant.get_client()
    rankings: list[list[str]] = []
    payloads: dict[str, dict] = {}
    for v in variants:
        vec = await embed.embed_one(v)
        with tracing.stage(f"search_variant_{v[:10]}"):
            hits = await client.query_points(collection_name="rule_doc", query=vec, using="dense", limit=3, with_payload=True)
        ids = []
        for pt in hits.points:
            pid = str(pt.id)
            ids.append(pid)
            payloads[pid] = pt.payload or {}
        rankings.append(ids)
    scores: dict[str, float] = {}
    for r in rankings:
        for rank, pid in enumerate(r):
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (RRF_K + rank + 1)
    top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
    cites = [CitationDetail(
        source_name=payloads[pid].get("source_name", "rule_doc"), source_type="rule_doc",
        source_url=payloads[pid].get("source_url"), chunk_text=payloads[pid].get("text", ""),
        relevance_score=score,
    ) for pid, score in top]
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
