"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import {
  applyFix,
  getCurrentRag,
  listScenarios,
  listVersions,
  revertToVersion,
  saveRagCode,
} from "../../lib/api";
import type { RagVersion, ScenarioMeta } from "../../types";

const MonacoEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.default), {
  ssr: false,
});

interface Props {
  scenarioId: string | null;
  bumpKey: number; // increment to force re-fetch after scenario activate / apply-fix
}

const INSIGHT_BY_PIT: Record<
  string,
  {
    technique: string;
    purpose: string;
    expected: string;
    benefit: string;
  }
> = {
  pit_01_hybrid_weights: {
    technique: "Reciprocal Rank Fusion (RRF), scale-free hybrid retrieval",
    purpose: "避免 dense cosine 與 BM25 原始分數直接加權，造成某一路分數尺度支配排序。",
    expected: "退件問題應優先命中申請書/健康告知相關 FAQ，而不是泛客服資訊。",
    benefit: "混合檢索排序更穩定，換模型或調 BM25 時比較不會讓結果大幅飄移。",
  },
  pit_02_rrf_confidence: {
    technique: "Two-stage scoring: RRF 排序 + cosine confidence re-score",
    purpose: "把 ranking score 與 confidence 分離，避免把 RRF 分數誤當成答案信心。",
    expected: "答案仍可召回繳費方式，但信心標示降為中等，讓使用者知道相關性有限。",
    benefit: "降低假高信心回覆，讓 UI/客服 handoff 可以用更可信的門檻決策。",
  },
  pit_03_rerank_tiered: {
    technique: "Tiered re-ranking, cheap-first then precise re-rank",
    purpose: "先用低成本檢索縮小候選，再對 top-k 做更精準排序。",
    expected: "把真正相關的條款推到前面，降低粗召回排序誤差。",
    benefit: "在延遲與品質之間取得可控平衡。",
  },
  pit_04_ingest_expansion: {
    technique: "Ingestion-time query/document expansion",
    purpose: "在寫入索引時補上同義詞與背景詞，避免短查詢漏召回。",
    expected: "使用者用不同說法提問時仍能命中同一份知識。",
    benefit: "召回率提升，且查詢端不必每次做昂貴改寫。",
  },
  pit_05_temporal_parser: {
    technique: "Relative-time parser + recency-filtered fallback tiers",
    purpose: "把『最近、今年、目前』這類相對時間轉成可查詢的時間條件。",
    expected: "最近申報期限從舊公告切到 2026 相關公告。",
    benefit: "時間敏感知識不再只靠語意相似度，能避開舊資料誤命中。",
  },
  pit_06_bitemporal_kg: {
    technique: "Bi-temporal knowledge graph + Cypher as-of query",
    purpose: "用 graph relation 的 valid_at/invalid_at 表示歷史有效版本。",
    expected: "問 2 年前合約時，從最新 60 天規則切回當時有效的 30 天規則。",
    benefit: "能回答『當時』而不是『現在』的事實，是 Graph 場景的核心價值。",
  },
  pit_07_content_hash_versioning: {
    technique: "Content-hash versioning + retrieval-side deduplication",
    purpose: "同來源多版本文件命中時，避免新舊內容混答。",
    expected: "理賠天數只引用最新版本，不再混入過期規則。",
    benefit: "降低版本衝突造成的錯答，資料更新後也更容易追蹤來源。",
  },
  pit_08_retention_sweep: {
    technique: "Retention policy sweep",
    purpose: "把過期或政策上不應再回答的資料從可檢索集合中移除。",
    expected: "問題不再命中已超過保留期限的內容。",
    benefit: "降低陳舊資料與合規風險。",
  },
  pit_09_intent_router: {
    technique: "Intent routing before retrieval",
    purpose: "先判斷查詢意圖，再選擇 FAQ、規則、客服等不同檢索路徑。",
    expected: "同一句話可依意圖走到正確 collection 或回答策略。",
    benefit: "減少跨領域誤召回，讓系統行為更可解釋。",
  },
  pit_10_entity_disambiguation: {
    technique: "Dense + BM25 sparse hybrid with entity bonus and dense floor",
    purpose: "讓短人名查詢優先命中員工實體，同時避免純詞彙誤擊。",
    expected: "『誰是張主任』從泛職稱定義切到風險管理部員工卡。",
    benefit: "短 query 的命名實體查詢更穩，還能顯示人物縮圖等結構化資訊。",
  },
  pit_11_domain_glossary: {
    technique: "Domain glossary alias expansion + RRF",
    purpose: "把非正式術語展開成 canonical term 與縮寫，例如遞延負債 -> DTL。",
    expected: "原本找不到的領域詞，套用 fix 後能命中 DTL 文件。",
    benefit: "降低專業縮寫、俗稱、正式名稱不一致造成的漏召回。",
  },
  pit_12_handoff_threshold: {
    technique: "Confidence threshold + human handoff queue",
    purpose: "低信心或個案型問題不要硬答，改轉接專人。",
    expected: "理賠金額估算不再編數字，而是明確提示轉接。",
    benefit: "降低高風險場景的幻覺與責任風險。",
  },
  pit_13_layered_guardrails: {
    technique: "Layered guardrails around answer generation",
    purpose: "把安全規則與業務限制放進回答流程，而不是只靠模型自覺。",
    expected: "敏感或不該承諾的請求被明確拒答或改寫。",
    benefit: "把風險控制變成可測、可維護的工程邏輯。",
  },
  pit_14_regression_gate: {
    technique: "Regression gate over known bad/golden cases",
    purpose: "新 prompt 或檢索策略上線前先跑既有題庫。",
    expected: "會破壞既有答案的改動被擋下來。",
    benefit: "防止 demo 或產品在修一題時弄壞另一題。",
  },
  pit_15_cache_query: {
    technique: "Query-keyed response cache with scenario/version scoped key",
    purpose: "快取要綁 query/情境/版本，而不是回傳一個硬編答案。",
    expected: "營業時間從 stale hardcoded bubble 切到 09:00-18:00。",
    benefit: "保留快取效能，同時避免資料更新後繼續回舊答案。",
  },
  pit_16_three_layer_cache: {
    technique: "Three-layer cache: memory, retrieval, response",
    purpose: "區分不同快取層的生命週期與失效條件。",
    expected: "命中快取時仍維持正確來源與版本語意。",
    benefit: "降低延遲與成本，同時減少 stale cache 的事故面。",
  },
  pit_17_memory_tiers: {
    technique: "Hot/cold/older memory tiers with summarization fallback",
    purpose: "長對話中保留重要舊資訊，不只看最近幾輪。",
    expected: "能回憶早先提供的保單編號 P12345678。",
    benefit: "改善長會話客服體驗，避免使用者重複提供資料。",
  },
  pit_18_multi_collection: {
    technique: "Multi-collection retrieval and routing",
    purpose: "把不同資料域分 collection 管理，依問題選擇或合併查詢。",
    expected: "跨 FAQ/entity/rule_doc 的問題能命中正確資料域。",
    benefit: "資料治理更清楚，召回策略更容易針對不同資料調整。",
  },
  pit_19_image_materialization: {
    technique: "Image/materialized asset citations",
    purpose: "把圖片或視覺資料作為可引用結果，而不是只回文字。",
    expected: "答案能帶出相關 image thumbnail 或 materialized asset。",
    benefit: "讓多模態/文件截圖型知識更容易被使用者驗證。",
  },
  pit_20_eval_framework: {
    technique: "Golden benchmark + RAGAS-style metric reporting",
    purpose: "把人工 vibe check 改成可重複的評估框架。",
    expected: "跑 benchmark 時輸出指標、診斷與 gate decision。",
    benefit: "讓 20 個修正是否真的變好可以被量化，而非只靠感覺。",
  },
};

export function CodePanel({ scenarioId, bumpKey }: Props) {
  const [source, setSource] = useState<string>("");
  const [versionId, setVersionId] = useState<number | null>(null);
  const [freeEdit, setFreeEdit] = useState(false);
  const [versions, setVersions] = useState<RagVersion[]>([]);
  const [scenario, setScenario] = useState<ScenarioMeta | null>(null);
  const [banner, setBanner] = useState<{ ok: boolean; msg: string } | null>(null);
  const [lastDiff, setLastDiff] = useState<{
    from: number;
    to: number;
    text: string;
  } | null>(null);
  const [insightOpen, setInsightOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [hostSize, setHostSize] = useState<{ w: number; h: number } | null>(null);
  const editorRef = useRef<any>(null);
  const editorHostRef = useRef<HTMLDivElement>(null);

  // Pass Monaco explicit pixel dimensions instead of "100%". The
  // @monaco-editor/react wrapper sets its own `<section style="height:
  // 100%">` which fails to resolve through this project's deep
  // `flex-1 min-h-0` chain — Monaco then latches onto a 5px stale
  // measurement and never recovers (Tabs layout: tab switch leaves
  // rag.py rendered as a sliver). Measuring the host with a
  // ResizeObserver and feeding numbers to Monaco bypasses the
  // percentage-resolution bug entirely.
  useEffect(() => {
    const host = editorHostRef.current;
    if (!host || typeof ResizeObserver === "undefined") return;
    const sync = () => {
      const r = host.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) return;
      setHostSize((prev) =>
        prev && prev.w === r.width && prev.h === r.height ? prev : { w: r.width, h: r.height },
      );
    };
    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(host);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const curr = await getCurrentRag();
        setSource(curr.source ?? "");
        setVersionId(curr.version_id);
      } catch {}
      if (scenarioId) {
        try {
          setVersions(await listVersions(scenarioId));
        } catch {
          setVersions([]);
        }
        try {
          const all = await listScenarios();
          setScenario(all.find((s) => s.pit_id === scenarioId) ?? null);
        } catch {
          setScenario(null);
        }
      } else {
        setVersions([]);
        setScenario(null);
      }
      setLastDiff(null);
      setInsightOpen(false);
    })();
  }, [scenarioId, bumpKey]);

  const buildQuickDiff = (before: string, after: string) => {
    const a = before.split("\n");
    const b = after.split("\n");
    const max = Math.max(a.length, b.length);
    const out: string[] = [];
    for (let i = 0; i < max; i += 1) {
      const left = a[i] ?? "";
      const right = b[i] ?? "";
      if (left === right) continue;
      if (left !== "") out.push(`- ${left}`);
      if (right !== "") out.push(`+ ${right}`);
      if (out.length >= 240) {
        out.push("... (diff truncated)");
        break;
      }
    }
    return out.join("\n") || "(no textual diff)";
  };

  const buildInsight = () => {
    if (!lastDiff) return null;
    const added = lastDiff.text.split("\n").filter((line) => line.startsWith("+ ")).length;
    const removed = lastDiff.text.split("\n").filter((line) => line.startsWith("- ")).length;
    const canned = scenarioId ? INSIGHT_BY_PIT[scenarioId] : undefined;
    return {
      caseTitle: scenario?.title ?? scenarioId ?? "custom rag.py",
      coreProgram: `live rag.py v${lastDiff.from} -> v${lastDiff.to} (${added} additions, ${removed} removals)`,
      technique: canned?.technique ?? "Scenario-specific retrieval / generation patch",
      purpose: canned?.purpose ?? "Replace the active before implementation with the corrected after implementation.",
      expected:
        canned?.expected ??
        `Before marker: ${scenario?.expected_before_substr ?? "n/a"}; after marker: ${
          scenario?.expected_after_substr ?? "n/a"
        }.`,
      benefit:
        canned?.benefit ??
        "Makes the demo behavior easier to explain and gives the audience a concise reason for the code change.",
    };
  };

  const onApplyFix = async () => {
    if (!scenarioId) return;
    const prevVersionId = versionId;
    const prevSource = source;
    setLastDiff(null);
    setBusy(true);
    const res = await applyFix();
    setBanner(
      res.ok
        ? { ok: true, msg: `applied · v${res.version_id}` }
        : { ok: false, msg: `failed: ${res.error ?? "unknown"}` },
    );
    setBusy(false);
    const curr = await getCurrentRag();
    setSource(curr.source ?? "");
    setVersionId(curr.version_id);
    try {
      const nextVersions = await listVersions(scenarioId);
      setVersions(nextVersions);
      if (res.ok && res.version_id && prevVersionId != null) {
        const newer = nextVersions.find((v) => v.id === res.version_id);
        const older = nextVersions.find((v) => v.id === prevVersionId);
        const before = older?.source ?? prevSource;
        const after = newer?.source ?? curr.source ?? "";
        setLastDiff({
          from: prevVersionId,
          to: res.version_id,
          text: buildQuickDiff(before, after),
        });
        setInsightOpen(true);
      }
    } catch {}
  };

  const onSave = async () => {
    setBusy(true);
    const res = await saveRagCode(source, "manual edit");
    setBanner(
      res.ok
        ? { ok: true, msg: `saved · v${res.version_id}` }
        : { ok: false, msg: `failed: ${res.error ?? "unknown"}` },
    );
    setBusy(false);
    try {
      setVersions(await listVersions(scenarioId ?? undefined));
    } catch {}
  };

  const onRevert = async (vid: number) => {
    setBusy(true);
    const res = await revertToVersion(vid);
    setBanner(
      res.ok
        ? { ok: true, msg: `reverted to v${vid}` }
        : { ok: false, msg: `failed: ${res.error ?? "unknown"}` },
    );
    setBusy(false);
    const curr = await getCurrentRag();
    setSource(curr.source ?? "");
    setVersionId(curr.version_id);
  };

  return (
    <section className="flex flex-col flex-1 min-h-0 border border-slate-800 rounded-lg bg-slate-950/40">
      <header className="px-3 py-2 border-b border-slate-800 text-sm flex items-center gap-2 text-slate-300">
        <span>📝 rag.py</span>
        {versionId != null && (
          <span className="text-xs text-slate-500">· v{versionId}</span>
        )}
        <label className="ml-auto flex items-center gap-1 text-xs">
          <input
            type="checkbox"
            checked={freeEdit}
            onChange={(e) => setFreeEdit(e.target.checked)}
          />
          Free edit
        </label>
        {scenarioId && !freeEdit && (
          <button
            className="text-xs px-2 py-1 rounded bg-brand hover:bg-brand-dim text-white disabled:opacity-50"
            disabled={busy}
            onClick={onApplyFix}
          >
            Apply Fix
          </button>
        )}
        {freeEdit && (
          <button
            className="text-xs px-2 py-1 rounded bg-brand hover:bg-brand-dim text-white disabled:opacity-50"
            disabled={busy}
            onClick={onSave}
          >
            Save &amp; Reload
          </button>
        )}
      </header>

      {banner && (
        <div
          className={`text-xs px-3 py-1 ${
            banner.ok ? "bg-emerald-900/50 text-emerald-200" : "bg-rose-900/50 text-rose-200"
          }`}
          onClick={() => setBanner(null)}
        >
          {banner.msg} <span className="opacity-50">(click to dismiss)</span>
        </div>
      )}

      {lastDiff && (
        <details className="border-b border-slate-800">
          <summary className="px-3 py-2 text-xs cursor-pointer text-slate-300 flex items-center gap-2">
            <span>apply-fix diff · v{lastDiff.from} → v{lastDiff.to}</span>
            <button
              type="button"
              className="ml-auto px-2 py-0.5 rounded-full border border-amber-400/40 bg-amber-400/10 text-amber-200 hover:bg-amber-400/20"
              onClick={(e) => {
                e.preventDefault();
                setInsightOpen((open) => !open);
              }}
            >
              💡 Insight
            </button>
          </summary>
          {insightOpen && (() => {
            const insight = buildInsight();
            if (!insight) return null;
            return (
              <div className="m-3 p-3 rounded-lg border border-amber-400/25 bg-amber-950/20 text-xs text-slate-200">
                <div className="flex items-center gap-2 mb-2 text-amber-200 font-semibold">
                  <span>💡 修改 insight</span>
                  <span className="text-[10px] text-amber-200/60">Apply Fix 摘要</span>
                </div>
                <dl className="grid grid-cols-[88px_1fr] gap-x-3 gap-y-1.5">
                  <dt className="text-slate-500">Case</dt>
                  <dd>{insight.caseTitle}</dd>
                  <dt className="text-slate-500">核心程式</dt>
                  <dd><code>{insight.coreProgram}</code></dd>
                  <dt className="text-slate-500">技術</dt>
                  <dd>{insight.technique}</dd>
                  <dt className="text-slate-500">目的/預期</dt>
                  <dd>{insight.purpose} {insight.expected}</dd>
                  <dt className="text-slate-500">效益</dt>
                  <dd>{insight.benefit}</dd>
                </dl>
              </div>
            );
          })()}
          <pre className="text-[11px] leading-4 p-3 overflow-auto max-h-48 bg-slate-950 text-slate-300 border-t border-slate-800">
            {lastDiff.text.split("\n").map((line, i) => (
              <span
                key={i}
                className={
                  line.startsWith("+ ")
                    ? "block text-emerald-300"
                    : line.startsWith("- ")
                      ? "block text-rose-300"
                      : "block text-slate-400"
                }
              >
                {line}
              </span>
            ))}
          </pre>
        </details>
      )}

      <div className="flex-1 min-h-0" ref={editorHostRef}>
        {hostSize && (
          <MonacoEditor
            width={hostSize.w}
            height={hostSize.h}
            defaultLanguage="python"
            theme={
              typeof document !== "undefined" &&
              document.documentElement.getAttribute("data-theme") === "light"
                ? "vs-light"
                : "vs-dark"
            }
            value={source}
            onChange={(v) => setSource(v ?? "")}
            onMount={(editor) => {
              editorRef.current = editor;
            }}
            options={{
              readOnly: !freeEdit,
              fontSize: 12,
              minimap: { enabled: false },
              lineNumbers: "on",
              wordWrap: "on",
            }}
          />
        )}
      </div>

      {versions.length > 0 && (
        <details className="text-xs border-t border-slate-800">
          <summary className="px-3 py-2 cursor-pointer text-slate-400">
            版本 · versions ({versions.length})
          </summary>
          <ul className="max-h-32 overflow-y-auto">
            {versions.map((v) => (
              <li
                key={v.id}
                className="flex items-center gap-2 px-3 py-1 hover:bg-slate-900"
              >
                <code className="text-slate-500 w-10">v{v.id}</code>
                <span className="text-slate-300 flex-1 truncate">{v.label}</span>
                <button
                  className="text-brand hover:underline"
                  onClick={() => onRevert(v.id)}
                  disabled={busy}
                >
                  revert
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
