"""Pit 14 · AFTER — compare candidate params against baseline on golden set.

Baseline RAGAS-shaped metrics are hard-coded (as if stored in CI). New
params run the golden set through retrieval, compute metric delta, fail
the gate if any metric drops > 3%.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator

from app.core import embed, qdrant, tracing
from app.models.schemas import CitationDetail

TOLERANCE = 0.03

BASELINE = {
    "faithfulness": 0.91,
    "answer_relevancy": 0.86,
    "context_precision": 0.79,
    "context_recall": 0.88,
}

GOLDEN = [
    ("怎麼試算保費", "保費試算"),
    ("想要退保", "退保流程"),
    ("要保人變更怎麼辦", "契約變更"),
]


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


async def _candidate_scores() -> dict[str, float]:
    client = qdrant.get_client()
    hits_top_correct = 0
    for q, expect in GOLDEN:
        vec = await embed.embed_one(q)
        hits = await client.query_points(collection_name="faq", query=vec, using="dense", limit=1, with_payload=True)
        if hits.points and (hits.points[0].payload or {}).get("source_name") == expect:
            hits_top_correct += 1
    recall = hits_top_correct / len(GOLDEN)
    # Approximate the four metrics from one observable (recall-at-1). In
    # production these come from ragas.evaluate over a real golden set.
    return {
        "faithfulness": recall * 0.95,
        "answer_relevancy": recall * 0.90,
        "context_precision": recall,
        "context_recall": recall,
    }


async def _stream() -> AsyncIterator[str]:
    with tracing.stage("score_candidate"):
        cand = await _candidate_scores()
    yield "🧪 candidate vs baseline\n\n"
    fail = False
    for name, base in BASELINE.items():
        c = cand[name]
        delta = c - base
        flag = "✅" if delta >= -TOLERANCE else "❌"
        if delta < -TOLERANCE:
            fail = True
        yield f"  {flag} {name:18} base {base:.2f}  cand {c:.2f}  delta {delta:+.2f}\n"
    yield "\n"
    if fail:
        yield "🚫 regression-gate FAIL — block merge\n"
    else:
        yield "✅ regression-gate PASS — merge allowed\n"


async def run_rag(ctx: RagContext) -> RagAnswer:
    return RagAnswer(_stream(), [], 0.0, [], False)
