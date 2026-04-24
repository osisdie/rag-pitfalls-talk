"""Pit 4 · Runtime HyDE vs ingest-time expansion — the compute-forward fix."""
from __future__ import annotations
from dataclasses import dataclass
from app.db.seed_loader import load_json, seed_qdrant_docs
from app.scenarios.base import SeedContext, registry


@dataclass
class Pit04IngestExpansion:
    pit_id: str = "pit_04_ingest_expansion"
    title: str = "Runtime HyDE vs 進庫前擴寫"
    bucket: int = 1
    probing_question: str = "接到法院傳票該怎麼辦"
    expected_before_substr: str = "runtime"  # before labels itself
    expected_after_substr: str = "variant"  # after cites variant chunks
    has_graph_seed: bool = False
    has_image_seed: bool = False

    async def seed(self, ctx: SeedContext) -> None:
        docs = load_json(ctx.scenario_dir / "seed" / "qdrant_docs.json")
        await seed_qdrant_docs("faq", docs)


registry.add(Pit04IngestExpansion())
