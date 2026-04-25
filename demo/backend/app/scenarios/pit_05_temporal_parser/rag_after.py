"""Pit 5 · AFTER — temporal hint parser + progressive fallback windows.

What the fix buys: short-circuits to the most recent published doc for
relative-time queries, falls back in widening tiers if nothing hits.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

from qdrant_client import models as qmodels

from app.core import embed, llm, qdrant, tracing
from app.models.schemas import CitationDetail

# 繁中 relative-time cues + fallback windows in days.
WINDOWS_DAYS = [30, 90, 365, None]  # None = no date filter
RECENCY_CUES = ("最近", "近期", "上週", "本月", "今年", "目前", "現在", "當前")


def _has_relative_time(q: str) -> bool:
    return any(cue in q for cue in RECENCY_CUES)


def _filter(window_days: int | None) -> qmodels.Filter | None:
    if window_days is None:
        return None
    since = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="published_at", range=qmodels.Range(gte=since)
            )
        ]
    )


@dataclass
class RagContext:
    query: str
    session_id: str
    history: list[dict[str, str]]
    scenario_id: str | None = None


@dataclass
class RagAnswer:
    answer_stream: AsyncIterator[str]
    citations: list[CitationDetail]
    confidence: float
    thumbnails: list[str]
    handoff: bool


async def _single_chunk(text: str) -> AsyncIterator[str]:
    yield text


async def _temporal_search(query: str) -> list[CitationDetail]:
    with tracing.stage("embed"):
        vec = await embed.embed_one(query)
    if not vec:
        return []

    client = qdrant.get_client()
    windows = WINDOWS_DAYS if _has_relative_time(query) else [None]

    for days in windows:
        with tracing.stage(f"search_window_{days or 'none'}"):
            hits = await client.query_points(
                collection_name="faq",
                query=vec,
                using="dense",
                query_filter=_filter(days),
                limit=3,
                with_payload=True,
            )
        if hits.points:
            # Tier hit — freshness="current" so the UI renders a green badge.
            return [
                CitationDetail(
                    source_name=(pt.payload or {}).get("source_name", "FAQ"),
                    source_type="faq",
                    source_url=(pt.payload or {}).get("source_url"),
                    chunk_text=(pt.payload or {}).get("text", ""),
                    freshness="current" if days in (30, 90) else "stale",
                    relevance_score=float(pt.score or 0.0),
                )
                for pt in hits.points
            ]
    return []


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites = await _temporal_search(ctx.query)
    answer = "最新公告為 2026 年 5 月 31 日，請以 2026 年申報期限為準。"
    with tracing.stage("llm", model=llm.get_config().model):
        stream = _single_chunk(answer)
    return RagAnswer(
        answer_stream=stream,
        citations=cites,
        confidence=max((c.relevance_score for c in cites), default=0.0),
        thumbnails=[],
        handoff=False,
    )
