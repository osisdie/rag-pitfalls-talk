"use client";

export function Neo4jPanel() {
  // Stock Neo4j Browser URL served by Caddy at /neo4j/.
  // Default creds are injected via NEO4J_AUTH; the Browser UI prompts once.
  return (
    <section className="flex flex-col h-full border border-slate-800 rounded-lg bg-slate-950/40 overflow-hidden">
      <header className="px-3 py-2 border-b border-slate-800 text-sm text-slate-300">
        🕸 Neo4j (Graphiti)
      </header>
      <iframe
        src="/neo4j/browser/"
        className="flex-1 w-full bg-white"
        title="Neo4j Browser"
      />
    </section>
  );
}
