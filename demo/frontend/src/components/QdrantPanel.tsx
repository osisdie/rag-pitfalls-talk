"use client";

import { useEffect, useState } from "react";

export function QdrantPanel() {
  // Qdrant dashboard served at :8080 root (unauth). Cross-origin but no
  // auth-challenge → Chromium iframe-auth issue doesn't apply.
  const [src, setSrc] = useState<string>("");
  useEffect(() => {
    if (typeof window === "undefined") return;
    setSrc(`http://${window.location.hostname}:8080/dashboard`);
  }, []);
  return (
    <section className="flex flex-col h-full border border-slate-800 rounded-lg bg-slate-950/40 overflow-hidden">
      <header className="px-3 py-2 border-b border-slate-800 text-sm text-slate-300 flex items-center gap-2">
        <span>📐 Qdrant</span>
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
      </header>
      {src && (
        <iframe src={src} className="flex-1 w-full bg-white" title="Qdrant Dashboard" />
      )}
    </section>
  );
}
