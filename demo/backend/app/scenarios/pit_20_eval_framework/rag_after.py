"""Pit 20 · AFTER — golden-set benchmark + CI gate.

Runs the small golden set in `seed/golden_set.json` through the active
retrieval path, computes approximations of the four RAGAS metrics, and
emits a pass/fail CI gate. The streaming output is the summary bar chart;
citations carry per-question diagnostics.

For pedagogy we compute metrics with simple heuristics (keyword presence,
source match) rather than full RAGAS — the shape matches the real thing,
and the teaching is about the *framework*, not the specific math.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from app.config import get_settings
from app.core import embed, qdrant, tracing
from app.models.schemas import CitationDetail

# Threshold gates — sourced from the talk's evaluation discussion.
GATES = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_precision": 0.70,
    "context_recall": 0.80,
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


def _golden_path() -> Path:
    s = get_settings()
    return s.scenarios_root / "pit_20_eval_framework" / "seed" / "golden_set.json"


async def _run_one(q: str, expected_substr: str, expected_source: str) -> dict:
    vec = await embed.embed_one(q)
    client = qdrant.get_client()
    hits = await client.query_points(
        collection_name="faq", query=vec, using="dense", limit=3, with_payload=True
    )
    points = hits.points
    ctx_texts = [(p.payload or {}).get("text", "") for p in points]
    ctx_sources = [(p.payload or {}).get("source_name", "") for p in points]
    joined_ctx = " ".join(ctx_texts)

    context_precision = (
        1.0 if expected_source in ctx_sources and ctx_sources and ctx_sources[0] == expected_source
        else 0.5 if expected_source in ctx_sources
        else 0.0
    )
    context_recall = 1.0 if expected_substr in joined_ctx else 0.0
    faithfulness = context_recall  # conservative proxy: if the fact isn't in context, faithfulness = 0
    answer_relevancy = 1.0 if context_recall else 0.4  # if context has it, assume LLM restates it

    return {
        "question": q,
        "expected_substr": expected_substr,
        "context_precision": context_precision,
        "context_recall": context_recall,
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "top_source": ctx_sources[0] if ctx_sources else None,
    }


def _bars(scores: dict[str, float]) -> str:
    lines = []
    for name, val in scores.items():
        gate = GATES[name]
        ok = val >= gate
        filled = int(val * 20)
        bar = "█" * filled + "░" * (20 - filled)
        flag = "✅" if ok else "❌"
        lines.append(f"  {flag} {name:18} {bar} {val:.2f}  (gate {gate})")
    return "\n".join(lines)


async def _bench_stream(trigger: str) -> AsyncIterator[str]:
    with tracing.stage("load_golden"):
        golden = json.loads(_golden_path().read_text(encoding="utf-8"))

    yield "🔬 Golden-set benchmark · running…\n\n"

    per_q: list[dict] = []
    with tracing.stage("run_golden", n=len(golden)):
        for item in golden:
            result = await _run_one(
                item["question"],
                item["expected_substr"],
                item["expected_source_name"],
            )
            per_q.append(result)
            flag = "✓" if result["context_recall"] >= 1.0 else "✗"
            yield f"  {flag}  {item['question']}  →  top: {result['top_source']}\n"

    def avg(k: str) -> float:
        return sum(r[k] for r in per_q) / max(1, len(per_q))

    scores = {
        "faithfulness": avg("faithfulness"),
        "answer_relevancy": avg("answer_relevancy"),
        "context_precision": avg("context_precision"),
        "context_recall": avg("context_recall"),
    }

    yield "\n📊 Aggregate metrics (approx. RAGAS shape):\n\n"
    yield _bars(scores) + "\n\n"

    gate_ok = all(scores[k] >= GATES[k] for k in GATES)
    if gate_ok:
        yield "🚦 **CI gate: PASS** — safe to deploy.\n"
    else:
        yield "🚦 **CI gate: FAIL** — block deployment, investigate failing metrics above.\n"


async def run_rag(ctx: RagContext) -> RagAnswer:
    # Any chat turn against the "after" runs the benchmark.
    return RagAnswer(
        answer_stream=_bench_stream(ctx.query),
        citations=[],
        confidence=0.0,  # meta scenario — no per-answer confidence
        thumbnails=[],
        handoff=False,
    )
