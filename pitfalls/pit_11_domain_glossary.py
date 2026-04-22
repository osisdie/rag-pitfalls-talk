"""
坑 11 · 行話（Domain Glossary）— 系統要會「說行話」   [Bucket 3: 讀懂用戶]

現象 Symptom:   會計領域「遞延負債」「遞延所得稅負債」「deferred liability」「DTL」被當成
                完全不同的詞。
成因 Root cause: Embedding 對同義詞、跨語、abbreviation 的 robustness 有限；沒有 canonical
                form 就無法 reuse 同一 concept 的知識。
解法 Solution:  Canonical-form + aliases 字典，在查詢端展開多變體，再用 RRF 合併結果。
"""
from __future__ import annotations

from ._common import VectorDB, embed
from .pit_01_hybrid_weights import rrf_merge


GLOSSARY: list[dict] = [
    {
        "canonical": "遞延所得稅負債",
        "aliases": ["遞延負債", "DTL", "deferred liability", "deferred tax liability"],
    },
    {
        "canonical": "應收帳款",
        "aliases": ["AR", "accounts receivable"],
    },
    # ... domain experts add terms here
]


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def retrieve_no_glossary(query: str, vector_db: VectorDB, limit: int = 10) -> list:
    """
    Each synonym of the same concept becomes a distinct vector. The user who
    writes "DTL" never finds the document written with full Chinese canonical form.
    """
    return vector_db.search(embed(query), limit=limit)


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def expand_with_glossary(query: str) -> list[str]:
    """Produce every canonical-form rewrite of the query."""
    variants: set[str] = {query}
    for term in GLOSSARY:
        for alias in term["aliases"]:
            if alias in query:
                variants.add(query.replace(alias, term["canonical"]))
    return list(variants)


def glossary_retrieve(query: str, vector_db: VectorDB, limit: int = 10) -> list[str]:
    """
    Multi-query retrieval: search once per variant, fuse with RRF.
    The canonical form tends to reach the authoritative document even when the
    original query used an abbreviation or cross-language term.
    """
    hit_lists = [
        [h.id for h in vector_db.search(embed(v), limit=limit)]
        for v in expand_with_glossary(query)
    ]
    return [doc_id for doc_id, _ in rrf_merge(hit_lists)][:limit]
