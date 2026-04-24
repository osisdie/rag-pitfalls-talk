"use client";

interface Props {
  sessionId: string | null;
  onNewSession: () => void;
}

export function SessionControls({ sessionId, onNewSession }: Props) {
  return (
    <div className="flex items-center gap-2 text-xs text-slate-500 px-3 py-2 border-t border-slate-800">
      <span>session: </span>
      <code className="text-slate-400">{sessionId?.slice(0, 8) ?? "none"}</code>
      <button
        className="ml-auto text-brand hover:underline"
        onClick={onNewSession}
      >
        clear history · 新 session
      </button>
    </div>
  );
}
