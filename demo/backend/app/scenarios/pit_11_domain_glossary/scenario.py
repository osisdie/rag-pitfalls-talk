"""Pit 11 · Domain glossary — canonical form + aliases for jargon."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit11DomainGlossary:
    pit_id: str = "pit_11_domain_glossary"
    title: str = "領域詞彙表 · 別名 → canonical"
    bucket: int = 3
    probing_question: str = "什麼是遞延負債"
    # Before: raw embed misses — "遞延負債" (informal) vs "遞延所得稅負債" (formal).
    expected_before_substr: str = "找不到"  # low-confidence
    # After: alias expansion → surfaces DTL doc.
    expected_after_substr: str = "DTL"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("rule_doc", docs)


registry.add(Pit11DomainGlossary())
