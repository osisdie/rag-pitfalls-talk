"""
坑 13 · 「今天幾號？」該回 vs「1+1=?」該擋   [Bucket 4: 護欄的拿捏]

現象 Symptom:   太寬：被 prompt injection 拐去寫詩；太嚴：連「今天幾號」都回超出範圍。
成因 Root cause: 單層 "is_faq_topic()" 檢查，只能二元判斷 allow/refuse，無法區分
                benign-meta 與真正的 off-topic。
解法 Solution:  分層 — system prompt 注入 meta（日期、身分），topic classifier 分多類，
                每類有不同處置。
"""
from __future__ import annotations

from datetime import date
from typing import Protocol

from ._common import Doc


class TopicClassifier(Protocol):
    def __call__(self, query: str) -> str: ...


SYSTEM_PROMPT = """你是保險 FAQ 助理。今天的日期是 {today}。
只回答保險條款、理賠、投保流程；其他話題請禮貌婉拒。
每一段回答必須附上 source id。"""

REFUSE_PROMPT = "這超出我的服務範圍，建議您改詢問官方客服。"

# Topics that *look* off-topic but are safe to answer from the system prompt itself.
ALLOWED_META: set[str] = {"ask_date", "ask_time", "ask_self_identity"}

# Topics we refuse outright — math, jailbreak attempts, adult content, etc.
BLOCKED: set[str] = {"math_puzzle", "prompt_injection", "off_topic", "adult"}


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def guard_binary(query: str, is_faq_topic) -> str | None:
    """
    Binary check. Anything not a FAQ topic — including benign "今天幾號" — is refused.
    Loses users to "why is this bot so dumb".
    """
    if not is_faq_topic(query):
        return REFUSE_PROMPT
    return None


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def build_prompt(
    query: str,
    docs: list[Doc],
    today: date,
    topic_classifier: TopicClassifier,
) -> str:
    """
    Three-way branch:
      ALLOWED_META → the system prompt itself already contains the answer
                     (date, self-identity) → just return it, no retrieval needed.
      BLOCKED      → explicit refusal.
      else         → full FAQ pipeline with context.
    """
    topic = topic_classifier(query)
    if topic in ALLOWED_META:
        return SYSTEM_PROMPT.format(today=today)
    if topic in BLOCKED:
        return REFUSE_PROMPT
    return SYSTEM_PROMPT.format(today=today) + "\n\n" + _render_context(docs)


def _render_context(docs: list[Doc]) -> str:
    return "\n".join(f"[{d.id}] {d.text}" for d in docs)
