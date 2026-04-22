"""
坑 8 · 清理老舊知識 — 不刪，系統會慢慢死   [Bucket 2: 時間的詛咒]

現象 Symptom:   系統跑 18 個月，Qdrant 從 10k points 長到 200k；p95 latency 80ms → 350ms；
                5 年前的舊公告偶爾贏上週新公告。
成因 Root cause: 沒有 retention policy。歷史資料只進不出，embedding 空間漂移加劇問題。
解法 Solution:  定期 sweep — 先軟刪過期 (archived=True)，再把久未點擊的搬到 cold collection。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from ._common import VectorDB

log = logging.getLogger(__name__)


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def ingest_loop_no_retention(vector_db: VectorDB) -> None:
    """
    Ingests forever, deletes never. The collection only grows — latency follows.
    By month 18 you are searching over mostly-dead data.
    """
    while True:
        for point in _fetch_new_points():
            vector_db.upsert(point)
        # ...never cleans up


def _fetch_new_points():
    raise NotImplementedError


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def retention_sweep(
    vector_db: VectorDB,
    cold_collection: VectorDB,
    today: date,
    click_counter: dict[str, int],
    stale_after_days: int = 730,
    cold_click_floor: int = 3,
) -> None:
    """
    Two-phase monthly sweep:
      Phase 1 — archive: set payload flag on entries past valid_until (soft delete).
      Phase 2 — cold-tier: move old + rarely-clicked entries to a cold collection
                (still reachable on explicit temporal queries, but out of the hot path).
    """
    # Phase 1 — archive expired
    expired = vector_db.query(filter={"valid_until": {"$lt": today}})
    vector_db.set_payload([e.id for e in expired], {"archived": True})

    # Phase 2 — cold-tier stale + unused
    cutoff = today - timedelta(days=stale_after_days)
    stale = vector_db.query(filter={"ingested_at": {"$lt": cutoff}})
    cold_candidates = [e for e in stale if click_counter.get(e.id, 0) < cold_click_floor]
    for entry in cold_candidates:
        cold_collection.upsert(entry)       # type: ignore[arg-type]
        vector_db.delete(ids=[entry.id])

    log.info("retention_done",
             extra={"archived": len(expired), "cold": len(cold_candidates)})
