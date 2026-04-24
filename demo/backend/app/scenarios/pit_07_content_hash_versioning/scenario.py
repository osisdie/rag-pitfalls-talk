"""Pit 7 · Naive upsert leaves orphan chunks — content-hash + orphan delete."""
from __future__ import annotations

from dataclasses import dataclass

from app.core import qdrant as qcore
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import ScenarioBase, SeedContext, registry


@dataclass
class Pit07ContentHash:
    pit_id: str = "pit_07_content_hash_versioning"
    title: str = "內容雜湊版本 · 沒做好留下孤兒 chunk"
    bucket: int = 2
    probing_question: str = "理賠天數是多久"
    # "Before" mixes old "5-7 天" + new "3 天" citations — LLM will be confused.
    # "After" shows only the latest (v2) chunk per source_url.
    expected_before_substr: str = "5-7"
    expected_after_substr: str = "3"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        # Seed BOTH old + new as if a naive ingestion pass had appended
        # the new version without deleting the old one.
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("rule_doc", docs)


registry.add(Pit07ContentHash())
