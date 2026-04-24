"""Pit 19 · Materialize images at ingestion — don't trust external URLs."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit19ImageMaterialization:
    pit_id: str = "pit_19_image_materialization"
    title: str = "圖片落地 · 別信外部 URL"
    bucket: int = 5
    probing_question: str = "新台幣紙鈔長怎樣"
    expected_before_substr: str = "外部"
    expected_after_substr: str = "本地"
    has_graph_seed: bool = False
    has_image_seed: bool = True

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit19ImageMaterialization())
