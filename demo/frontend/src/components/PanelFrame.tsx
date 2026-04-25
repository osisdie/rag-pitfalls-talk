"use client";

import type { ReactNode } from "react";

export type PanelId = "chat" | "code" | "qdrant" | "neo4j";

interface Props {
  id: PanelId;
  collapsed: boolean;
  isFocused: boolean;
  onToggleCollapse: () => void;
  onMaximize: () => void;
  onMinimize: () => void;
  children: ReactNode;
}

/**
 * Panel shell — draws the corner buttons and clips children when collapsed.
 *
 * Collapsed behaviour: section shrinks to ~40 px and `overflow-hidden`
 * clips everything below the first 40 px of children. Each panel's own
 * `<header>` is already about that height, so the user sees the panel's
 * title bar with the corner buttons — making the panel findable and the
 * `▣` restore button clickable even when collapsed.
 *
 * Focus mode overrides collapse visually: when a panel is the focused
 * one, it always renders expanded so its content is readable. The
 * persisted collapsed state is preserved for when we return to grid.
 */
export function PanelFrame({
  id,
  collapsed,
  isFocused,
  onToggleCollapse,
  onMaximize,
  onMinimize,
  children,
}: Props) {
  const visuallyCollapsed = collapsed && !isFocused;
  return (
    <section
      data-panel-id={id}
      className={`flex flex-col border border-slate-800 rounded-lg bg-slate-950/40 ${
        visuallyCollapsed
          ? "max-h-10 min-h-10 shrink-0 overflow-hidden"
          : "flex-1 min-h-0 overflow-hidden"
      }`}
    >
      <div className="flex-1 min-h-0 flex flex-col relative">
        {/* Control cluster — always visible, even when collapsed, so the
            restore button is reachable. */}
        <div className="absolute top-1.5 right-2 z-10 flex items-center gap-1 text-xs">
          {!isFocused && (
            <button
              className="w-6 h-6 rounded text-slate-400 hover:text-brand hover:bg-slate-800 flex items-center justify-center"
              title={collapsed ? "expand" : "collapse"}
              onClick={onToggleCollapse}
            >
              {collapsed ? "▣" : "▢"}
            </button>
          )}
          <button
            className="w-6 h-6 rounded text-slate-400 hover:text-brand hover:bg-slate-800 flex items-center justify-center"
            title={isFocused ? "restore" : "maximize"}
            onClick={isFocused ? onMinimize : onMaximize}
          >
            {isFocused ? "⤡" : "⤢"}
          </button>
        </div>
        {children}
      </div>
    </section>
  );
}
