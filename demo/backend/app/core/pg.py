"""PostgreSQL pool + chat session / message / rag_versions persistence.

Schema:
    chat_sessions   (id UUID pk, created_at, scenario_id)
    chat_messages   (id UUID pk, session_id fk, role, content, citations JSONB,
                     confidence, handoff, created_at)
    rag_versions    (id serial pk, scenario_id, author, label, source TEXT,
                     created_at)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg

from app.config import get_settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        s = get_settings()
        _pool = await asyncpg.create_pool(dsn=s.postgres_dsn, min_size=1, max_size=10)
    return _pool


# ─── Sessions ─────────────────────────────────────────────────


async def create_session(scenario_id: str | None = None) -> str:
    pool = await get_pool()
    sid = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_sessions (id, scenario_id, created_at) VALUES ($1, $2, $3)",
            sid,
            scenario_id,
            datetime.now(timezone.utc),
        )
    return sid


async def delete_session(session_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM chat_messages WHERE session_id = $1", session_id
        )
        await conn.execute("DELETE FROM chat_sessions WHERE id = $1", session_id)


async def session_exists(session_id: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM chat_sessions WHERE id = $1", session_id
        )
        return row is not None


# ─── Messages ─────────────────────────────────────────────────


async def append_message(
    session_id: str,
    role: str,
    content: str,
    citations: list[dict[str, Any]] | None = None,
    confidence: float = 0.0,
    handoff: bool = False,
) -> str:
    pool = await get_pool()
    mid = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO chat_messages
                (id, session_id, role, content, citations, confidence, handoff, created_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8)
            """,
            mid,
            session_id,
            role,
            content,
            json.dumps(citations or []),
            confidence,
            handoff,
            datetime.now(timezone.utc),
        )
    return mid


async def list_messages(session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, role, content, citations, confidence, handoff, created_at
            FROM chat_messages WHERE session_id = $1
            ORDER BY created_at ASC LIMIT $2
            """,
            session_id,
            limit,
        )
    return [dict(r) for r in rows]


# ─── rag.py versions ──────────────────────────────────────────


async def insert_version(
    scenario_id: str | None, author: str, label: str, source: str
) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO rag_versions (scenario_id, author, label, source, created_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            scenario_id,
            author,
            label,
            source,
            datetime.now(timezone.utc),
        )
    return int(row["id"])


async def latest_version(scenario_id: str | None) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, scenario_id, author, label, source, created_at
            FROM rag_versions
            WHERE ($1::text IS NULL OR scenario_id = $1)
            ORDER BY id DESC LIMIT 1
            """,
            scenario_id,
        )
    return dict(row) if row else None


async def list_versions(
    scenario_id: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, scenario_id, author, label, source, created_at
            FROM rag_versions
            WHERE ($1::text IS NULL OR scenario_id = $1)
            ORDER BY id DESC LIMIT $2
            """,
            scenario_id,
            limit,
        )
    return [dict(r) for r in rows]


async def get_version(version_id: int) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, scenario_id, author, label, source, created_at FROM rag_versions WHERE id = $1",
            version_id,
        )
    return dict(row) if row else None


async def prune_versions(scenario_id: str, keep: int) -> int:
    """Cap rag_versions growth per scenario (default 10)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        deleted = await conn.execute(
            """
            DELETE FROM rag_versions
            WHERE scenario_id = $1 AND id NOT IN (
                SELECT id FROM rag_versions
                WHERE scenario_id = $1
                ORDER BY id DESC LIMIT $2
            )
            """,
            scenario_id,
            keep,
        )
    return int(deleted.split()[-1]) if deleted.startswith("DELETE ") else 0


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
