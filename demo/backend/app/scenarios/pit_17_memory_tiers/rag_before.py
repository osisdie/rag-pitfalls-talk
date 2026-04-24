"""Pit 17 · BEFORE — pass only last N turns literally; older context lost."""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator

from app.core import llm, tracing
from app.models.schemas import CitationDetail

TRUNCATE_TO = 3  # too few — deliberately forgets


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
    with tracing.stage("truncate_to_last_N", n=TRUNCATE_TO, forgot=max(0, len(ctx.history) - TRUNCATE_TO)):
        recent = ctx.history[-TRUNCATE_TO:]
    turns = "\n".join(f"{t['role']}: {t['content']}" for t in recent)
    prompt = (
        "若 context 未提供某項資料，明確回答『資料未提供』不要猜測。\n\n"
        f"Recent turns:\n{turns}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, [], 0.0, [], False)
