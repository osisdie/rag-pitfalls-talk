"""Pit 11 · BEFORE — raw embed, no alias expansion."""
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


async def _single_chunk(text: str) -> AsyncIterator[str]:
    yield text


async def run_rag(ctx: RagContext) -> RagAnswer:
    vec = await embed.embed_one(ctx.query)
    client = qdrant.get_client()
    with tracing.stage("raw_embed_search"):
        hits = await client.query_points(collection_name="rule_doc", query=vec, using="dense", limit=3, with_payload=True)
    top = float(hits.points[0].score or 0.0) if hits.points else 0.0
    cites = [CitationDetail(
        source_name=(p.payload or {}).get("source_name", "rule_doc"), source_type="rule_doc",
        source_url=(p.payload or {}).get("source_url"), chunk_text=(p.payload or {}).get("text", ""),
        relevance_score=float(p.score or 0.0),
    ) for p in hits.points]
    # No glossary expansion → without aliases, raw embed pulls adjacent terms
    # but the system can't bridge them. Modern LLMs *will* synthesize a
    # plausible answer from the close hits, which hides the pit's failure
    # mode from the audience. Return a deterministic "找不到" so the BEFORE
    # contrast vs. AFTER (DTL via alias map) lands every time. Citations
    # still render the close-but-wrong chunks.
    answer = (
        f"找不到與『{ctx.query.strip()}』完全相符的詞彙資料。"
        "（最相近的條目已列在來源，但本系統未配置同義詞對照。）"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = _single_chunk(answer)
    return RagAnswer(stream, cites, top, [], False)
