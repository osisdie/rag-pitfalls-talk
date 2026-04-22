"""
坑 17 · 聊天紀錄的 hot / cold / compressed 三層   [Bucket 5: 基礎設施]

現象 Symptom:   30 輪對話後 context overflow；中段被稀釋（lost-in-the-middle），LLM 忘記
                第 3 輪的關鍵事實。
成因 Root cause: 把全部歷史 verbatim 塞進 prompt — 長度線性成長，中段 attention 衰減。
解法 Solution:  三層 memory — hot (verbatim) / cold (LLM summary) / older (vector-retrieved)。
"""
from __future__ import annotations

from typing import Protocol

from ._common import Turn, embed


class LLM(Protocol):
    def summarize(self, turns: list[Turn]) -> str: ...


class MemoryStore(Protocol):
    def search(self, vector: list[float], limit: int = 3) -> list[Turn]: ...


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def assemble_context_verbatim(history: list[Turn], current: str) -> str:
    """
    Dump everything. 30 turns × 200 tokens ≈ 6000 tokens; middle turns get
    ignored by attention; cost climbs linearly with session length.
    """
    return "\n".join(f"{t.role}: {t.text}" for t in history) + f"\nuser: {current}"


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def assemble_context_tiered(
    turns: list[Turn],
    current: str,
    llm: LLM,
    memory_store: MemoryStore,
) -> dict:
    """
    Hot:   last 5 turns verbatim — recency matters, avoid summarization loss.
    Cold:  turns 6-20, LLM-compressed once then cached.
    Older: vector-retrieved snippets — only pull what's relevant to *this* turn.

    Keeps prompt length flat regardless of session depth, preserves signal from
    very long conversations.
    """
    hot = turns[-5:]
    cold = turns[-20:-5]
    older = turns[:-20]

    cold_summary = llm.summarize(cold) if cold else ""
    older_hits: list[Turn] = []
    if older:
        q_vec = embed(current)
        older_hits = memory_store.search(q_vec, limit=3)

    return {
        "hot": [{"role": t.role, "content": t.text} for t in hot],
        "cold_summary": cold_summary,
        "older_snippets": [h.text for h in older_hits],
    }
