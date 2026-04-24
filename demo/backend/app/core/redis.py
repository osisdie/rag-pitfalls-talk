"""Redis hot-memory for chat history + response cache.

Mirrors Agentory-CS's Redis-hot + PG-cold dual-write:
- `memory:{session_id}` LIST of json-encoded turns, trimmed to MEMORY_WINDOW_SIZE
- `cache:response:{key}` response cache (used by pit_15, pit_16)
"""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

_client: aioredis.Redis | None = None


def get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        s = get_settings()
        _client = aioredis.from_url(s.redis_url, decode_responses=True)
    return _client


# ─── Memory (last N turns) ────────────────────────────────────


def _mem_key(session_id: str) -> str:
    return f"memory:{session_id}"


async def push_turn(session_id: str, role: str, content: str) -> None:
    s = get_settings()
    client = get_client()
    key = _mem_key(session_id)
    await client.rpush(key, json.dumps({"role": role, "content": content}))
    await client.ltrim(key, -s.memory_window_size * 2, -1)  # keep N user+assistant pairs


async def get_history(session_id: str) -> list[dict[str, str]]:
    s = get_settings()
    client = get_client()
    raw = await client.lrange(_mem_key(session_id), -s.memory_window_size * 2, -1)
    return [json.loads(r) for r in raw]


async def clear_memory(session_id: str) -> None:
    await get_client().delete(_mem_key(session_id))


# ─── Response cache (pit_15, pit_16) ──────────────────────────


async def cache_response_get(key: str) -> dict[str, Any] | None:
    raw = await get_client().get(f"cache:response:{key}")
    return json.loads(raw) if raw else None


async def cache_response_set(key: str, value: dict[str, Any], ttl: int = 86400) -> None:
    await get_client().setex(f"cache:response:{key}", ttl, json.dumps(value))


async def cache_response_bust_prefix(prefix: str) -> int:
    client = get_client()
    count = 0
    async for key in client.scan_iter(match=f"cache:response:{prefix}*"):
        await client.delete(key)
        count += 1
    return count


async def close() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
