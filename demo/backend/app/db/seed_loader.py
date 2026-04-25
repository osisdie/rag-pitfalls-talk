"""Shared seed-loading helpers.

Scenario `seed()` implementations use these to upsert docs, episodes, images
in a uniform way so the scenario code stays short and readable.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from qdrant_client import models as qmodels

from app.core import embed, graph, qdrant

log = logging.getLogger(__name__)

_bm25_embedder = None


def _get_bm25_embedder():
    """Lazy-init the fastembed BM25 sparse encoder.

    qdrant-client's `Document` helper only runs fastembed on the query path —
    on upsert it ships the Document to the server and expects server-side
    inference. Our Qdrant container has no inference service, so we encode
    BM25 client-side at seed time and submit raw (indices, values) as a
    SparseVector. The collection's `Modifier.IDF` applies IDF on the server
    during scoring.
    """
    global _bm25_embedder
    if _bm25_embedder is None:
        from fastembed import SparseTextEmbedding
        _bm25_embedder = SparseTextEmbedding("Qdrant/bm25")
    return _bm25_embedder


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def stable_point_id(*parts: str) -> str:
    """Deterministic UUID-ish id so repeated seeds are idempotent."""
    h = hashlib.md5(":".join(parts).encode("utf-8")).hexdigest()
    return str(uuid.UUID(h))


async def seed_qdrant_docs(
    collection: str,
    docs: list[dict[str, Any]],
    *,
    recreate: bool = True,
    text_key: str = "text",
) -> int:
    """Embed + upsert docs into a Qdrant collection.

    Each doc is a dict with at least a `text` key; the full dict becomes
    the payload, and id defaults to `stable_point_id(collection, text)`
    unless `doc["id"]` is provided.
    """
    if recreate:
        await qdrant.drop_collection(collection)
    await qdrant.ensure_collection(collection)

    client = qdrant.get_client()
    texts = [d[text_key] for d in docs]
    if not texts:
        return 0
    vectors = await embed.embed_dense(texts)

    bm25 = _get_bm25_embedder()
    sparse = list(bm25.embed(texts))  # SparseEmbedding(indices, values) per doc

    points = []
    for i, d in enumerate(docs):
        pid = d.get("id") or stable_point_id(collection, d[text_key])
        points.append(
            qmodels.PointStruct(
                id=pid,
                vector={
                    "dense": vectors[i],
                    "bm25": qmodels.SparseVector(
                        indices=sparse[i].indices.tolist(),
                        values=sparse[i].values.tolist(),
                    ),
                },
                payload=d,
            )
        )
    await client.upsert(collection_name=collection, points=points)
    log.info("seeded %d docs into %s", len(points), collection)
    return len(points)


async def seed_graphiti_episodes(episodes: list[dict[str, Any]]) -> int:
    """Write episodes as (entity)-[fact]->(entity) triples with valid_at.

    For a public demo we keep this explicit & readable rather than going
    through Graphiti's episodic ingestion pipeline (which needs the LLM).
    """
    if not episodes:
        return 0
    # Reset demo graph for idempotent seed runs
    await graph.run_cypher("MATCH (n) DETACH DELETE n")
    count = 0
    for ep in episodes:
        await graph.run_cypher(
            """
            MERGE (s:Entity {name: $subject})
            MERGE (o:Entity {name: $object})
            CREATE (s)-[r:FACT {
                predicate:  $predicate,
                valid_at:   datetime($valid_at),
                invalid_at: CASE WHEN $invalid_at IS NULL THEN NULL ELSE datetime($invalid_at) END,
                source:     $source
            }]->(o)
            """,
            {
                "subject": ep["subject"],
                "predicate": ep["predicate"],
                "object": ep["object"],
                "valid_at": ep["valid_at"],
                "invalid_at": ep.get("invalid_at"),
                "source": ep.get("source", "seed"),
            },
        )
        count += 1
    log.info("seeded %d Graphiti episodes", count)
    return count


def load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
