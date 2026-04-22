"""
坑 15 · 預設聊天泡泡要快取「查詢」，不是「答案」   [Bucket 4: 護欄的拿捏]

現象 Symptom:   前端泡泡寫死「營業時間：週一到週五 9-18」；公司改成 9-19，要改 code +
                redeploy 前端才能反映。
成因 Root cause: 把答案當 config 放前端。任何 FAQ 內容更動都變成前端部署工作。
解法 Solution:  快取 query，讓 RAG pipeline 依 TTL 自動刷新答案；FAQ 改版只要 bust cache。
"""
from __future__ import annotations

import hashlib
import json
from typing import Protocol


class Redis(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def setex(self, key: str, ttl: int, value: str) -> None: ...
    def scan_iter(self, pattern: str): ...
    def delete(self, key: str) -> None: ...


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
DEFAULT_BUBBLES = [
    {"q": "營業時間？", "a": "週一到週五 9:00-18:00"},
    {"q": "退款政策？", "a": "七天內無條件退款"},
]
"""
Answer hardcoded in the frontend. Every FAQ tweak becomes a frontend redeploy.
On-call engineer ends up apologizing to marketing for one-word changes.
"""


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def _key(tenant_id: str, query: str, version: str = "v2") -> str:
    q_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
    return f"rag:{version}:{tenant_id}:{q_hash}"


def cached_rag(
    query: str,
    tenant_id: str,
    redis: Redis,
    run_rag_pipeline,
    ttl_seconds: int = 86_400,     # 24h default
) -> dict:
    """
    Cache keyed on (tenant, query_hash). Answer regenerates when TTL expires
    OR when bust_cache is called — no frontend changes needed.
    """
    key = _key(tenant_id, query)
    cached = redis.get(key)
    if cached is not None:
        return json.loads(cached)
    answer = run_rag_pipeline(query)
    redis.setex(key, ttl_seconds, json.dumps(answer))
    return answer


def bust_cache(tenant_id: str, redis: Redis, version: str = "v2") -> None:
    """Call this on FAQ updates — next user click refreshes the answer."""
    for key in redis.scan_iter(f"rag:{version}:{tenant_id}:*"):
        redis.delete(key)
