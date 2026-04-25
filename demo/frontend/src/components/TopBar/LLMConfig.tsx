"use client";

import { useEffect, useState } from "react";
import { fetchLLMConfig, saveLLMConfig } from "../../lib/api";
import type { LLMConfig as LLMConfigType } from "../../types";

export function LLMConfigBar() {
  const [cfg, setCfg] = useState<LLMConfigType>({
    model: "gemini-2.5-flash-lite",
    temperature: 0.3,
    top_p: 0.95,
    web_search: false,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchLLMConfig().then(setCfg).catch(() => {});
  }, []);

  const save = async (next: LLMConfigType) => {
    setSaving(true);
    try {
      const saved = await saveLLMConfig(next);
      setCfg(saved);
    } finally {
      setSaving(false);
    }
  };

  const webSearchSupported = !cfg.model.endsWith("-flash-lite");

  return (
    <div className="flex items-center gap-3 text-sm flex-wrap">
      <label className="text-slate-400">model</label>
      <select
        className="bg-slate-900 border border-slate-700 rounded px-2 py-1"
        value={cfg.model}
        onChange={(e) => save({ ...cfg, model: e.target.value as LLMConfigType["model"] })}
      >
        <option value="gemini-2.5-flash-lite">gemini-2.5-flash-lite</option>
        <option value="gemini-2.5-flash">gemini-2.5-flash</option>
        <option value="gemini-3.1-flash-lite">gemini-3.1-flash-lite</option>
        <option value="gemini-3.1-flash">gemini-3.1-flash</option>
      </select>

      <label className="text-slate-400">T</label>
      <input
        type="number"
        min={0}
        max={2}
        step={0.1}
        value={cfg.temperature}
        className="w-16 bg-slate-900 border border-slate-700 rounded px-1 py-1"
        onChange={(e) => save({ ...cfg, temperature: Number(e.target.value) })}
      />

      <label className="text-slate-400">top_p</label>
      <input
        type="number"
        min={0}
        max={1}
        step={0.05}
        value={cfg.top_p}
        className="w-16 bg-slate-900 border border-slate-700 rounded px-1 py-1"
        onChange={(e) => save({ ...cfg, top_p: Number(e.target.value) })}
      />

      <label
        className="text-slate-400 flex items-center gap-1"
        title={
          webSearchSupported
            ? "Gemini Google Search grounding"
            : "Web Search only on non-lite models; switch model first"
        }
      >
        <input
          type="checkbox"
          checked={cfg.web_search && webSearchSupported}
          disabled={!webSearchSupported}
          onChange={(e) => save({ ...cfg, web_search: e.target.checked })}
        />
        web search
      </label>

      {saving && <span className="text-xs text-slate-500">saving…</span>}
    </div>
  );
}
