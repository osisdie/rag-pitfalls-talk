"use client";

import { useEffect, useState } from "react";

export function Neo4jPanel() {
  // Neo4j Browser at :8081 root. Bolt is on :7687 direct.
  // IMPORTANT: The Database user for Neo4j is `neo4j`, NOT `admin`
  // (that's the Caddy basic-auth user for the main page).
  const [src, setSrc] = useState<string>("");
  const [host, setHost] = useState<string>("");
  useEffect(() => {
    if (typeof window === "undefined") return;
    const h = window.location.hostname;
    setHost(h);
    setSrc(`http://${h}:8081/browser/`);
  }, []);
  return (
    <section className="flex flex-col h-full border border-slate-800 rounded-lg bg-slate-950/40 overflow-hidden">
      <header className="px-3 py-2 border-b border-slate-800 text-sm text-slate-300 flex flex-col gap-1">
        <div className="flex items-center gap-2 flex-wrap pr-16">
          <span>🕸 Neo4j (Graphiti)</span>
          {src && (
            <a
              href={src}
              target="_blank"
              rel="noreferrer"
              className="ml-auto text-xs text-brand hover:underline"
            >
              open in new tab
            </a>
          )}
        </div>
        {host && (
          <div className="text-[10px] text-slate-500 font-mono">
            URL <code className="bg-slate-900 px-1 rounded">bolt://{host}:7687</code>
            {" · "}User <code className="bg-slate-900 px-1 rounded text-emerald-300">neo4j</code>
            <span className="text-amber-400">{" (not admin!)"}</span>
          </div>
        )}
      </header>
      {src && (
        <iframe src={src} className="flex-1 w-full bg-white" title="Neo4j Browser" />
      )}
    </section>
  );
}
