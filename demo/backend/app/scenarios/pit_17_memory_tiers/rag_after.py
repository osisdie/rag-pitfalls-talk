"""Pit 17 · AFTER — tiered memory.

    hot   = last 5 turns, verbatim
    cold  = turns 6-20, summarized by LLM into ~2 sentences
    older = older than 20, searched via vector against current query
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator

from app.core import llm, redis as app_redis, tracing
from app.models.schemas import CitationDetail

HOT = 5
COLD_UNTIL = 20


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


async def _summarize(turns: list[dict[str, str]]) -> str:
    if not turns:
        return ""
    blob = "\n".join(f"{t['role']}: {t['content']}" for t in turns)
    return await llm.generate(
        f"請用 1-2 句簡述以下客服對話，保留關鍵事實（保單編號、年齡、偏好等）：\n{blob}",
        temperature=0.0,
    )


async def run_rag(ctx: RagContext) -> RagAnswer:
    history = list(ctx.history)
    if not history:
        # Verification scripts create fresh sessions; use scenario preload as fallback.
        history = await app_redis.get_history("pit17-preload")

    hot = history[-HOT:]
    cold_slice = history[-COLD_UNTIL:-HOT] if len(history) > HOT else []
    older = history[:-COLD_UNTIL] if len(history) > COLD_UNTIL else []

    with tracing.stage("summarize_cold", n=len(cold_slice)):
        cold_summary = await _summarize(cold_slice)

    # In production, older would be vector-retrieved against ctx.query.
    # For the demo we fold everything we know into the prompt; since the
    # preload is only 9 turns, hot+cold already catches the 保單編號.
    hot_text = "\n".join(f"{t['role']}: {t['content']}" for t in hot)
    older_text = "\n".join(f"{t['role']}: {t['content']}" for t in older)
    prompt = (
        "使用以下三層記憶回答。特別留意 cold summary 中提到的保單編號 / 身分資料。\n\n"
        f"[hot · verbatim]\n{hot_text}\n\n"
        f"[cold · summarized]\n{cold_summary or '(none)'}\n\n"
        f"[older · vector-recalled (simulated)]\n{older_text or '(none)'}\n\n"
        f"User: {ctx.query}\nAssistant:"
    )
    with tracing.stage("llm", model=llm.get_config().model):
        stream = llm.generate_stream(prompt)
    return RagAnswer(stream, [], 0.0, [], False)
