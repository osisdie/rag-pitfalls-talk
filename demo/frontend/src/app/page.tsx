"use client";

import { useState } from "react";
import { ChatPanel } from "@/components/ChatPanel/ChatPanel";
import { CodePanel } from "@/components/CodePanel/CodePanel";
import { Neo4jPanel } from "@/components/Neo4jPanel";
import { QdrantPanel } from "@/components/QdrantPanel";
import { LLMConfigBar } from "@/components/TopBar/LLMConfig";
import { ResetDataButton } from "@/components/TopBar/ResetDataButton";
import { ScenarioSelector } from "@/components/TopBar/ScenarioSelector";
import type { ScenarioMeta } from "@/types";

export default function Dashboard() {
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [prefill, setPrefill] = useState("");
  const [codeBump, setCodeBump] = useState(0);

  const onScenarioChange = (pid: string | null, meta: ScenarioMeta | null) => {
    setScenarioId(pid);
    setPrefill(meta?.probing_question ?? "");
    setCodeBump((n) => n + 1);
  };

  return (
    <main className="min-h-screen flex flex-col p-3 gap-3">
      <header className="flex items-center gap-4 flex-wrap px-3 py-2 border border-slate-800 rounded-lg bg-slate-900/60">
        <h1 className="text-lg font-semibold text-slate-100">
          RAG Pitfalls · Live Demo
        </h1>
        <ScenarioSelector value={scenarioId} onChange={onScenarioChange} />
        <ResetDataButton scenarioId={scenarioId} />
        <div className="ml-auto">
          <LLMConfigBar />
        </div>
      </header>

      <div className="flex-1 grid grid-cols-2 grid-rows-2 gap-3 min-h-0">
        <div className="min-h-0">
          <ChatPanel
            scenarioId={scenarioId}
            prefill={prefill}
            onPrefillConsumed={() => setPrefill("")}
          />
        </div>
        <div className="min-h-0">
          <CodePanel scenarioId={scenarioId} bumpKey={codeBump} />
        </div>
        <div className="min-h-0">
          <QdrantPanel />
        </div>
        <div className="min-h-0">
          <Neo4jPanel />
        </div>
      </div>
    </main>
  );
}
