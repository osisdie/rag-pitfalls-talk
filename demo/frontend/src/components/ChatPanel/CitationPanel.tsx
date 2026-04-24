"use client";

import type { CitationDetail, TimelineEvent } from "@/types";
import { CitationCard } from "./CitationCard";

interface Props {
  citations: CitationDetail[];
  timeline?: TimelineEvent[];
  ragVersionId?: number | null;
}

export function CitationPanel({ citations, timeline, ragVersionId }: Props) {
  if (!citations.length && !timeline?.length) return null;
  return (
    <div className="border-t border-slate-800 p-3 space-y-3 bg-slate-950/60">
      {citations.length > 0 && (
        <div>
          <div className="text-xs text-slate-500 mb-1">
            來源 · sources ({citations.length})
          </div>
          <div className="space-y-2">
            {citations.map((c, i) => (
              <CitationCard c={c} index={i} key={i} />
            ))}
          </div>
        </div>
      )}
      {timeline && timeline.length > 0 && (
        <div>
          <div className="text-xs text-slate-500 mb-1">
            timeline {ragVersionId != null && `· answered by v${ragVersionId}`}
          </div>
          <div className="flex gap-1 flex-wrap text-[10px]">
            {timeline.map((e, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded bg-slate-800 text-slate-300"
                title={JSON.stringify(e.meta)}
              >
                {e.stage} {e.took_ms.toFixed(0)}ms
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
