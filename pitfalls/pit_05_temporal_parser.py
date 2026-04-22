"""
坑 5 · 相對時間解析 —「最近的申報期限」是多久？   [Bucket 2: 時間的詛咒]

現象 Symptom:   會計 bot 被問「最近的申報期限」，系統回「請參考 2019 年公告」。
成因 Root cause: 「最近」被當普通 token 丟進 embedding；2019 公告 TF-IDF 剛好高，
                無 temporal filter → 歷史文件永遠贏最新文件的 surface match。
解法 Solution:  中文相對時間專屬 pattern parser + progressive 4-tier fallback。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from ._common import Doc, VectorDB, embed

log = logging.getLogger(__name__)

WINDOWS_DAYS: dict[str, int] = {
    "今天": 1, "昨天": 1,
    "最近": 30, "近期": 30,
    "上週": 7, "本週": 7, "下週": 7,
    "上個月": 30, "本月": 30,
    "季末": 90, "年底": 365,
}


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def search_no_temporal(query: str, vector_db: VectorDB) -> list[Doc]:
    """
    Feed the raw query into embedding. 「最近」dissolves into tokens and old
    docs with high TF-IDF happily outrank recent ones.
    """
    return vector_db.search(embed(query), limit=10)


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def temporal_search(
    query: str,
    vector_db: VectorDB,
    today: date,
    limit: int = 10,
) -> list[Doc]:
    """
    Pattern match → primary window, then progressive fallback so the caller
    always learns *which* window the hit came from (observability ≠ silent drop).
    """
    primary = next((d for k, d in WINDOWS_DAYS.items() if k in query), None)
    for days in (primary, 90, 365, None):             # 4-tier fallback
        flt = None if days is None else {"date": {"$gte": today - timedelta(days=days)}}
        hits = vector_db.search(embed(query), filter=flt, limit=limit)
        if hits:
            log.info("temporal_hit", extra={"window_days": days, "n": len(hits)})
            return hits
    return []
