"use client";

import type { LayoutMode } from "../../types";

const OPTIONS: { value: LayoutMode; label: string; hint: string }[] = [
  { value: "grid", label: "▦ 2×2", hint: "four panels in a grid" },
  { value: "columns", label: "▥ Columns", hint: "chat+code left · DBs right" },
  { value: "tabs", label: "▤ Tabs", hint: "one panel at a time, switch via tabs" },
  { value: "focus", label: "◉ Focus", hint: "maximize a single panel" },
];

interface Props {
  value: LayoutMode;
  onChange: (m: LayoutMode) => void;
}

export function LayoutSelector({ value, onChange }: Props) {
  return (
    <div className="flex items-center gap-1 text-xs">
      <span className="text-slate-400 mr-1">layout</span>
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          title={opt.hint}
          onClick={() => onChange(opt.value)}
          className={`px-2 py-1 rounded border ${
            value === opt.value
              ? "bg-brand text-white border-brand"
              : "border-slate-700 text-slate-300 hover:border-brand"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
