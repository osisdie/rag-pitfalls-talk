"""BGE-M3 dense embedding client (HF Text Embeddings Inference server).

For sparse retrieval we rely on Qdrant's built-in BM25 (server-side) —
cheaper than running SPLADE, and matches what most production setups
actually use. See app/core/qdrant.py for the BM25 config.
"""
from __future__ import annotations

import httpx

from app.config import get_settings

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def embed_dense(texts: list[str]) -> list[list[float]]:
    """Return BGE-M3 dense embeddings (1024-dim by default)."""
    if not texts:
        return []
    s = get_settings()
    resp = await _get_client().post(
        f"{s.embedder_url}/embed",
        json={"inputs": texts, "truncate": True},
    )
    resp.raise_for_status()
    data = resp.json()
    # HF TEI returns list[list[float]] for batch requests, list[float] for single.
    if isinstance(data[0], float):
        return [data]  # type: ignore[list-item]
    return data


async def embed_one(text: str) -> list[float]:
    vectors = await embed_dense([text])
    return vectors[0] if vectors else []


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
