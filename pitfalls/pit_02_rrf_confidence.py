"""
坑 2 · RRF 的 score 不是「信心」   [Bucket 1: 取回的藝術]

現象 Symptom:   系統回「合約有效期到 2030 年」，RRF 信心 0.97 — 但來源根本不是合約本文。
成因 Root cause: RRF 分數只是排名函數，不是語義相似度。dense 與 sparse 都把 A 排第 1
                即使 A 的真實 cosine 只有 0.3，RRF 也會給超高分。
解法 Solution:  Two-stage retrieval — RRF 粗排出候選，dense cosine re-score 當 confidence。
"""
from __future__ import annotations

from ._common import Doc, cosine_similarity


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def answer_from_rrf_only(rrf_top: list[tuple[str, float]],
                         rrf_threshold: float = 0.6) -> str | None:
    """
    Apply confidence threshold on RRF score itself.
    Looks like a 0-1 number but it's just a rank artifact — hallucinations slip through.
    """
    doc_id, rrf_score = rrf_top[0]
    if rrf_score >= rrf_threshold:
        return f"answer for {doc_id}"
    return None


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def calibrated_retrieve(
    query_emb: list[float],
    rrf_candidates: list[Doc],
    threshold: float = 0.6,
) -> tuple[Doc | None, float]:
    """
    Re-score every RRF survivor with true cosine similarity, then threshold
    on the *calibrated* score. This is what downstream handoff logic should use.
    """
    rescored = [(d, cosine_similarity(query_emb, d.embedding)) for d in rrf_candidates]
    rescored.sort(key=lambda x: -x[1])
    best_doc, conf = rescored[0]
    return (best_doc, conf) if conf >= threshold else (None, conf)
