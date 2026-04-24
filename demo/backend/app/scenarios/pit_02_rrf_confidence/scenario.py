"""Pit 2 · RRF score ≠ confidence — re-score with cosine for confidence gating."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit02RrfConfidence:
    pit_id: str = "pit_02_rrf_confidence"
    title: str = "RRF 分數 ≠ 信心 · 用 cosine 再評分一次"
    bucket: int = 1
    probing_question: str = "自動扣款失敗還能用哪種繳費方式"
    expected_before_substr: str = "高信心"  # fake-high RRF confidence asserted
    expected_after_substr: str = "中等信心"  # two-stage cosine reveals true confidence
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit02RrfConfidence())
