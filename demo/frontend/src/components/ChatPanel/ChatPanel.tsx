"use client";

import { useCallback, useEffect, useState } from "react";
import { deleteSession, newSession } from "../../lib/api";
import { postChatStream } from "../../lib/sse";
import type { ChatMessageClient, ChatResponse } from "../../types";
import { MessageList } from "./MessageList";
import { SessionControls } from "./SessionControls";

interface Props {
  scenarioId: string | null;
  prefill: string;
  onPrefillConsumed: () => void;
}

export function ChatPanel({ scenarioId, prefill, onPrefillConsumed }: Props) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageClient[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const sid = await newSession(scenarioId ?? undefined);
        setSessionId(sid);
      } catch (e) {
        console.warn("newSession failed", e);
      }
    })();
  }, [scenarioId]);

  useEffect(() => {
    if (prefill) {
      setInput(prefill);
      onPrefillConsumed();
    }
  }, [prefill, onPrefillConsumed]);

  const send = useCallback(async () => {
    if (!input.trim() || busy) return;
    const text = input.trim();
    const userMsg: ChatMessageClient = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text,
    };
    const botId = `b-${Date.now()}`;
    const botMsg: ChatMessageClient = {
      id: botId,
      role: "assistant",
      content: "",
      isStreaming: true,
    };
    setMessages((prev) => [...prev, userMsg, botMsg]);
    setInput("");
    setBusy(true);

    await postChatStream(
      { message: text, session_id: sessionId, scenario_id: scenarioId },
      {
        onToken: (t) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === botId ? { ...m, content: (m.content || "") + t } : m)),
          );
        },
        onDone: (final: ChatResponse) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botId
                ? {
                    ...m,
                    content: final.answer || m.content || "",
                    citations: final.citations,
                    confidence: final.confidence,
                    thumbnails: final.thumbnails,
                    handoff: final.handoff,
                    timeline: final.timeline,
                    rag_version_id: final.rag_version_id,
                    isStreaming: false,
                  }
                : m,
            ),
          );
          setSessionId(final.session_id);
        },
        onError: (err) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botId
                ? {
                    ...m,
                    content: (m.content || "") + `\n\n[error] ${err}`,
                    isStreaming: false,
                  }
                : m,
            ),
          );
        },
      },
    );
    setBusy(false);
  }, [input, busy, sessionId, scenarioId]);

  const onNewSession = useCallback(async () => {
    if (sessionId) await deleteSession(sessionId);
    setMessages([]);
    try {
      const sid = await newSession(scenarioId ?? undefined);
      setSessionId(sid);
    } catch (e) {
      console.warn(e);
    }
  }, [sessionId, scenarioId]);

  return (
    <section className="flex flex-col flex-1 min-h-0 border border-slate-800 rounded-lg bg-slate-950/40">
      <header className="px-3 py-2 border-b border-slate-800 text-sm font-medium text-slate-300 flex items-center">
        <span>💬 Chat</span>
        {scenarioId && (
          <span className="ml-2 text-xs text-slate-500">· {scenarioId}</span>
        )}
      </header>
      <MessageList messages={messages} />
      <SessionControls sessionId={sessionId} onNewSession={onNewSession} />
      <form
        className="flex gap-2 p-3 border-t border-slate-800"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <textarea
          className="flex-1 resize-none bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm focus:outline-none focus:border-brand"
          rows={2}
          placeholder="問點什麼 · ask anything…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button
          className="px-4 rounded bg-brand hover:bg-brand-dim text-white text-sm disabled:opacity-50"
          disabled={busy}
        >
          送出
        </button>
      </form>
    </section>
  );
}
