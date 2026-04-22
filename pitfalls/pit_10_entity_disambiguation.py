"""
坑 10 · 實體消歧 —「蘋果」是水果還是公司   [Bucket 3: 讀懂用戶]

現象 Symptom:   法律助理 bot 被問「張主任」，系統命中法律條款裡的「主任」角色 —
                但用戶要找的是事務所的員工張主任。
成因 Root cause: 短詞對 dense embedding 不利（語義分佈太散），但對 sparse 極強
                （字面 token 明確）。如果一律 dense，就壓住 sparse 的訊號。
解法 Solution:  短詞給 sparse-match bonus，但要有 dense floor 做安全網避免 one-sided 贏。
"""
from __future__ import annotations

from .pit_01_hybrid_weights import rrf_merge

# Dense score safety net — if dense 完全判定無關就不給 sparse bonus
DENSE_FLOOR: float = 0.2

# Short-query threshold — entity lookups tend to be ≤ 5 chars / tokens
SHORT_QUERY_LEN: int = 6


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def search_dense_only(query: str, dense_search) -> list:
    """
    Dense-only routing. Short entity queries land on semantic-cousin documents
    instead of the literal entity record.
    """
    return dense_search(query, limit=5)


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def hybrid_with_entity_bonus(
    query: str,
    dense_hits: list[tuple[str, float]],   # (doc_id, cosine_score)
    sparse_hits: list[str],                # doc_ids ordered by sparse rank
    bonus: float = 1.5,
) -> list[tuple[str, float]]:
    """
    1. Standard RRF merge.
    2. If query is short AND a doc is sparse-top-3 AND its dense score is at least
       DENSE_FLOOR (sanity check), boost its RRF score.
    """
    rrf = dict(rrf_merge([[d for d, _ in dense_hits], sparse_hits]))
    if len(query) >= SHORT_QUERY_LEN:
        return sorted(rrf.items(), key=lambda kv: -kv[1])

    sparse_top3 = set(sparse_hits[:3])
    dense_map = dict(dense_hits)
    for doc_id in list(rrf):
        if doc_id in sparse_top3 and dense_map.get(doc_id, 0.0) >= DENSE_FLOOR:
            rrf[doc_id] *= bonus
    return sorted(rrf.items(), key=lambda kv: -kv[1])
