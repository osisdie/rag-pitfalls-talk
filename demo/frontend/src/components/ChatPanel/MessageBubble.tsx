"use client";

import ReactMarkdown from "react-markdown";
import type { ChatMessageClient } from "@/types";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { ImageThumbnails } from "./ImageThumbnails";
import { CitationPanel } from "./CitationPanel";
import { TypingIndicator } from "./TypingIndicator";

export function MessageBubble({ m }: { m: ChatMessageClient }) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-brand-dim text-white rounded-2xl rounded-tr-sm px-3 py-2 text-sm whitespace-pre-wrap">
          {m.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[95%] w-full bg-slate-900 rounded-2xl rounded-tl-sm text-sm border border-slate-800">
        <div className="p-3">
          {m.isStreaming && !m.content ? (
            <TypingIndicator />
          ) : (
            <ReactMarkdown>{m.content || ""}</ReactMarkdown>
          )}
          <ImageThumbnails urls={m.thumbnails ?? []} />
          {!m.isStreaming && (
            <div className="flex items-center gap-2 mt-2">
              {typeof m.confidence === "number" && (
                <ConfidenceBadge value={m.confidence} />
              )}
              {m.handoff && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-amber-900/60 text-amber-200 border border-amber-700">
                  handoff queued
                </span>
              )}
            </div>
          )}
        </div>
        <CitationPanel
          citations={m.citations ?? []}
          timeline={m.timeline}
          ragVersionId={m.rag_version_id}
        />
      </div>
    </div>
  );
}
