"""Pit 16 · Three-layer cache: response / embedding / image."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit16ThreeLayerCache:
    pit_id: str = "pit_16_three_layer_cache"
    title: str = "三層快取 · response/embedding/image"
    bucket: int = 5
    probing_question: str = "產品保固多久"
    expected_before_substr: str = "combined TTL"
    expected_after_substr: str = "layers"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit16ThreeLayerCache())
