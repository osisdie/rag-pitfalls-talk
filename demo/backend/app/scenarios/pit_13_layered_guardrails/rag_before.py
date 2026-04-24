"""Pit 13 · BEFORE — single-layer 'is_in_scope' classifier over-blocks."""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator
from app.core import llm, tracing
from app.models.schemas import CitationDetail

IN_SCOPE_TERMS = ("保險", "理賠", "保費", "保單", "投保")


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


async def _refuse():
    yield "很抱歉，您的問題超出範圍，本助理僅回答保險相關問題。\n"


async def run_rag(ctx: RagContext) -> RagAnswer:
    with tracing.stage("single_layer_scope_check"):
        in_scope = any(t in ctx.query for t in IN_SCOPE_TERMS)
    if not in_scope:
        return RagAnswer(_refuse(), [], 0.0, [], False)
    # real path omitted; this pit is only about the refuse flow
    return RagAnswer(llm.generate_stream(ctx.query), [], 0.0, [], False)
