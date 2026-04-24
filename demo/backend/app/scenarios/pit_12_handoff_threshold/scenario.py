"""Pit 12 · Handoff threshold — 'I don't know' is a feature."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit12HandoffThreshold:
    pit_id: str = "pit_12_handoff_threshold"
    title: str = "Handoff threshold · 不會就說不會"
    bucket: int = 3
    probing_question: str = "我的理賠金額大概多少"
    expected_before_substr: str = "NT"  # before fabricates a number
    expected_after_substr: str = "轉接"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit12HandoffThreshold())
