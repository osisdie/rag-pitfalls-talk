"""Pit 9 · AFTER — rule-based intent router, parallelized with embedding.

In production the classifier would be a tiny LLM call; here we use keyword
rules so the demo stays fast and deterministic. The teaching is the SHAPE:
branch before you pay the full RAG cost.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import AsyncIterator
from app.core import embed, llm, qdrant, tracing
from app.models.schemas import CitationDetail

CHITCHAT = ("你好", "hi", "hello", "謝謝", "thank")
HANDOFF = ("投訴", "客訴", "生氣", "要告", "complaint")


def _classify(q: str) -> str:
    if any(k in q.lower() for k in CHITCHAT):
        return "chitchat"
    if any(k in q for k in HANDOFF):
        return "handoff"
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


async def _canned(text: str) -> AsyncIterator[str]:
    for line in text.split("\n"):
        yield line + "\n"


async def run_rag(ctx: RagContext) -> RagAnswer:
    with tracing.stage("intent_classify_and_embed_parallel"):
        intent, vec = await asyncio.gather(
            asyncio.to_thread(_classify, ctx.query),
            embed.embed_one(ctx.query),
        )

    if intent == "chitchat":
        return RagAnswer(_canned("你好！我是客服 AI，很高興為您服務。"), [], 0.0, [], False)

    if intent == "handoff":
        return RagAnswer(
            _canned("已為您登記『客訴 · handoff』，24 小時內由專人聯繫。\n請提供聯絡電話。"),
            [], 0.0, [], True,
        )

    # FAQ branch: full RAG
    client = qdrant.get_client()
    with tracing.stage("search_faq"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=3, with_payload=True)
    cites = [CitationDetail(
        source_name=(p.payload or {}).get("source_name", "FAQ"), source_type="faq",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
