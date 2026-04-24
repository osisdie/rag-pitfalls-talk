"""Pit 9 · One pipeline for every query wastes latency — lightweight intent router."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit09IntentRouter:
    pit_id: str = "pit_09_intent_router"
    title: str = "意圖路由 · 一條管線打天下 = 浪費"
    bucket: int = 3
    probing_question: str = "我想投訴"
    expected_before_substr: str = "full-pipeline"
    expected_after_substr: str = "handoff"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit09IntentRouter())
