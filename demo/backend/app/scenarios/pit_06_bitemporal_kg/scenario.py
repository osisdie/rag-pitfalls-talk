"""Pit 6 · Vector DB is timeless — bi-temporal KG for historical facts."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs, seed_graphiti_episodes
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit06BitemporalKG:
    pit_id: str = "pit_06_bitemporal_kg"
    title: str = "Bi-temporal KG · 歷史事實需要時間維度"
    bucket: int = 2
    probing_question: str = "2 年前簽的合約適用什麼規則"
    # Before: returns v2 (latest) — wrong.
    # After: Cypher as_of=2023 → returns v1.
    expected_before_substr: str = "60 天"
    expected_after_substr: str = "30 天"
    has_graph_seed: bool = True
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("rule_doc", docs)
        episodes = load_json(ctx.scenario_dir / "seed" / "graphiti_episodes.json")
        await seed_graphiti_episodes(episodes)


registry.add(Pit06BitemporalKG())
