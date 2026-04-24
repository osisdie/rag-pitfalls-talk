"use client";

import { useState } from "react";

export function ResetDataButton({ scenarioId }: { scenarioId: string | null }) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      className="text-xs px-2 py-1 rounded border border-slate-700 text-slate-300 hover:border-brand disabled:opacity-50"
      disabled={busy || !scenarioId}
      title={scenarioId ? "re-seed this scenario" : "pick a scenario first"}
      onClick={async () => {
        if (!scenarioId) return;
        setBusy(true);
        try {
          await fetch(`/api/seed/${scenarioId}`, { method: "POST" });
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? "resetting…" : "reset data"}
    </button>
  );
}
