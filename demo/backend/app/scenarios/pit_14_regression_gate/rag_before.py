"""Pit 14 · BEFORE — 'I tweaked magic numbers in Cursor, looks good'."""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator
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


async def _vibe():
    lines = [
        "🛠 vibe-coded params:\n",
        "  HYBRID_ALPHA = 0.9   # magic number: 那題之前壞了, 調高一點\n",
        "  RRF_K = 72           # magic number: 聽說 Reddit 說 60 太低\n",
        "  RERANK_FLOOR = 0.55  # magic number: 看著順眼\n\n",
        "Ship it! (no tests, no regression gate)\n",
    ]
    for l in lines:
        yield l


async def run_rag(ctx: RagContext) -> RagAnswer:
    return RagAnswer(_vibe(), [], 0.99, [], False)
