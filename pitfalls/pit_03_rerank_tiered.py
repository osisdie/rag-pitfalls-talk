"""
坑 3 · Rerank 用 Cross-Encoder 還是 Dense Re-score？   [Bucket 1: 取回的藝術]

現象 Symptom:   掛上 Cohere / BGE-Reranker，p95 latency 從 800ms 飆到 1.3s。
成因 Root cause: Cross-encoder 對每個 (query, doc) pair 做 full attention，Top-20 候選 =
                20 次 forward pass，硬成本 200-500ms。
解法 Solution:  兩階段 rerank — dense 粗排先削到 Top-K，只對 Top-K 花 cross-encoder 預算。
"""
from __future__ import annotations

from typing import Protocol

from ._common import Doc, cosine_similarity


class DenseModel(Protocol):
    def encode(self, text: str) -> list[float]: ...


class CrossEncoder(Protocol):
    def predict(self, query: str, text: str) -> float: ...


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def rerank_naive(query: str, candidates: list[Doc], ce: CrossEncoder) -> list[Doc]:
    """
    Run cross-encoder on every candidate — 20x full-attention forward pass,
    200-500ms even on GPU. Latency explodes as candidate pool grows.
    """
    scored = [(d, ce.predict(query, d.text)) for d in candidates]
    return [d for d, _ in sorted(scored, key=lambda x: -x[1])]


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def rerank_tiered(
    query: str,
    candidates: list[Doc],
    dense: DenseModel,
    ce: CrossEncoder,
    k_ce: int = 5,                         # 只精排前 K 名 / only top-K get cross-encoder
) -> list[Doc]:
    """
    Stage 1: cheap dense re-score (vectorized, < 10ms for 20 candidates).
    Stage 2: expensive cross-encoder, but only on survivors.

    Typical result: ~85% of cross-encoder quality at ~10% of its latency.
    """
    q_emb = dense.encode(query)
    coarse = sorted(candidates, key=lambda d: -cosine_similarity(q_emb, d.embedding))
    survivors = coarse[:k_ce]
    scored = [(d, ce.predict(query, d.text)) for d in survivors]
    return [d for d, _ in sorted(scored, key=lambda x: -x[1])]
