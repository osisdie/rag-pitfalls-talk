"""Pit 8 · BEFORE — archived docs still searchable, noisy results."""
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
    with tracing.stage("search_no_retention"):
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=3, with_payload=True)
    return [CitationDetail(
        source_name=(p.payload or {}).get("source_name", "FAQ"), source_type="faq",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]


async def _single_chunk(text: str) -> AsyncIterator[str]:
    yield text


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _retrieve(ctx.query)
    # No retention sweep → archived 2020 docs stay searchable and the LLM
    # will recite them. Make BEFORE deterministic so the audience sees the
    # canonical "outdated 居家辦公 公告" leak every time, then AFTER (with
    # retention sweep) cleanly returns "已歸檔" instead.
    answer = (
        "根據 FAQ：2020 年防疫公告指出居家辦公申請流程請至人資系統提交，"
        "並提及 2020 員工旅遊補助。"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = _single_chunk(answer)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
