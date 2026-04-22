"""
坑 20 · Evaluation 框架 — 沒有 regression，就沒有進步   [Bucket 6: 驗證之神]

現象 Symptom:   修好坑 1 看似 OK，但坑 2 悄悄壞了。沒有 regression baseline，任何
                「修好了嗎」的判斷都是信仰，不是事實。
成因 Root cause: 人工測 20 題 ≠ systematic evaluation。測試集不穩、結果不可比較、
                每次修改沒有 delta。
解法 Solution:  Golden Set + RAGAS 自動化 + Threshold sweep + CI regression gate。
                這是讓其他 19 個解法真正可信的「元」解法。

Requires: pip install ragas datasets
"""
from __future__ import annotations

import sys
from typing import Protocol

from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from ._common import Query


class RAGPipeline(Protocol):
    def __call__(self, question: str) -> "RAGResult": ...


class RAGResult(Protocol):
    answer: str
    contexts: list

# 四個指標 / four floors — 任一掉 >3% vs. baseline 視為 regression
GATES: dict[str, float] = {
    "faithfulness":      0.85,   # 答案有無根據 / grounded in retrieved context
    "answer_relevancy":  0.80,   # 答案是否切題 / relevant to the question
    "context_precision": 0.70,   # 取回的 context 有多精準
    "context_recall":    0.80,   # 該取回的 context 是否都取到
}


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def manual_vibe_check(run_rag: RAGPipeline) -> None:
    """
    'Looks fine' is not evaluation. Three weeks later someone ships a change
    that breaks a case you eyeballed-and-forgot a month ago.
    """
    print(run_rag("最近申報期限？"))
    print(run_rag("理賠要幾天？"))
    print(run_rag("我要投訴"))


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def run_golden_benchmark(
    golden_set: list[Query],
    run_rag: RAGPipeline,
) -> dict[str, float]:
    """Build RAGAS samples from each golden query, run all four metrics."""
    samples = []
    for q in golden_set:
        result = run_rag(q.text)
        samples.append({
            "question":     q.text,
            "answer":       result.answer,
            "contexts":     [c.text for c in result.contexts],
            "ground_truth": q.expected_answer,
        })
    scores = evaluate(
        samples,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    return {m: float(scores[m]) for m in GATES}


def ci_gate(scores: dict[str, float]) -> int:
    """Exit code for CI — 0 = merge OK, 1 = block merge."""
    fail = False
    for metric, floor in GATES.items():
        if scores[metric] < floor:
            print(f"FAIL {metric}: {scores[metric]:.2f} < {floor}")
            fail = True
    return 1 if fail else 0


if __name__ == "__main__":
    # Wire these to your actual benchmark in CI:
    #   scores = run_golden_benchmark(load_golden_set(), your_pipeline)
    #   sys.exit(ci_gate(scores))
    sys.exit(0)
