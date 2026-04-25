"use client";

import { useEffect, useState } from "react";
import { activateScenario, listScenarios } from "../../lib/api";
import type { ScenarioMeta } from "../../types";

interface Props {
  value: string | null;
  onChange: (pitId: string | null, meta: ScenarioMeta | null) => void;
}

export function ScenarioSelector({ value, onChange }: Props) {
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listScenarios().then(setScenarios).catch(() => setScenarios([]));
  }, []);

  return (
    <div className="flex items-center gap-2 text-sm">
      <label className="text-slate-400">scenario</label>
      <select
        className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm"
        value={value ?? ""}
        disabled={busy}
        onChange={async (e) => {
          const pid = e.target.value || null;
          if (!pid) {
            onChange(null, null);
            return;
          }
          setBusy(true);
          try {
            const meta = await activateScenario(pid);
            onChange(pid, meta);
          } catch (err) {
            console.warn("activate failed", err);
          }
          setBusy(false);
        }}
      >
        <option value="">(none)</option>
        {scenarios.map((s) => (
          <option value={s.pit_id} key={s.pit_id}>
            Bucket {s.bucket} · {s.pit_id} · {s.title}
          </option>
        ))}
      </select>
      {busy && <span className="text-xs text-slate-500">activating…</span>}
    </div>
  );
}
