"""
Shared stub types for the pitfall examples.

These are intentionally thin — each example file demonstrates a *pattern*, not
a runnable RAG system. If you want to execute an example end-to-end, wire the
stubs below to your own vector_db / LLM / cache backend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Doc:
    id: str
    text: str
    embedding: list[float] = field(default_factory=list)
    confidence: float = 0.0
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Query:
    text: str
    expected_answer: str = ""


@dataclass
class Turn:
    role: str                # "user" | "assistant"
    text: str


@dataclass
class FAQ:
    id: str
    question: str
    answer: str


@dataclass
class Point:
    id: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


class VectorDB(Protocol):
    def search(self, vector: list[float], filter: dict | None = None,
               limit: int = 10) -> list[Doc]: ...
    def upsert(self, point: Point) -> None: ...
    def delete(self, filter: dict | None = None,
               ids: list[str] | None = None) -> None: ...
    def query(self, filter: dict) -> list[Doc]: ...
    def fetch_payload(self, filter: dict, limit: int = 1) -> dict | None: ...
    def set_payload(self, ids: list[str], payload: dict) -> None: ...


# Stubs — replace with your real models / clients in production
def embed(text: str) -> list[float]:
    """Dense embedding (e.g. BGE-M3, text-embedding-3-large)."""
    raise NotImplementedError


def cosine_similarity(a: list[float], b: list[float]) -> float:
    raise NotImplementedError


def stable_id(*parts: Any) -> str:
    """Deterministic ID so re-ingestion upserts instead of duplicating."""
    raise NotImplementedError
