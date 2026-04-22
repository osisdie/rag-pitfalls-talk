"""
坑 9 · Routing — 讓 query 找對自己的家   [Bucket 3: 讀懂用戶]

現象 Symptom:   用戶打「我想投訴」，系統跑完整 RAG pipeline 花 2 秒，只為回一句
                「請撥客服專線」。
成因 Root cause: 所有 query 走同一條 pipeline。但 chitchat / handoff / tool-call / time-
                sensitive 各自的最佳路徑完全不同。
解法 Solution:  輕量 intent classifier 與 embedding 平行跑，把分類 latency 吸進 embed 時間。
"""
from __future__ import annotations

import asyncio
from typing import Protocol

from ._common import embed


class TinyLLM(Protocol):
    async def classify(self, query: str) -> str: ...


CANNED_RESPONSES: dict[str, str] = {
    "chitchat": "您好～我是 FAQ 助理，有什麼問題想問嗎？",
}


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
async def handle_single_pipeline(query: str) -> str:
    """
    Every query — even pure chitchat — pays for embedding + retrieval + rerank + LLM.
    2 seconds of latency for "我想投訴" is not a product, it's an insult.
    """
    q_emb = embed(query)
    docs = await _search(q_emb)
    ranked = await _rerank(query, docs)
    return await _llm_generate(query, ranked)


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
async def handle_routed(query: str, tiny_llm: TinyLLM) -> str:
    """
    Parallel: classify + embed at the same time. Branch on intent — cheap paths
    finish before the expensive RAG pipeline would have even started.
    """
    intent_task = asyncio.create_task(tiny_llm.classify(query))
    embed_task = asyncio.create_task(asyncio.to_thread(embed, query))
    intent, q_emb = await asyncio.gather(intent_task, embed_task)

    if intent == "chitchat":
        return CANNED_RESPONSES[intent]            # ~50ms total
    if intent == "handoff":
        return _enqueue_human(query)               # hand to agent queue
    return await _run_rag_pipeline(query, q_emb)


# --- stubs (wire to your pipeline) ---------------------------------
async def _search(q_emb): raise NotImplementedError
async def _rerank(query, docs): raise NotImplementedError
async def _llm_generate(query, ranked): raise NotImplementedError
async def _run_rag_pipeline(query, q_emb): raise NotImplementedError
def _enqueue_human(query): raise NotImplementedError
