"""Pit 18 · AFTER — intent → collection routing."""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator

from app.core import embed, llm, qdrant, tracing
from app.models.schemas import CitationDetail

COLLECTION_FOR_INTENT = {
    "entity": "entity",
    "faq": "faq",
    "rule": "rule_doc",
    "temporal": "temporal",
}


def _classify_intent(q: str) -> str:
    if any(k in q for k in ("統編", "地址", "董事長", "誰是", "電話")):
        return "entity"
    if any(k in q for k in ("何時", "最近", "期限", "幾年")):
        return "temporal"
    if any(k in q for k in ("規定", "規則", "條款", "政策")):
        return "rule"
    return "faq"


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
    intent = _classify_intent(ctx.query)
    target = COLLECTION_FOR_INTENT[intent]
    with tracing.stage("route_by_intent", intent=intent, collection=target):
        pass
    vec = await embed.embed_one(ctx.query)
    client = qdrant.get_client()
    try:
        hits = await client.query_points(collection_name=target, query=vec, using="dense", limit=3, with_payload=True)
    except Exception:
        # Fallback to faq if the intent's collection isn't seeded this scenario.
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=3, with_payload=True)
    cites = [CitationDetail(
        source_name=(p.payload or {}).get("source_name", target), source_type=intent if intent in ("faq", "entity") else "rule_doc",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        f"[router: intent={intent} · collection={target}]\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
