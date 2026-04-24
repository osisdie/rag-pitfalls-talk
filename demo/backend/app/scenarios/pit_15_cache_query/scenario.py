"""Pit 15 · Cache the query, not the answer."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit15CacheQuery:
    pit_id: str = "pit_15_cache_query"
    title: str = "快取 query, 不是 answer"
    bucket: int = 4
    probing_question: str = "營業時間是幾點"
    expected_before_substr: str = "hardcoded"
    expected_after_substr: str = "09:00"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit15CacheQuery())
