"use client";

import { useEffect, useMemo, useState } from "react";
import { ChatPanel } from "../components/ChatPanel/ChatPanel";
import { CodePanel } from "../components/CodePanel/CodePanel";
import { Neo4jPanel } from "../components/Neo4jPanel";
import { QdrantPanel } from "../components/QdrantPanel";
import { PanelFrame } from "../components/PanelFrame";
import { LLMConfigBar } from "../components/TopBar/LLMConfig";
import { LayoutSelector } from "../components/TopBar/LayoutSelector";
import { ResetDataButton } from "../components/TopBar/ResetDataButton";
import { ScenarioSelector } from "../components/TopBar/ScenarioSelector";
import { ThemeToggle } from "../components/TopBar/ThemeToggle";
import type { LayoutMode, PanelId, ScenarioMeta } from "../types";

const LS_LAYOUT = "rag-pitfalls.layout";
const LS_COLLAPSED = "rag-pitfalls.collapsed";

const PANELS: { id: PanelId; label: string }[] = [
  { id: "chat", label: "💬 Chat" },
  { id: "code", label: "📝 rag.py" },
  { id: "qdrant", label: "📐 Qdrant" },
  { id: "neo4j", label: "🕸 Neo4j" },
];

export default function Dashboard() {
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [prefill, setPrefill] = useState("");
  const [codeBump, setCodeBump] = useState(0);

  // Layout state, persisted in localStorage.
  const [layout, setLayout] = useState<LayoutMode>("grid");
  const [focused, setFocused] = useState<PanelId>("chat");
  const [activeTab, setActiveTab] = useState<PanelId>("chat");
  // Default: DB-iframe panels collapsed out of the way — they only matter
  // when the user explicitly wants to inspect Qdrant / Neo4j state.
  const [collapsed, setCollapsed] = useState<Record<PanelId, boolean>>({
    chat: false,
    code: false,
    qdrant: true,
    neo4j: true,
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const l = window.localStorage.getItem(LS_LAYOUT) as LayoutMode | null;
    if (l) setLayout(l);
    const c = window.localStorage.getItem(LS_COLLAPSED);
    if (c) {
      try {
        setCollapsed({
          chat: false, code: false, qdrant: true, neo4j: true,
          ...JSON.parse(c),
        });
      } catch {
        // ignore corrupt persisted state
      }
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(LS_LAYOUT, layout);
  }, [layout]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(LS_COLLAPSED, JSON.stringify(collapsed));
  }, [collapsed]);

  const onScenarioChange = (pid: string | null, meta: ScenarioMeta | null) => {
    setScenarioId(pid);
    setPrefill(meta?.probing_question ?? "");
    setCodeBump((n) => n + 1);
  };

  const toggleCollapse = (id: PanelId) =>
    setCollapsed((s) => ({ ...s, [id]: !s[id] }));

  const maximize = (id: PanelId) => {
    setLayout("focus");
    setFocused(id);
  };

  const minimizeFocus = () => setLayout("grid");

  // Each panel rendered once, then placed by current layout.
  const panelMap = useMemo(() => {
    const chat = (
      <ChatPanel
        scenarioId={scenarioId}
        prefill={prefill}
        onPrefillConsumed={() => setPrefill("")}
      />
    );
    const code = <CodePanel scenarioId={scenarioId} bumpKey={codeBump} />;
    const qdrant = <QdrantPanel />;
    const neo4j = <Neo4jPanel />;
    return { chat, code, qdrant, neo4j } as Record<PanelId, JSX.Element>;
  }, [scenarioId, prefill, codeBump]);

  const wrap = (id: PanelId) => (
    <PanelFrame
      id={id}
      collapsed={!!collapsed[id]}
      isFocused={layout === "focus" && focused === id}
      onToggleCollapse={() => toggleCollapse(id)}
      onMaximize={() => maximize(id)}
      onMinimize={minimizeFocus}
    >
      {panelMap[id]}
    </PanelFrame>
  );

  // Columns layout wants column-major filling (chat/code in left column,
  // qdrant/neo4j in right). The default 2×2 grid is row-major, so for
  // columns mode we pin each panel to an explicit (col, row) cell.
  const COLUMNS_PLACEMENT: Record<PanelId, { gridColumn: string; gridRow: string }> = {
    chat:   { gridColumn: "1", gridRow: "1" },
    code:   { gridColumn: "1", gridRow: "2" },
    qdrant: { gridColumn: "2", gridRow: "1" },
    neo4j:  { gridColumn: "2", gridRow: "2" },
  };

  const isPanelVisible = (id: PanelId) =>
    layout === "grid" ||
    layout === "columns" ||
    (layout === "tabs" && activeTab === id) ||
    (layout === "focus" && focused === id);

  const containerClass =
    layout === "grid" || layout === "columns"
      ? "flex-1 min-h-0 grid grid-cols-2 grid-rows-2 gap-3"
      : "flex-1 min-h-0 flex flex-col";

  return (
    <main className="h-screen flex flex-col p-3 gap-3 overflow-hidden">
      <header className="flex items-center gap-3 flex-wrap px-3 py-2 border border-slate-800 rounded-lg bg-slate-900/60 shrink-0">
        <h1 className="text-lg font-semibold text-slate-100 mr-2">
          RAG Pitfalls
        </h1>
        <ScenarioSelector value={scenarioId} onChange={onScenarioChange} />
        <ResetDataButton scenarioId={scenarioId} />
        <LayoutSelector value={layout} onChange={setLayout} />
        <ThemeToggle />
        <div className="ml-auto">
          <LLMConfigBar />
        </div>
      </header>

      {layout === "tabs" && (
        <div className="flex gap-1 text-sm shrink-0">
          {PANELS.map((p) => (
            <button
              key={p.id}
              onClick={() => setActiveTab(p.id)}
              className={`px-3 py-1.5 rounded-t border-b-2 ${
                activeTab === p.id
                  ? "bg-slate-900 text-slate-100 border-brand"
                  : "bg-slate-950 text-slate-400 border-transparent hover:text-slate-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}

      {/* Single stable container — all 4 panels stay mounted across layout
          changes so component state (chat history, code edits, scroll
          positions) survives toggling between grid/columns/tabs/focus. */}
      <div className={containerClass}>
        {PANELS.map((p) => {
          const visible = isPanelVisible(p.id);
          const wrapperClass = [
            "min-h-0 flex flex-col",
            visible ? "" : "hidden",
            layout === "tabs" || layout === "focus" ? "flex-1" : "",
          ]
            .filter(Boolean)
            .join(" ");
          const style = layout === "columns" ? COLUMNS_PLACEMENT[p.id] : undefined;
          return (
            <div key={p.id} className={wrapperClass} style={style}>
              {wrap(p.id)}
            </div>
          );
        })}
      </div>
    </main>
  );
}
