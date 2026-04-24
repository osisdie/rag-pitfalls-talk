"""Pit 10 · Short-entity queries need sparse bonus with dense-floor safeguard."""
from __future__ import annotations

from dataclasses import dataclass

from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import ScenarioBase, SeedContext, registry


@dataclass
class Pit10EntityDisambig:
    pit_id: str = "pit_10_entity_disambiguation"
    title: str = "短實體查詢 · 稀疏加分 + 密集安全閥"
    bucket: int = 3
    probing_question: str = "誰是張主任"
    # "Before" surfaces the generic "director" definition, missing the named person.
    # "After" surfaces the employee directory entry with photo.
    expected_before_substr: str = "中階主管"
    expected_after_substr: str = "風險管理部"
    has_graph_seed: bool = False
    has_image_seed: bool = True

    async def seed(self, ctx: SeedContext) -> None:
        # Mix rule_doc + entity rows in one collection so short-query
        # ranking is an honest competition. The scenario seeds into
        # "entity" collection which is the one rag_after.py queries.
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("entity", docs)


registry.add(Pit10EntityDisambig())
