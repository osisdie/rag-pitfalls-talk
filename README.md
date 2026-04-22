# RAG Pitfalls · 20 個 Production 踩坑與解法

> 公開演講的程式碼範本 · Companion code for the talk
> **《RAG 系統踩坑 · 從 60% 到 95% 的那 20 個小時》**
> HIT LLM Foundation 技術交流群 · 2026-04
> 講者 Speaker: **Kevin Wu**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

20 real pitfalls hit while running **production RAG** for legal / accounting
/ insurance FAQ bots. Each pit is one Python file with an **anti-pattern**
(❌) and a **recommended replacement** (✅) side-by-side, so a reader can
see the problem and the fix in one screen.

這份 repo 是一場關於 RAG 系統踩坑的公開演講的**程式碼伴讀**。演講主軸是
「當你的 RAG 已經跑起來之後，還會在哪 20 個地方壞掉」。每個坑用一個 Python
檔案呈現：上半段 ❌ 反模式、下半段 ✅ 建議寫法，肉眼可比較。

## 使用方式 · How to read

```bash
git clone https://github.com/<your-org>/rag-pitfalls-talk.git
cd rag-pitfalls-talk

# (optional) install the libs the examples reference
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Then open any `pitfalls/pit_NN_*.py` in your editor. The examples are
**readable, type-checked pseudocode** — they demonstrate *patterns*, not a
runnable end-to-end RAG system. Wire the stubs in
[`pitfalls/_common.py`](pitfalls/_common.py) to your real vector DB / LLM /
cache backend to execute them.

## 目錄 · The 20 pitfalls

### Bucket 1 · 取回的藝術 · The Art of Retrieval

| # | Pitfall | File |
|---|---|---|
| 1 | Hybrid search weighted-blend is a trap — use RRF | [pit_01_hybrid_weights.py](pitfalls/pit_01_hybrid_weights.py) |
| 2 | RRF score isn't confidence — re-score with cosine  | [pit_02_rrf_confidence.py](pitfalls/pit_02_rrf_confidence.py) |
| 3 | Cross-encoder on all candidates kills p95 latency  | [pit_03_rerank_tiered.py](pitfalls/pit_03_rerank_tiered.py) |
| 4 | Runtime HyDE vs. ingest-time expansion             | [pit_04_ingest_expansion.py](pitfalls/pit_04_ingest_expansion.py) |

### Bucket 2 · 時間的詛咒 · The Curse of Time

| # | Pitfall | File |
|---|---|---|
| 5 | Relative time («最近») needs a parser + fallback tiers | [pit_05_temporal_parser.py](pitfalls/pit_05_temporal_parser.py) |
| 6 | Vector DB is timeless — bi-temporal KG for historical facts | [pit_06_bitemporal_kg.py](pitfalls/pit_06_bitemporal_kg.py) |
| 7 | Naive upsert leaves orphan chunks — content-hash + orphan delete | [pit_07_content_hash_versioning.py](pitfalls/pit_07_content_hash_versioning.py) |
| 8 | No retention = slow death — monthly sweep + cold tier | [pit_08_retention_sweep.py](pitfalls/pit_08_retention_sweep.py) |

### Bucket 3 · 讀懂用戶 · Understanding Users

| # | Pitfall | File |
|---|---|---|
| 9  | One pipeline for every query wastes latency — lightweight intent router | [pit_09_intent_router.py](pitfalls/pit_09_intent_router.py) |
| 10 | Short entity queries need a sparse-match bonus with dense-floor safeguard | [pit_10_entity_disambiguation.py](pitfalls/pit_10_entity_disambiguation.py) |
| 11 | Domain glossary — canonical form + aliases for jargon | [pit_11_domain_glossary.py](pitfalls/pit_11_domain_glossary.py) |
| 12 | Handoff threshold — «I don't know» is a feature | [pit_12_handoff_threshold.py](pitfalls/pit_12_handoff_threshold.py) |

### Bucket 4 · 護欄的拿捏 · Guardrails Calibration

| # | Pitfall | File |
|---|---|---|
| 13 | Layered guardrails — allow benign meta, block injection | [pit_13_layered_guardrails.py](pitfalls/pit_13_layered_guardrails.py) |
| 14 | Regression gate against a golden set — the anti-vibe-coding pattern | [pit_14_regression_gate.py](pitfalls/pit_14_regression_gate.py) |
| 15 | Cache the *query*, not the *answer* | [pit_15_cache_query.py](pitfalls/pit_15_cache_query.py) |

### Bucket 5 · 基礎設施 · Infrastructure

| # | Pitfall | File |
|---|---|---|
| 16 | Three-layer cache: response / embedding / image — each with its own TTL | [pit_16_three_layer_cache.py](pitfalls/pit_16_three_layer_cache.py) |
| 17 | Hot / cold / compressed memory tiers for long chats | [pit_17_memory_tiers.py](pitfalls/pit_17_memory_tiers.py) |
| 18 | Multi-collection by *retrieval nature*, not by *source* | [pit_18_multi_collection.py](pitfalls/pit_18_multi_collection.py) |
| 19 | Materialize images at ingestion — don't trust external URLs | [pit_19_image_materialization.py](pitfalls/pit_19_image_materialization.py) |

### Bucket 6 · 驗證之神 · The God of Verification

| # | Pitfall | File |
|---|---|---|
| 20 | Golden set + RAGAS + CI gate — the meta-pitfall that validates the other 19 | [pit_20_eval_framework.py](pitfalls/pit_20_eval_framework.py) |

## 結構 · Structure

```
rag-pitfalls-talk/
├── README.md                              # you are here
├── LICENSE                                # MIT
├── requirements.txt                       # libs referenced across pits
├── pitfalls/
│   ├── __init__.py
│   ├── _common.py                         # shared stub types (Doc / Query / VectorDB Protocol / ...)
│   ├── pit_01_hybrid_weights.py
│   ├── ...
│   └── pit_20_eval_framework.py
└── .github/workflows/verify.yml           # CI: AST syntax check on every push
```

## 每個 pit 檔案的形狀 · Anatomy of a pit file

```python
"""
坑 N · <Title>   [Bucket X: <name>]

現象 Symptom:   <one-line user-visible problem>
成因 Root cause: <one-line technical reason>
解法 Solution:  <one-line fix philosophy>
"""
from __future__ import annotations
# ... imports ...

# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def bad_xxx(...):
    """Why it fails."""
    ...

# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def good_xxx(...):
    """What the fix buys."""
    ...
```

Key-line comments are **bilingual** (繁中 / English) so readers from the
HIT 社群 and the broader international OSS community can both follow.

## 授權 · License

[MIT](LICENSE) — use freely in your own talks, blog posts, and production
code. Attribution appreciated but not required.

## 延伸閱讀 · Further reading

- RRF paper: Cormack, Clarke, Büttcher — *Reciprocal Rank Fusion outperforms Condorcet and Individual Rank Learning Methods* (SIGIR 2009)
- RAGAS: [docs.ragas.io](https://docs.ragas.io)
- Graphiti / bi-temporal KG: [getzep.com/graphiti](https://getzep.com/graphiti)
- Qdrant RRF (server-side): [qdrant.tech/documentation/concepts/hybrid-queries](https://qdrant.tech/documentation/concepts/hybrid-queries/)
