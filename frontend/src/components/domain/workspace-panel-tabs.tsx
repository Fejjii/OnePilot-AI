"use client";

import { BookOpen, History, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

export type WorkspacePanelId = "chat" | "history" | "details";

interface WorkspacePanelTabsProps {
  active: WorkspacePanelId;
  onChange: (panel: WorkspacePanelId) => void;
  /** Soft indicator that response details are available. */
  detailsAvailable?: boolean;
  conversationCount?: number;
}

const TABS: ReadonlyArray<{
  id: WorkspacePanelId;
  label: string;
  icon: typeof MessageSquare;
}> = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "history", label: "History", icon: History },
  { id: "details", label: "Details", icon: BookOpen },
];

/**
 * Segmented control for switching among workspace panels on narrow viewports.
 * Desktop keeps the three-column layout and does not render this control.
 */
export function WorkspacePanelTabs({
  active,
  onChange,
  detailsAvailable = false,
  conversationCount,
}: WorkspacePanelTabsProps) {
  function focusAdjacent(delta: number) {
    const index = TABS.findIndex((tab) => tab.id === active);
    const next = TABS[(index + delta + TABS.length) % TABS.length];
    onChange(next.id);
  }

  return (
    <div
      role="tablist"
      aria-label="Workspace panels"
      className="grid grid-cols-3 gap-1 rounded-xl border border-slate-200 bg-slate-100/80 p-1 lg:hidden"
      onKeyDown={(event) => {
        if (event.key === "ArrowRight") {
          event.preventDefault();
          focusAdjacent(1);
        } else if (event.key === "ArrowLeft") {
          event.preventDefault();
          focusAdjacent(-1);
        } else if (event.key === "Home") {
          event.preventDefault();
          onChange(TABS[0].id);
        } else if (event.key === "End") {
          event.preventDefault();
          onChange(TABS[TABS.length - 1].id);
        }
      }}
    >
      {TABS.map((tab) => {
        const selected = active === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`workspace-tab-${tab.id}`}
            aria-selected={selected}
            aria-controls={`workspace-panel-${tab.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.id)}
            className={cn(
              "relative flex min-h-[44px] items-center justify-center gap-1.5 rounded-lg px-2 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
              selected
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900",
            )}
          >
            <tab.icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span>{tab.label}</span>
            {tab.id === "details" && detailsAvailable && !selected && (
              <span
                aria-hidden="true"
                className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-indigo-500"
              />
            )}
            {tab.id === "history" &&
              typeof conversationCount === "number" &&
              conversationCount > 0 && (
                <span className="rounded-full bg-slate-200 px-1.5 text-[10px] font-semibold text-slate-600">
                  {conversationCount > 99 ? "99+" : conversationCount}
                </span>
              )}
          </button>
        );
      })}
    </div>
  );
}
