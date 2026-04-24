"""Qdrant client factory + collection bootstrap.

Collections use a **named dense vector** ("dense") + **BM25 sparse vector**
("bm25") layout so scenarios can demo hybrid retrieval without an extra
SPLADE service. Qdrant v1.10+ has native BM25 support.
"""
from __future__ import annotations

from qdrant_client import AsyncQdrantClient, models

from app.config import get_settings

_client: AsyncQdrantClient | None = None

# Standard collections seeded across scenarios. Per-scenario variants
# may swap payload schemas but keep these names stable.
COLLECTIONS = {
    "faq": {"distance": models.Distance.COSINE, "size": 1024},
    "rule_doc": {"distance": models.Distance.COSINE, "size": 1024},
    "entity": {"distance": models.Distance.COSINE, "size": 1024},
    "temporal": {"distance": models.Distance.COSINE, "size": 1024},
}


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        s = get_settings()
        _client = AsyncQdrantClient(url=s.qdrant_url, prefer_grpc=False)
    return _client


async def ensure_collection(
    name: str,
    vector_size: int = 1024,
    distance: models.Distance = models.Distance.COSINE,
) -> None:
    """Idempotently create a collection with dense + BM25 sparse vectors."""
    client = get_client()
    existing = {c.name for c in (await client.get_collections()).collections}
    if name in existing:
        return
    await client.create_collection(
        collection_name=name,
        vectors_config={
            "dense": models.VectorParams(size=vector_size, distance=distance),
        },
        sparse_vectors_config={
            "bm25": models.SparseVectorParams(
                modifier=models.Modifier.IDF,  # IDF-weighted BM25
            ),
        },
    )


async def drop_collection(name: str) -> None:
    client = get_client()
    try:
        await client.delete_collection(collection_name=name)
    except Exception:
        pass


async def ensure_all_defaults() -> None:
    for name, cfg in COLLECTIONS.items():
        await ensure_collection(
            name, vector_size=cfg["size"], distance=cfg["distance"]
        )


async def close() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
