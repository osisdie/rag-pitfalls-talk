"""Pit 5 · Relative time needs a parser + fallback tiers."""
from __future__ import annotations

from dataclasses import dataclass

from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import ScenarioBase, SeedContext, registry


@dataclass
class Pit05Temporal:
    pit_id: str = "pit_05_temporal_parser"
    title: str = "相對時間需要 parser + fallback tiers"
    bucket: int = 2
    probing_question: str = "最近的申報期限是什麼時候"
    # "Before" retrieves 2019 or 2022 because dense similarity dominates;
    # "after" narrows to the most recent filing window (2026).
    expected_before_substr: str = "2019"
    expected_after_substr: str = "2026"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit05Temporal())
