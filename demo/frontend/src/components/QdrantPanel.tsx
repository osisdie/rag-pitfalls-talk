"use client";

export function QdrantPanel() {
  return (
    <section className="flex flex-col h-full border border-slate-800 rounded-lg bg-slate-950/40 overflow-hidden">
      <header className="px-3 py-2 border-b border-slate-800 text-sm text-slate-300">
        📐 Qdrant
      </header>
      <iframe
        src="/qdrant/dashboard"
        className="flex-1 w-full bg-white"
        title="Qdrant Dashboard"
      />
    </section>
  );
}
