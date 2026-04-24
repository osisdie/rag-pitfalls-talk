"""Pit 20 · BEFORE — manual vibe check.

When the speaker asks "run golden benchmark", the naive implementation
runs a handful of queries and prints "looks ok to me". No structured
metrics, no regression gate, no aggregate score. This is what your
product manager demos right before shipping to production.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

from app.core import llm, tracing
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


async def _vibe_stream() -> AsyncIterator[str]:
    # Streaming fake "vibe check" output. The speaker reads this on stage
    # and groans — then clicks Apply Fix to see the before/after comparison.
    lines = [
        "⚡ Manual vibe check · 手動感覺測試\n\n",
        "Q1: 客服電話？ → 0800-123-456  ✓ looks good\n",
        "Q2: 退款時限？ → 7 天  ✓ looks good\n",
        "Q3: VIP 門檻？ → 10,000  ✓ looks good\n\n",
        "Summary: **vibe = good** 👍\n",
        "Shipping it. (Confidence? haha trust me bro)\n",
    ]
    for line in lines:
        yield line


async def run_rag(ctx: RagContext) -> RagAnswer:
    with tracing.stage("vibe_check"):
        pass  # no real work

    # Bypass the LLM entirely — the "before" state is exactly the absence
    # of any structured evaluation.
    return RagAnswer(
        answer_stream=_vibe_stream(),
        citations=[],
        confidence=0.99,  # fake high confidence — the whole teaching point
        thumbnails=[],
        handoff=False,
    )
