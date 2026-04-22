"""
坑 7 · 新舊知識的版本管理   [Bucket 2: 時間的詛咒]

現象 Symptom:   保險公司 3 月發新理賠規則；舊規則沒被刪，系統同時回「5 到 7 天」
                (新=5、舊=7，兩邊都對但組合起來是錯的)。
成因 Root cause: Naive ingestion 只做 upsert，不做 orphan delete。舊 chunk 永遠留在 DB。
解法 Solution:  Content-hash diff + filter-based orphan delete + 爬蟲失敗的 shrink guard。
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from ._common import Point, VectorDB, embed, stable_id

log = logging.getLogger(__name__)


@dataclass
class Doc:
    url: str
    text: str


def _split(text: str) -> list[str]:
    """Your chunker here — semantic / sliding window / etc."""
    raise NotImplementedError


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def ingest_naive(doc: Doc, vector_db: VectorDB) -> None:
    """
    Upsert only. Every re-ingest adds new chunks; old ones stick around forever.
    Retrieval happily returns both versions and the LLM blends them into lies.
    """
    for chunk in _split(doc.text):
        vector_db.upsert(Point(
            id=stable_id("rand", chunk),     # non-deterministic id — 更糟
            vector=embed(chunk),
            payload={"source_url": doc.url},
        ))


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def ingest_with_versioning(doc: Doc, vector_db: VectorDB) -> None:
    """
    1. Compute content_hash — if unchanged, skip entirely (saves embedding $$).
    2. Shrink guard — reject obviously-truncated scrapes (likely scraper fail).
    3. Delete orphans by source_url, then upsert fresh chunks.
    """
    new_hash = hashlib.sha256(doc.text.encode("utf-8")).hexdigest()
    prev = vector_db.fetch_payload(filter={"source_url": doc.url}, limit=1)

    if prev and prev.get("content_hash") == new_hash:
        return  # unchanged

    # Suspicious shrink — bail out instead of overwriting rich old data with nothing.
    if prev and len(doc.text) < 50 and len(prev.get("text", "")) > 200:
        log.warning("suspicious_shrink", extra={"url": doc.url})
        return

    vector_db.delete(filter={"source_url": doc.url})
    for chunk in _split(doc.text):
        vector_db.upsert(Point(
            id=stable_id(doc.url, chunk),
            vector=embed(chunk),
            payload={"source_url": doc.url, "content_hash": new_hash, "text": chunk},
        ))
