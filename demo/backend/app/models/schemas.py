"""Pydantic request / response schemas.

Mirrors the shapes of `ai-rag-graphiti` (`CitationDetail`) and
`Agentory-CS` (image thumbnails) so future UI components can be
ported with minimal re-mapping.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ─── Citations / retrieval ─────────────────────────────────────

SourceType = Literal["faq", "rule_doc", "entity", "temporal", "graph"]
Freshness = Literal["current", "stale", "expired"]


class CitationDetail(BaseModel):
    source_name: str
    source_type: SourceType
    source_url: str | None = None
    chunk_text: str = ""
    edge_fact: str | None = None  # present for graph-backed citations
    entity_name: str | None = None
    freshness: Freshness | None = None
    source_date: datetime | None = None
    relevance_score: float = 0.0
    image_url: str | None = None  # materialized local URL (pit_19)


class TimelineEvent(BaseModel):
    stage: str  # e.g. "embed", "search_dense", "search_sparse", "rerank", "llm"
    took_ms: float
    meta: dict = Field(default_factory=dict)


# ─── Chat ─────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    scenario_id: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime | None = None


class ChatResponse(BaseModel):
    """Non-streaming envelope returned after SSE completion.

    Streaming chunks arrive as `event: token` / `event: done` SSE events;
    after `done` the client can fetch this envelope for structured metadata.
    """

    answer: str
    session_id: str
    message_id: str
    citations: list[CitationDetail] = Field(default_factory=list)
    confidence: float = 0.0
    thumbnails: list[str] = Field(default_factory=list)
    handoff: bool = False
    timeline: list[TimelineEvent] = Field(default_factory=list)
    rag_version_id: int | None = None
    scenario_id: str | None = None


# ─── Scenarios ────────────────────────────────────────────────


class ScenarioMeta(BaseModel):
    pit_id: str
    title: str
    bucket: int
    probing_question: str
    expected_before_substr: str
    expected_after_substr: str
    has_graph_seed: bool = False
    has_image_seed: bool = False
    current_state: Literal["before", "after", "custom"] = "before"


# ─── rag.py versioning ────────────────────────────────────────


class RagVersion(BaseModel):
    id: int
    label: str
    source: str
    author: str  # scenario_id or "manual"
    created_at: datetime


class ApplyFixResult(BaseModel):
    ok: bool
    version_id: int | None = None
    error: str | None = None
    rolled_back: bool = False


class SaveCodeRequest(BaseModel):
    source: str
    label: str = "manual edit"


# ─── LLM config ───────────────────────────────────────────────


class LLMConfig(BaseModel):
    model: Literal["gemini-2.5-flash-lite", "gemini-2.5-flash"] = "gemini-2.5-flash-lite"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    web_search: bool = False  # requires model != -lite


# ─── Sessions ─────────────────────────────────────────────────


class SessionMeta(BaseModel):
    session_id: str
    created_at: datetime
    message_count: int
