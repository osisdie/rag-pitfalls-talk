"use client";

/**
 * Three bouncing dots, staggered 150 ms apart. Pattern ported from
 * Agentory-CS — Tailwind's animate-bounce + inline animationDelay
 * instead of a motion library.
 */
export function TypingIndicator() {
  return (
    <div className="inline-flex items-center gap-1 text-slate-400">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="block w-2 h-2 rounded-full bg-brand animate-bounce"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
      <span className="ml-2 text-xs animate-pulse">思考中 · thinking</span>
    </div>
  );
}
