"""
坑 12 · Handoff — 知道自己不知道   [Bucket 3: 讀懂用戶]

現象 Symptom:   律師看到 bot 回「根據類似案例，約賠 NT$500K-1.2M」— 實際信心只有 0.3，
                但系統還是信誓旦旦地回答。客戶把它當建議，律師氣炸。
成因 Root cause: 沒有 confidence gate。低信心 = 「別亂答」，但預設行為是「硬答」。
解法 Solution:  Threshold-sweep 選 F1-optimal 閾值；低於閾值一律不生成，進 handoff queue。
"""
from __future__ import annotations

from typing import Any, Protocol

from ._common import Doc

# 由 threshold sweep 在 golden set 上選出 F1-optimal — 常見在 0.55-0.65 之間
HANDOFF_THRESHOLD: float = 0.6


class LLM(Protocol):
    def generate(self, query: str, context: list[Doc]) -> str: ...


class Queue(Protocol):
    def enqueue(self, payload: dict[str, Any]) -> None: ...


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def generate_unguarded(query: str, docs: list[Doc], llm: LLM) -> dict:
    """
    Always answer, regardless of confidence. Confident-sounding hallucinations
    are worse than "I don't know" in legal / medical / financial domains.
    """
    return {
        "answer": llm.generate(query, context=docs),
        "confidence": docs[0].confidence if docs else 0.0,
    }


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def guarded_generate(
    query: str,
    docs: list[Doc],
    llm: LLM,
    queue: Queue,
    threshold: float = HANDOFF_THRESHOLD,
) -> dict:
    """
    Below threshold: refuse + enqueue to human queue. Above: answer as usual.
    Healthy handoff rate is 10-20%. <5% means threshold is too lenient; >40%
    means the system isn't useful enough.
    """
    top_conf = docs[0].confidence if docs else 0.0
    if top_conf < threshold:
        queue.enqueue({
            "query": query,
            "reason": "low_confidence",
            "top_conf": top_conf,
        })
        return {
            "answer": "這個問題我沒把握，已轉交人工回覆。",
            "handoff": True,
            "confidence": top_conf,
        }
    return {
        "answer": llm.generate(query, context=docs),
        "handoff": False,
        "confidence": top_conf,
    }
