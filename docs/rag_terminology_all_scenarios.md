# RAG Terminology Table (All Scenarios)

This is the unified terminology table across all 20 scenarios in this demo.

| 中文名詞 | English | 名詞解釋 | 參考資料 |
|---|---|---|---|
| 檢索增強生成 | Retrieval-Augmented Generation (RAG) | 先檢索外部知識，再把檢索結果注入提示詞給 LLM 生成答案。 | `demo/backend/app/core/rag.py.default`, `demo/backend/app/api/chat.py` |
| 密集檢索 | Dense Retrieval | 以向量相似度進行語意檢索，通常對語意改寫更穩健。 | `demo/backend/app/core/embed.py`, 各 `pit_*/rag_before.py` 的 `using="dense"` |
| 稀疏檢索 | Sparse Retrieval | 以詞項匹配為核心的檢索，對短查詢與關鍵字更敏感。 | `demo/backend/app/scenarios/pit_01_hybrid_weights/rag_after.py`, `pit_10_entity_disambiguation/rag_after.py` |
| BM25 | BM25 | 經典稀疏排序函式，使用詞頻與逆文件頻率。 | `Document(text=query, model="Qdrant/bm25")` 於多個 `rag_after.py` |
| 混合檢索 | Hybrid Retrieval | 同時跑 dense 與 sparse，融合後排序，平衡語意與詞彙訊號。 | `pit_01_hybrid_weights/rag_after.py`, `pit_02_rrf_confidence/rag_after.py` |
| 倒數排名融合 | Reciprocal Rank Fusion (RRF) | 用 `1/(K+rank)` 融合多路排名，避免分數尺度不一致問題。 | `pit_01_hybrid_weights/rag_after.py`, `pit_02_rrf_confidence/rag_after.py` |
| 加權融合陷阱 | Weighted-blend trap | 直接相加 dense/BM25 分數常因量綱不同導致錯排。 | `demo/backend/app/scenarios/pit_01_hybrid_weights/scenario.py` |
| 信心分數 | Confidence Score | 用於估計答案可信度，應與實際相似度或校準策略對齊。 | `demo/frontend/src/components/ChatPanel/ConfidenceBadge.tsx`, `demo/backend/app/models/schemas.py` |
| 兩階段信心評估 | Two-stage confidence scoring | 先決定排序，再用 cosine 等相似度重新評估信心，避免把 RRF 當信心。 | `pit_02_rrf_confidence/rag_after.py` |
| 餘弦相似度 | Cosine Similarity | 衡量 query 與文件向量夾角的相似度，常用於 confidence re-score。 | `pit_02_rrf_confidence/rag_after.py` |
| 重排序 | Re-ranking | 先粗召回，再以第二階段模型/規則重排 top-k。 | `demo/backend/app/scenarios/pit_03_rerank_tiered/rag_after.py` |
| 分層重排 | Tiered Re-rank | 依成本/精度分層重排（例如先便宜再昂貴），控制延遲與品質。 | `demo/backend/app/scenarios/pit_03_rerank_tiered/scenario.py`, `pit_03_rerank_tiered/rag_after.py` |
| 查詢擴展 | Query Expansion | 將使用者問題擴展成同義詞/背景詞以提高召回。 | `demo/backend/app/scenarios/pit_04_ingest_expansion/rag_after.py` |
| Ingest 擴展 | Ingest-time Expansion | 在寫入索引時加入別名、同義詞、補充欄位，降低查詢端負擔。 | `demo/backend/app/scenarios/pit_04_ingest_expansion/scenario.py` |
| 時間語意解析 | Temporal Parsing | 將「最近/去年/某月」等自然語言轉為可檢索時間條件。 | `demo/backend/app/scenarios/pit_05_temporal_parser/rag_after.py` |
| 雙時間知識圖譜 | Bi-temporal KG | 同時管理事件生效時間（valid time）與寫入時間（transaction time）。 | `demo/backend/app/scenarios/pit_06_bitemporal_kg/scenario.py`, `pit_06_bitemporal_kg/rag_after.py` |
| 圖查詢 | Graph Query / Cypher | 以圖資料庫語言查關係與時態條件，再回補檢索引用。 | `pit_06_bitemporal_kg/rag_after.py`, `demo/backend/app/core/graph.py` |
| 內容雜湊版本 | Content-hash Versioning | 對同 source 的內容做版本識別，避免新舊內容混答。 | `demo/backend/app/scenarios/pit_07_content_hash_versioning/scenario.py`, `pit_07_content_hash_versioning/rag_after.py` |
| 去重 | Deduplication | 在檢索尾端或索引端移除重複來源，降低衝突證據。 | `pit_07_content_hash_versioning/rag_after.py` |
| 保留策略清理 | Retention Sweep | 依資料時效/策略清理舊資料，避免陳舊內容持續命中。 | `demo/backend/app/scenarios/pit_08_retention_sweep/rag_after.py` |
| 意圖路由 | Intent Router | 先判斷問題意圖，再選擇對應檢索路徑或資料集合。 | `demo/backend/app/scenarios/pit_09_intent_router/rag_after.py` |
| 實體消歧 | Entity Disambiguation | 區分「通用詞義」與「特定人物/實體」，避免答非所問。 | `demo/backend/app/scenarios/pit_10_entity_disambiguation/scenario.py`, `pit_10_entity_disambiguation/rag_after.py` |
| 實體加分 | Entity Bonus | 對實體類候選加分，強化短查詢的人名/組織命中。 | `pit_10_entity_disambiguation/rag_after.py` |
| 密集分數地板 | Dense Floor | 對 sparse 命中加一道 dense 門檻，防止純詞彙誤命中。 | `pit_10_entity_disambiguation/rag_after.py` |
| 領域詞彙表 | Domain Glossary | 維護術語標準寫法與別名，降低領域縮寫/俗稱造成的漏召回。 | `demo/backend/app/scenarios/pit_11_domain_glossary/scenario.py`, `pit_11_domain_glossary/rag_after.py` |
| 人工接手 | Human Handoff | 低信心問題轉人工隊列處理，避免高風險誤答。 | `demo/backend/app/scenarios/pit_12_handoff_threshold/rag_after.py` |
| 閾值閘門 | Threshold Gate | 當信心低於門檻時觸發特定流程（如 handoff）。 | `pit_12_handoff_threshold/rag_after.py` |
| 分層護欄 | Layered Guardrails | 以多層規則/檢查限制模型輸出風險（安全、合規、範圍）。 | `demo/backend/app/scenarios/pit_13_layered_guardrails/rag_after.py` |
| 回歸門檻 | Regression Gate | 以 golden set 與指標差異判斷是否允許變更上線。 | `demo/backend/app/scenarios/pit_14_regression_gate/rag_after.py` |
| Golden Set | Golden Set | 固定測例集合，用於比較改版前後品質。 | `pit_14_regression_gate/rag_after.py`, `pit_20_eval_framework/rag_after.py` |
| 查詢快取 | Query Cache | 對重複問題快取答案，降低延遲與成本。 | `demo/backend/app/scenarios/pit_15_cache_query/rag_after.py` |
| TTL | Time To Live (TTL) | 快取有效期限，過期後需重算。 | `pit_15_cache_query/rag_after.py`, `pit_16_three_layer_cache/rag_after.py` |
| 三層快取 | Three-layer Cache | 將 embedding / response / image 分層快取並分離失效策略。 | `demo/backend/app/scenarios/pit_16_three_layer_cache/scenario.py`, `pit_16_three_layer_cache/rag_after.py` |
| 記憶分層 | Memory Tiers | 依時間與重要性分短期/長期記憶，平衡上下文長度與成本。 | `demo/backend/app/scenarios/pit_17_memory_tiers/rag_after.py` |
| 多集合路由 | Multi-collection Routing | 依意圖把檢索導向不同 Qdrant collection，而非單一桶。 | `demo/backend/app/scenarios/pit_18_multi_collection/rag_after.py` |
| 影像物化 | Image Materialization | 回答同時附帶圖像證據/縮圖，提升實體辨識與可驗證性。 | `demo/backend/app/scenarios/pit_19_image_materialization/rag_after.py` |
| 評估框架 | Evaluation Framework | 將檢索/生成品質指標化、可重複比較並可納入 CI gate。 | `demo/backend/app/scenarios/pit_20_eval_framework/rag_after.py` |
| RAGAS（近似） | RAGAS (approx.) | 以 RAGAS 形狀的指標近似評估，支援 demo 與教學。 | `pit_20_eval_framework/rag_after.py` |
| 引用 | Citation | 將答案對應到來源片段與 metadata，支援可追溯性。 | `demo/backend/app/models/schemas.py`, `demo/frontend/src/components/ChatPanel/CitationCard.tsx` |
| 時間線量測 | Timeline Measurements | 記錄各 stage 耗時（如 search_dense、search_bm25、llm_ttft）。 | `demo/backend/app/core/tracing.py`, `demo/backend/app/api/chat.py` |
| 首 token 時間 | Time To First Token (TTFT) | 從發送 LLM 請求到第一個 token 的延遲。 | `demo/backend/app/api/chat.py` (`llm_ttft`) |
| 串流輸出 | Streaming Generation | LLM 逐 token 回傳內容，改善體感等待。 | `demo/backend/app/api/chat.py` 的 SSE `token` / `done` event |

## Scope

- Covers all scenarios under `demo/backend/app/scenarios/pit_*`.
- Focuses on terms that appear repeatedly in code, docs, and demo flow.
- References point to implementation entry files for quick lookup.
