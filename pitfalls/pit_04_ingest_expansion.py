"""
坑 4 · Rephrase — Runtime HyDE 還是 Ingest-time Expansion？   [Bucket 1: 取回的藝術]

現象 Symptom:   一筆 FAQ「我被告了怎麼辦」搜不到，因為用戶問「收到傳票該怎麼辦」。
成因 Root cause: Canonical FAQ 問法與 verbatim user query 之間有 surface-form gap；
                embedding 對同義句的 robustness 不是無限的。
解法 Solution:  計算前移 — ingestion 階段就讓 LLM 生成 N 個同義變體並一起入庫。
"""
from __future__ import annotations

from typing import Protocol

from ._common import FAQ, Point, VectorDB, embed, stable_id


class LLM(Protocol):
    def generate_variants(self, question: str, n: int) -> list[str]: ...


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
async def search_with_runtime_hyde(
    query: str,
    llm: LLM,
    vector_db: VectorDB,
) -> list:
    """
    Generate query variants on every request. Pays LLM cost + 500-1500ms latency
    per user question — fine on a demo, crippling in production.
    """
    variants = await llm.generate_variants(query, n=3)  # type: ignore[misc]
    hits = []
    for v in variants:
        hits.extend(vector_db.search(embed(v), limit=10))
    return hits


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def expand_and_index_faq(
    faq: FAQ,
    llm: LLM,
    vector_db: VectorDB,
    n_variants: int = 3,
) -> None:
    """
    Offline: each FAQ → original + N 個同義問法，一起 embedding 入庫。
    100 FAQs → ~400 points. Runtime 端只做一次 vector search。
    """
    variants = llm.generate_variants(faq.question, n=n_variants)
    for text in [faq.question, *variants]:
        vector_db.upsert(Point(
            id=stable_id(faq.id, text),
            vector=embed(text),
            payload={
                "canonical_id": faq.id,              # 連回原 FAQ / link to origin
                "answer": faq.answer,
                "is_variant": text != faq.question,
            },
        ))
