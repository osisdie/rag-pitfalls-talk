"use client";

import { useState } from "react";
import type { CitationDetail } from "@/types";

/**
 * Per-citation card. Collapsed by default — shows source name, type icon,
 * freshness, relevance bar; expanded reveals full chunk text and edge fact.
 * Pattern ported from ai-rag-graphiti.
 */
export function CitationCard({ c, index }: { c: CitationDetail; index: number }) {
  const [open, setOpen] = useState(false);
  const preview = c.edge_fact || c.chunk_text || "";
  const tone =
    c.freshness === "current"
      ? "text-emerald-300"
      : c.freshness === "stale"
      ? "text-amber-300"
      : c.freshness === "expired"
      ? "text-rose-300"
      : "text-slate-400";

  return (
    <div className="border border-slate-700 rounded-lg bg-slate-900/60 p-3 text-sm">
      <button
        className="w-full text-left flex items-start gap-2"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-xs text-slate-500 w-6 shrink-0">[{index + 1}]</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium">{c.source_name}</span>
            <span className="text-[10px] uppercase text-slate-500">
              {c.source_type}
            </span>
            {c.freshness && (
              <span className={`text-[10px] ${tone}`}>{c.freshness}</span>
            )}
            <span className="text-[10px] text-slate-500 ml-auto">
              score {c.relevance_score.toFixed(3)}
            </span>
          </div>
          <p className="text-slate-300 mt-1 line-clamp-2 break-words">{preview}</p>
        </div>
      </button>
      {open && (
        <div className="mt-2 pl-8 text-slate-300 space-y-2">
          {c.edge_fact && (
            <div>
              <div className="text-[10px] uppercase text-slate-500">edge fact</div>
              <div className="whitespace-pre-wrap">{c.edge_fact}</div>
            </div>
          )}
          {c.chunk_text && (
            <div>
              <div className="text-[10px] uppercase text-slate-500">chunk</div>
              <div className="whitespace-pre-wrap">{c.chunk_text}</div>
            </div>
          )}
          {c.source_url && (
            <a
              href={c.source_url}
              target="_blank"
              rel="noreferrer"
              className="text-brand underline text-xs"
            >
              開啟原始資料 · open source
            </a>
          )}
        </div>
      )}
    </div>
  );
}
