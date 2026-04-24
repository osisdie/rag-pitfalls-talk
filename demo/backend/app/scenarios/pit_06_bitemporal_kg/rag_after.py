"""Pit 6 · AFTER — bi-temporal Cypher with $as_of parameter.

Parses relative time cues ("2 年前" → as_of = now - 2y), then queries
the graph for `FACT` edges where valid_at <= as_of AND
(invalid_at IS NULL OR invalid_at > as_of). Pulls the matching rule
version's doc from Qdrant and returns as the citation.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

from app.core import embed, graph, llm, qdrant, tracing
from app.models.schemas import CitationDetail


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


def _parse_as_of(q: str) -> datetime:
    m = re.search(r"(\d+)\s*年前", q)
    if m:
        years = int(m.group(1))
        return datetime.now(timezone.utc) - timedelta(days=365 * years)
    return datetime.now(timezone.utc)


async def _cypher_rules_version(as_of: datetime) -> str | None:
    rows = await graph.run_cypher(
        """
        MATCH (s:Entity {name: '採購合約'})-[r:FACT {predicate: 'APPLIES_RULES_VERSION'}]->(o:Entity)
        WHERE r.valid_at <= datetime($as_of)
          AND (r.invalid_at IS NULL OR r.invalid_at > datetime($as_of))
        RETURN o.name AS version
        LIMIT 1
        """,
        {"as_of": as_of.isoformat().replace("+00:00", "Z")},
    )
    return rows[0]["version"] if rows else None


async def _retrieve(query: str) -> tuple[list[CitationDetail], CitationDetail | None]:
    as_of = _parse_as_of(query)
    with tracing.stage("cypher_as_of", as_of=as_of.isoformat()):
        version = await _cypher_rules_version(as_of)

    vec = await embed.embed_one(query)
    client = qdrant.get_client()
    with tracing.stage("search_rule_doc"):
        hits = await client.query_points(collection_name="rule_doc", query=vec, using="dense", limit=5, with_payload=True)

    target = None
    others = []
    for pt in hits.points:
        p = pt.payload or {}
        cite = CitationDetail(
            source_name=p.get("source_name", "rule_doc"), source_type="temporal",
            source_url=p.get("source_url"), chunk_text=p.get("text", ""),
            edge_fact=f"APPLIES_RULES_VERSION={version} as_of={as_of.date()}" if version else None,
            freshness="current" if str(p.get("version", "")) == (version or "").replace("v", "") else "stale",
            relevance_score=float(pt.score or 0.0),
        )
        if version and str(p.get("version", "")) == version.replace("v", ""):
            target = cite
        else:
            others.append(cite)
    cites = ([target] if target else []) + others
    return cites[:3], target


async def run_rag(ctx: RagContext) -> RagAnswer:
    cites, target = await _retrieve(ctx.query)
    ctx_text = "\n\n".join(f"[{i+1}] {c.chunk_text}" for i, c in enumerate(cites))
    prompt = (
        "根據當時有效的合約版本回答（注意生效日期）。\n\n"
        f"Context:\n{ctx_text}\n\nUser: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, cites, max((c.relevance_score for c in cites), default=0.0), [], False)
