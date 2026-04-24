"""Scenario registry.

Scenarios import themselves into the registry on package-load. The
frontend `/api/scenarios` endpoint enumerates the registry in insertion
order (so the dropdown lists Bucket 1 first, Bucket 6 last).
"""
from __future__ import annotations

from .base import ScenarioBase, SeedContext, registry

# Trigger side-effect imports so each scenario self-registers.
# Only import modules that actually exist; Phase 2 ships 4 heroes.
for _mod in (
    # Bucket 1
    "app.scenarios.pit_01_hybrid_weights.scenario",
    "app.scenarios.pit_02_rrf_confidence.scenario",
    "app.scenarios.pit_03_rerank_tiered.scenario",
    "app.scenarios.pit_04_ingest_expansion.scenario",
    # Bucket 2
    "app.scenarios.pit_05_temporal_parser.scenario",
    "app.scenarios.pit_06_bitemporal_kg.scenario",
    "app.scenarios.pit_07_content_hash_versioning.scenario",
    "app.scenarios.pit_08_retention_sweep.scenario",
    # Bucket 3
    "app.scenarios.pit_09_intent_router.scenario",
    "app.scenarios.pit_10_entity_disambiguation.scenario",
    "app.scenarios.pit_11_domain_glossary.scenario",
    "app.scenarios.pit_12_handoff_threshold.scenario",
    # Bucket 4
    "app.scenarios.pit_13_layered_guardrails.scenario",
    "app.scenarios.pit_14_regression_gate.scenario",
    "app.scenarios.pit_15_cache_query.scenario",
    # Bucket 5
    "app.scenarios.pit_16_three_layer_cache.scenario",
    "app.scenarios.pit_17_memory_tiers.scenario",
    "app.scenarios.pit_18_multi_collection.scenario",
    "app.scenarios.pit_19_image_materialization.scenario",
    # Bucket 6
    "app.scenarios.pit_20_eval_framework.scenario",
):
    try:
        __import__(_mod)
    except ModuleNotFoundError:
        # Scenarios not yet implemented: silently skip so demo still boots.
        pass

__all__ = ["ScenarioBase", "SeedContext", "registry"]
