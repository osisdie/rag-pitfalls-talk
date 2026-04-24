"""Pit 17 · Hot / cold / compressed memory tiers for long chats.

Note: seed pre-loads a 9-turn history into Redis for whatever session
activates this scenario. The probing question 'my 保單編號是多少？'
requires recalling turn 3 — which the before-path forgets.
"""
from __future__ import annotations
from dataclasses import dataclass

from app.core import redis as app_redis
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit17MemoryTiers:
    pit_id: str = "pit_17_memory_tiers"
    title: str = "記憶分層 · hot/cold/compressed"
    bucket: int = 5
    probing_question: str = "我剛剛說的保單編號是多少"
    expected_before_substr: str = "未提供"  # forgets turn 3
    expected_after_substr: str = "P12345678"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)

        # Preload 9-turn history into a well-known "pit17-preload" session
        # so the UI can instantly replay it. In a real rehearsal the speaker
        # activates the scenario then opens that session via deep link.
        turns = load_json(ctx.scenario_dir / "seed" / "preload_turns.json")
        preload_sid = "pit17-preload"
        await app_redis.clear_memory(preload_sid)
        for t in turns:
            await app_redis.push_turn(preload_sid, t["role"], t["content"])


registry.add(Pit17MemoryTiers())
