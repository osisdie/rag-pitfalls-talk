"""Pit 20 · Evaluation framework — golden set + RAGAS + CI gate."""
from __future__ import annotations

from dataclasses import dataclass

from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import ScenarioBase, SeedContext, registry


@dataclass
class Pit20EvalFramework:
    pit_id: str = "pit_20_eval_framework"
    title: str = "評估框架 · 驗證之神"
    bucket: int = 6
    # The probing question is a magic trigger that both `rag_before` and
    # `rag_after` recognise — before emits a "vibe check" string, after
    # runs an actual benchmark.
    probing_question: str = "run golden benchmark"
    expected_before_substr: str = "vibe"
    expected_after_substr: str = "faithfulness"
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit20EvalFramework())
