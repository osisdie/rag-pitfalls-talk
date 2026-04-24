"""ScenarioBase Protocol + in-memory registry.

Each scenario lives in its own package (`pit_NN_name/`) and ships:
    scenario.py       — instance of ScenarioBase, calls register()
    rag_before.py     — full module replacing /app/core/rag.py (❌ pattern)
    rag_after.py      — full module replacing /app/core/rag.py (✅ pattern)
    seed/*.json       — qdrant docs, graphiti episodes, (optional) images

The registry holds scenario instances in insertion order. Scenarios are
keyed by their `pit_id` string.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Protocol, runtime_checkable

from app.models.schemas import ScenarioMeta


@dataclass
class SeedContext:
    """Passed to Scenario.seed()."""
    scenario_dir: Path  # path to the scenario package on disk
    rag_version_recorder: Callable[[str, str], Awaitable[int]]  # (label, source) → version_id


@runtime_checkable
class ScenarioBase(Protocol):
    pit_id: str
    title: str
    bucket: int
    probing_question: str
    expected_before_substr: str
    expected_after_substr: str
    has_graph_seed: bool
    has_image_seed: bool

    async def seed(self, ctx: SeedContext) -> None: ...


@dataclass
class _Registry:
    scenarios: dict[str, ScenarioBase] = field(default_factory=dict)

    def add(self, sc: ScenarioBase) -> None:
        self.scenarios[sc.pit_id] = sc

    def get(self, pit_id: str) -> ScenarioBase | None:
        return self.scenarios.get(pit_id)

    def all(self) -> list[ScenarioBase]:
        return list(self.scenarios.values())


registry = _Registry()


def scenario_meta(sc: ScenarioBase, current_state: str = "before") -> ScenarioMeta:
    return ScenarioMeta(
        pit_id=sc.pit_id,
        title=sc.title,
        bucket=sc.bucket,
        probing_question=sc.probing_question,
        expected_before_substr=sc.expected_before_substr,
        expected_after_substr=sc.expected_after_substr,
        has_graph_seed=sc.has_graph_seed,
        has_image_seed=sc.has_image_seed,
        current_state=current_state,  # type: ignore[arg-type]
    )


def scenario_dir(pit_id: str) -> Path:
    """Return on-disk path to the scenario package."""
    from app.config import get_settings

    return get_settings().scenarios_root / pit_id


def rag_before_source(pit_id: str) -> str:
    p = scenario_dir(pit_id) / "rag_before.py"
    if not p.exists():
        raise FileNotFoundError(p)
    return p.read_text(encoding="utf-8")


def rag_after_source(pit_id: str) -> str:
    p = scenario_dir(pit_id) / "rag_after.py"
    if not p.exists():
        raise FileNotFoundError(p)
    return p.read_text(encoding="utf-8")
