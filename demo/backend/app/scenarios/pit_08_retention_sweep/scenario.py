"""Pit 8 · No retention = slow death — monthly sweep + cold tier."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit08RetentionSweep:
    pit_id: str = "pit_08_retention_sweep"
    title: str = "沒做 retention · 老公告拖慢 p95"
    bucket: int = 2
    probing_question: str = "2020 年的公告還有用嗎"
    # Before: returns archived 2020 docs → confuses user.
    # After: filters `archived=true`; notes they're in cold tier.
    expected_before_substr: str = "居家辦公"
    expected_after_substr: str = "已歸檔"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit08RetentionSweep())
