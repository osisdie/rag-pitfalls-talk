"""Pit 15 · BEFORE — front-end renders a hardcoded bubble, bypasses RAG.

FAQ updated → stale bubble ships to users until next front-end deploy.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator
from app.models.schemas import CitationDetail

HARDCODED_BUBBLE = {
    "營業時間": "週一至週日 10:00-21:00 (hardcoded · stale since 2023-04)",
}


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


async def _canned(text: str):
    yield text + "\n"


async def run_rag(ctx: RagContext) -> RagAnswer:
    for key, reply in HARDCODED_BUBBLE.items():
        if key in ctx.query:
            return RagAnswer(_canned(f"[hardcoded bubble] {reply}"), [], 0.99, [], False)
    return RagAnswer(_canned("[hardcoded bubble] 請洽客服"), [], 0.0, [], False)
