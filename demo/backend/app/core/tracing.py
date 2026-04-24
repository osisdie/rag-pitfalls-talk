"""Lightweight per-request timeline for the 'Timeline' UI affordance.

Collects stage timings via a context manager; the final list is returned
alongside ChatResponse so the audience can see "embed 120 ms / search 80 ms
/ rerank 40 ms / llm 1200 ms" at a glance.
"""
from __future__ import annotations

import contextvars
import time
from contextlib import contextmanager
from typing import Iterator

from app.models.schemas import TimelineEvent

_current: contextvars.ContextVar[list[TimelineEvent] | None] = contextvars.ContextVar(
    "rag_timeline", default=None
)


def start() -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    _current.set(events)
    return events


def events() -> list[TimelineEvent]:
    return _current.get() or []


@contextmanager
def stage(name: str, **meta) -> Iterator[None]:
    t0 = time.perf_counter()
    try:
        yield
    finally:
        bucket = _current.get()
        if bucket is not None:
            bucket.append(
                TimelineEvent(
                    stage=name,
                    took_ms=(time.perf_counter() - t0) * 1000.0,
                    meta=meta,
                )
            )
