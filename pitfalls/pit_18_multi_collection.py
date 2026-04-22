"""
坑 18 · 資料分類不只是「web / file / db」   [Bucket 5: 基礎設施]

現象 Symptom:   Collection 依來源切分（web_docs / file_docs / db_docs），retrieval 時每次
                都搜全部，慢 + 精度低。
成因 Root cause: 「來源」不決定 retrieval 行為；真正該切分的是「檢索本質」—— FAQ、規則、
                時序資料、實體目錄、商品各需要不同 chunker / reranker / filter。
解法 Solution:  依 retrieval nature 建多 collection，每個 collection 配專屬 pipeline。
"""
from __future__ import annotations

from ._common import Doc

# Each collection gets its own chunking strategy, reranker, and filter schema.
COLLECTIONS: dict[str, dict] = {
    "faq":      {"chunker": "qa_pair",  "reranker": "dense"},
    "rule_doc": {"chunker": "semantic", "reranker": "cross_encoder"},
    "temporal": {"chunker": "doc",      "reranker": "dense",        "filter": "date"},
    "entity":   {"chunker": "record",   "reranker": "sparse_bonus"},
    "product":  {"chunker": "card",     "reranker": "dense"},
}

INTENT_TO_COLLECTION: dict[str, str] = {
    "faq":            "faq",
    "time_sensitive": "temporal",
    "entity_lookup":  "entity",
    "rule_question":  "rule_doc",
    "product_query":  "product",
}


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def create_collections_by_source(vector_db) -> None:
    """
    Source-based split. Retrieval can't exploit the structure — it still has to
    search everywhere because the same *kind* of knowledge lives across all three.
    """
    vector_db.create_collection("web_docs")
    vector_db.create_collection("file_docs")
    vector_db.create_collection("db_docs")


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def retrieve_by_intent(intent: str, query: str, run_pipeline) -> list[Doc]:
    """
    Route the query to the collection whose *retrieval nature* matches the
    intent. Each collection runs its own pipeline — no shared-pool compromise.
    """
    collection_name = INTENT_TO_COLLECTION.get(intent, "faq")
    config = COLLECTIONS[collection_name]
    return run_pipeline(collection_name, query, config)
