"""
坑 16 · Caching 的三層不同性格   [Bucket 5: 基礎設施]

現象 Symptom:   Response cache hit rate 10% 感覺沒用；結果發現 embedding 也在 1 小時後
                失效（但 embedding 根本不該過期）。
成因 Root cause: 三種不同性格的資料用同一把 key + 同一個 TTL。Response 該 bust 時牽連
                embedding，embedding 該常駐時被 response TTL 拉下水。
解法 Solution:  Response / Embedding / Image — 三層各自 TTL、各自 invalidation 策略。
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import Protocol


class Redis(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def setex(self, key: str, ttl: int, value: str) -> None: ...
    def scan_iter(self, pattern: str): ...
    def delete(self, key: str) -> None: ...


class EmbedModel(Protocol):
    def encode(self, text: str) -> list[float]: ...


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def cache_everything(redis: Redis, query: str, payload: dict) -> None:
    """
    One key, one TTL, everything inside. When response expires, so does the
    embedding you bundled in — and now your p95 spikes every hour.
    """
    redis.setex(f"cache:{query}", 3600, json.dumps(payload))


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
# Layer 1 — embedding: process-lifetime, 100% hit on repeat queries
@lru_cache(maxsize=10_000)
def cached_embed(text: str, model: EmbedModel) -> tuple[float, ...]:
    """Embedding of the same string never changes within a process lifetime."""
    return tuple(model.encode(text))


# Layer 2 — response: Redis with explicit bust on knowledge update
def cached_response(
    query: str,
    tenant_id: str,
    redis: Redis,
    run_pipeline,
    ttl: int = 86_400,
) -> dict:
    key = f"resp:{tenant_id}:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
    cached = redis.get(key)
    if cached is not None:
        return json.loads(cached)
    result = run_pipeline(query)
    redis.setex(key, ttl, json.dumps(result))
    return result


def bust_responses(tenant_id: str, redis: Redis) -> None:
    """Called whenever the knowledge base updates."""
    for key in redis.scan_iter(f"resp:{tenant_id}:*"):
        redis.delete(key)


# Layer 3 — image: offload to a CDN (see pit 19 for materialization).
# CDN gives ~90%+ hit rate; your app never sees image reads.
