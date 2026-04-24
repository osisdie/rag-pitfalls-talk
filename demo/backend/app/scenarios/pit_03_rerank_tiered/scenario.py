"""Pit 3 · Cross-encoder on all candidates kills p95 — tiered rerank."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit03RerankTiered:
    pit_id: str = "pit_03_rerank_tiered"
    title: str = "Cross-encoder 全跑 · p95 直接翻倍"
    bucket: int = 1
    probing_question: str = "理賠申請需要哪些文件"
    expected_before_substr: str = "高延遲"  # bad path explicitly reports
    expected_after_substr: str = "tiered"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit03RerankTiered())
