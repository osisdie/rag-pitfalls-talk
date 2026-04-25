"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import {
  applyFix,
  getCurrentRag,
  listVersions,
  revertToVersion,
  saveRagCode,
} from "../../lib/api";
import type { RagVersion } from "../../types";

const MonacoEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.default), {
  ssr: false,
});

interface Props {
  scenarioId: string | null;
  bumpKey: number; // increment to force re-fetch after scenario activate / apply-fix
}

export function CodePanel({ scenarioId, bumpKey }: Props) {
  const [source, setSource] = useState<string>("");
  const [versionId, setVersionId] = useState<number | null>(null);
  const [freeEdit, setFreeEdit] = useState(false);
  const [versions, setVersions] = useState<RagVersion[]>([]);
  const [banner, setBanner] = useState<{ ok: boolean; msg: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [hostSize, setHostSize] = useState<{ w: number; h: number } | null>(null);
  const editorRef = useRef<any>(null);
  const editorHostRef = useRef<HTMLDivElement>(null);

  // Pass Monaco explicit pixel dimensions instead of "100%". The
  // @monaco-editor/react wrapper sets its own `<section style="height:
  // 100%">` which fails to resolve through this project's deep
  // `flex-1 min-h-0` chain — Monaco then latches onto a 5px stale
  // measurement and never recovers (Tabs layout: tab switch leaves
  // rag.py rendered as a sliver). Measuring the host with a
  // ResizeObserver and feeding numbers to Monaco bypasses the
  // percentage-resolution bug entirely.
  useEffect(() => {
    const host = editorHostRef.current;
    if (!host || typeof ResizeObserver === "undefined") return;
    const sync = () => {
      const r = host.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) return;
      setHostSize((prev) =>
        prev && prev.w === r.width && prev.h === r.height ? prev : { w: r.width, h: r.height },
      );
    };
    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(host);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const curr = await getCurrentRag();
        setSource(curr.source ?? "");
        setVersionId(curr.version_id);
      } catch {}
      if (scenarioId) {
        try {
          setVersions(await listVersions(scenarioId));
        } catch {
          setVersions([]);
        }
      } else {
        setVersions([]);
      }
    })();
  }, [scenarioId, bumpKey]);

  const onApplyFix = async () => {
    if (!scenarioId) return;
    setBusy(true);
    const res = await applyFix();
    setBanner(
      res.ok
        ? { ok: true, msg: `applied · v${res.version_id}` }
        : { ok: false, msg: `failed: ${res.error ?? "unknown"}` },
    );
    setBusy(false);
    const curr = await getCurrentRag();
    setSource(curr.source ?? "");
    setVersionId(curr.version_id);
    try {
      setVersions(await listVersions(scenarioId));
    } catch {}
  };

  const onSave = async () => {
    setBusy(true);
    const res = await saveRagCode(source, "manual edit");
    setBanner(
      res.ok
        ? { ok: true, msg: `saved · v${res.version_id}` }
        : { ok: false, msg: `failed: ${res.error ?? "unknown"}` },
    );
    setBusy(false);
    try {
      setVersions(await listVersions(scenarioId ?? undefined));
    } catch {}
  };

  const onRevert = async (vid: number) => {
    setBusy(true);
    const res = await revertToVersion(vid);
    setBanner(
      res.ok
        ? { ok: true, msg: `reverted to v${vid}` }
        : { ok: false, msg: `failed: ${res.error ?? "unknown"}` },
    );
    setBusy(false);
    const curr = await getCurrentRag();
    setSource(curr.source ?? "");
    setVersionId(curr.version_id);
  };

  return (
    <section className="flex flex-col flex-1 min-h-0 border border-slate-800 rounded-lg bg-slate-950/40">
      <header className="px-3 py-2 border-b border-slate-800 text-sm flex items-center gap-2 text-slate-300">
        <span>📝 rag.py</span>
        {versionId != null && (
          <span className="text-xs text-slate-500">· v{versionId}</span>
        )}
        <label className="ml-auto flex items-center gap-1 text-xs">
          <input
            type="checkbox"
            checked={freeEdit}
            onChange={(e) => setFreeEdit(e.target.checked)}
          />
          Free edit
        </label>
        {scenarioId && !freeEdit && (
          <button
            className="text-xs px-2 py-1 rounded bg-brand hover:bg-brand-dim text-white disabled:opacity-50"
            disabled={busy}
            onClick={onApplyFix}
          >
            Apply Fix
          </button>
        )}
        {freeEdit && (
          <button
            className="text-xs px-2 py-1 rounded bg-brand hover:bg-brand-dim text-white disabled:opacity-50"
            disabled={busy}
            onClick={onSave}
          >
            Save &amp; Reload
          </button>
        )}
      </header>

      {banner && (
        <div
          className={`text-xs px-3 py-1 ${
            banner.ok ? "bg-emerald-900/50 text-emerald-200" : "bg-rose-900/50 text-rose-200"
          }`}
          onClick={() => setBanner(null)}
        >
          {banner.msg} <span className="opacity-50">(click to dismiss)</span>
        </div>
      )}

      <div className="flex-1 min-h-0" ref={editorHostRef}>
        {hostSize && (
          <MonacoEditor
            width={hostSize.w}
            height={hostSize.h}
            defaultLanguage="python"
            theme={
              typeof document !== "undefined" &&
              document.documentElement.getAttribute("data-theme") === "light"
                ? "vs-light"
                : "vs-dark"
            }
            value={source}
            onChange={(v) => setSource(v ?? "")}
            onMount={(editor) => {
              editorRef.current = editor;
            }}
            options={{
              readOnly: !freeEdit,
              fontSize: 12,
              minimap: { enabled: false },
              lineNumbers: "on",
              wordWrap: "on",
            }}
          />
        )}
      </div>

      {versions.length > 0 && (
        <details className="text-xs border-t border-slate-800">
          <summary className="px-3 py-2 cursor-pointer text-slate-400">
            版本 · versions ({versions.length})
          </summary>
          <ul className="max-h-32 overflow-y-auto">
            {versions.map((v) => (
              <li
                key={v.id}
                className="flex items-center gap-2 px-3 py-1 hover:bg-slate-900"
              >
                <code className="text-slate-500 w-10">v{v.id}</code>
                <span className="text-slate-300 flex-1 truncate">{v.label}</span>
                <button
                  className="text-brand hover:underline"
                  onClick={() => onRevert(v.id)}
                  disabled={busy}
                >
                  revert
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
