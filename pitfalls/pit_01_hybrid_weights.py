"""
坑 1 · Hybrid Search 的權重到底要 8/2、7/3、還是 6/4？   [Bucket 1: 取回的藝術]

現象 Symptom:   保險 FAQ bot 搜不到「投保退件怎麼辦」；調 dense 權重救 A 題弄壞 B 題。
成因 Root cause: 線性加權把 dense cosine (0-1) 與 sparse TF-IDF (無上限) 加起來 —
                「葡萄加蘋果」，任何 alpha 都對某些 query 不公平。
解法 Solution:  換成 Reciprocal Rank Fusion — 只看排名，不看分數。
"""
from __future__ import annotations


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def hybrid_score_linear(dense: float, sparse: float, alpha: float = 0.7) -> float:
    """
    Mix two incompatible-scale scores into one.
    dense ∈ [0, 1], sparse ∈ R₊ (任意大) — any alpha is unfair to some queries.
    """
    return alpha * dense + (1 - alpha) * sparse


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def rrf_merge(
    rankings: list[list[str]],
    k: int = 60,          # RRF paper constant (Cormack et al., 2009) — 不要亂改
) -> list[tuple[str, float]]:
    """
    Rank-based fusion: scale-invariant. Each retriever contributes 1 / (k + rank).

    Usage: dense 與 sparse 各自 prefetch top_k × 3，然後丟進 rrf_merge 合併。
    Every major vector DB (Qdrant, Weaviate, OpenSearch) ships this server-side.
    """
    scores: dict[str, float] = {}
    for ranked in rankings:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: -kv[1])
