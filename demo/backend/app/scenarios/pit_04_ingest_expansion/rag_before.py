"""Pit 4 · BEFORE — runtime HyDE: LLM rewrites the query on every request."""
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


async def _runtime_hyde(q: str) -> str:
    # LLM call inside the request path — adds latency + $ + failure modes.
    with tracing.stage("runtime_hyde", model=llm.get_config().model):
        return await llm.generate(
            f"將以下使用者問題改寫為 1-2 個 FAQ 標題樣式的表述，只回傳改寫文字、不用解釋:\n{q}",
            temperature=0.0,
        )


async def _retrieve(query: str):
    expanded = await _runtime_hyde(query)
    vec = await embed.embed_one(f"{query}\n{expanded}")
    client = qdrant.get_client()
    with tracing.stage("search_dense"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=3, with_payload=True)
    return [CitationDetail(
        source_name=(p.payload or {}).get("source_name", "FAQ"), source_type="faq",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "請在回答開頭標註『⚠️ runtime HyDE · 每次請求多一次 LLM call』。\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
