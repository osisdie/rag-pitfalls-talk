"""Pit 13 · AFTER — classifier with multiple allow-list buckets.

Meta questions ('今天幾號', '你是誰') pass through with a system prompt
that carries today's date + persona. Scope refusals still trigger on
truly off-topic, but not on benign meta.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import AsyncIterator

from app.core import llm, tracing
from app.models.schemas import CitationDetail

BUSINESS = ("保險", "理賠", "保費", "保單", "投保")
META_DATE = ("今天", "幾號", "日期", "星期")
META_SELF = ("你是", "誰是你", "你叫什麼")
INJECTION = ("ignore previous", "忘掉前面", "system prompt")


def _classify(q: str) -> str:
    if any(p in q.lower() for p in INJECTION):
        return "injection"
    if any(p in q for p in META_DATE):
        return "meta_date"
    if any(p in q for p in META_SELF):
        return "meta_self"
    if any(p in q for p in BUSINESS):
        return "business"
    return "out_of_scope"


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


async def _canned(text: str):
    yield text + "\n"


async def run_rag(ctx: RagContext) -> RagAnswer:
    with tracing.stage("layered_classify"):
        intent = _classify(ctx.query)

    if intent == "injection":
        return RagAnswer(_canned("我會依照原始指令協助您，不接受更改指令。"), [], 0.0, [], False)
    if intent == "out_of_scope":
        return RagAnswer(_canned("很抱歉，本助理僅回答保險相關問題。"), [], 0.0, [], False)

    today = date.today()
    system = (
        f"你是一位保險客服 AI 助理。\n"
        f"今天是 {today.isoformat()} (western) · 民國 {today.year - 1911} 年 {today.month} 月 {today.day} 日。\n"
        "若被問及日期時間，請直接用系統提供的今天回答。"
    )
    with tracing.stage("llm_with_meta_system", intent=intent):
        stream = llm.generate_stream(ctx.query, system=system)
    return RagAnswer(stream, [], 0.0, [], False)
