"use client";

export function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const tone =
    value >= 0.7
      ? "bg-emerald-900/60 text-emerald-200 border-emerald-700"
      : value >= 0.4
      ? "bg-amber-900/60 text-amber-200 border-amber-700"
      : "bg-rose-900/60 text-rose-200 border-rose-700";
  return (
    <span
      className={`text-[10px] px-2 py-0.5 rounded border ${tone}`}
      title="RAG confidence: max citation relevance score"
    >
      conf {pct}%
    </span>
  );
}
