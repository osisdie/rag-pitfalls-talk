"""Pit 18 · Multi-collection by retrieval nature, not by source."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit18MultiCollection:
    pit_id: str = "pit_18_multi_collection"
    title: str = "多集合路由 · 按性質不按來源"
    bucket: int = 5
    probing_question: str = "公司統編是多少"
    expected_before_substr: str = "web_docs"  # before cites wrong bucket
    expected_after_substr: str = "12345678"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        # entity-kind docs go to entity collection; faq-kind to faq.
        ents = [d for d in docs if d.get("source_type") == "entity"]
        faqs = [d for d in docs if d.get("source_type") == "faq"]
        await seed_qdrant_docs("entity", ents)
        await seed_qdrant_docs("faq", faqs)


registry.add(Pit18MultiCollection())
