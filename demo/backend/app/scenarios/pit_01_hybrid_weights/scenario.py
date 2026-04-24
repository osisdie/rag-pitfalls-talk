"""Pit 1 · Hybrid weighted-blend is a trap — use RRF."""
from __future__ import annotations

from dataclasses import dataclass

from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit01HybridWeights:
    pit_id: str = "pit_01_hybrid_weights"
    title: str = "Hybrid 加權融合的陷阱 · 改用 RRF"
    bucket: int = 1
    probing_question: str = "投保退件怎麼辦"
    # "Before" mis-ranks because dense + BM25 have incomparable scale:
    # surfaces the customer-service hotline as top hit.
    expected_before_substr: str = "客服"
    # "After" via RRF correctly ranks the 退件原因 doc first.
    expected_after_substr: str = "健康告知"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit01HybridWeights())
