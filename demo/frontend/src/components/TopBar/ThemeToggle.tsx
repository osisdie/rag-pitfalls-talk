"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";
const KEY = "rag-pitfalls.theme";

function applyTheme(t: Theme) {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", t);
}

export function ThemeToggle({
  onChange,
}: {
  onChange?: (t: Theme) => void;
}) {
  const [theme, setTheme] = useState<Theme>("dark");

  // Initialise from localStorage; fall back to OS preference.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = window.localStorage.getItem(KEY) as Theme | null;
    const initial: Theme =
      saved ??
      (window.matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark");
    setTheme(initial);
    applyTheme(initial);
    onChange?.(initial);
  }, [onChange]);

  const flip = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
    if (typeof window !== "undefined") window.localStorage.setItem(KEY, next);
    onChange?.(next);
  };

  return (
    <button
      onClick={flip}
      className="text-xs px-2 py-1 rounded border border-slate-700 text-slate-300 hover:border-brand"
      title={`switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {theme === "dark" ? "🌙 dark" : "☀ light"}
    </button>
  );
}
