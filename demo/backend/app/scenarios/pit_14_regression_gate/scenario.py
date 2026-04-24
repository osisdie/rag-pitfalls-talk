"""Pit 14 · Regression gate against a golden set — anti-vibe-coding."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit14RegressionGate:
    pit_id: str = "pit_14_regression_gate"
    title: str = "回歸測試閘道 · 對抗 vibe coding"
    bucket: int = 4
    probing_question: str = "run regression gate"
    expected_before_substr: str = "magic number"
    expected_after_substr: str = "delta"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit14RegressionGate())
