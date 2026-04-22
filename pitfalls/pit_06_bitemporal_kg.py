"""
坑 6 · Graphiti / Temporal Knowledge Graph — 什麼時候該上？   [Bucket 2: 時間的詛咒]

現象 Symptom:   客戶問「2 年前簽約當時適用的規則」，系統永遠回最新版。
成因 Root cause: Vector DB 是 timeless 的 — 每個 chunk 只有「存在 / 不存在」，
                無有效期概念。但合約、法規、稅制本質上就是時序事實。
解法 Solution:  Bi-temporal KG — 每個 edge 帶 valid_at / invalid_at，查詢時以 as_of 過濾。
"""
from __future__ import annotations

from datetime import date
from typing import Protocol

from ._common import VectorDB, embed


class Graph(Protocol):
    def run(self, cypher: str, **params): ...


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def lookup_rule_timeless(topic: str, vector_db: VectorDB) -> str:
    """
    Vector DB has no notion of fact validity — returns whatever has highest
    similarity right now, usually the newest version.
    """
    hits = vector_db.search(embed(topic), limit=1)
    return hits[0].text


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def lookup_rule_at(graph: Graph, topic: str, as_of: date) -> list[dict]:
    """
    Bi-temporal query:
      valid_at:   fact becomes business-valid from this date
      invalid_at: fact expires (NULL = still valid today)

    Neo4j + Graphiti ships this pattern; Zep's paper (2024) is the canonical ref.
    """
    cypher = """
        MATCH (t:Topic {name: $topic})-[r:GOVERNED_BY]->(rule:Rule)
        WHERE r.valid_at <= $as_of
          AND (r.invalid_at IS NULL OR r.invalid_at > $as_of)
        RETURN rule.text AS text,
               r.valid_at AS valid_from,
               r.invalid_at AS valid_to
        ORDER BY r.valid_at DESC
    """
    return graph.run(cypher, topic=topic, as_of=as_of).data()
