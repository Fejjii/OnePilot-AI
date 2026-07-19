"use client";

import { FlaskConical, ShieldCheck, Sparkles } from "lucide-react";
import { PromptSuggestions } from "@/components/domain/prompt-suggestions";

interface WorkspaceEmptyStateProps {
  /** True while an authenticated one-click demo session is active. */
  isDemo: boolean;
  /** Submits the selected suggested prompt through the normal chat flow. */
  onPrompt: (prompt: string) => void;
  disabled?: boolean;
}

/**
 * First-run guidance shown in the chat column before any messages exist.
 * Explains what OnePilot can do, that demo actions are simulated (demo mode
 * only), that consequential actions stay behind human approval, and offers
 * clickable starter prompts.
 */
export function WorkspaceEmptyState({
  isDemo,
  onPrompt,
  disabled = false,
}: WorkspaceEmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 px-4 py-8 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 text-white">
        <Sparkles className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="max-w-md space-y-2">
        <h3 className="text-sm font-semibold text-slate-900">
          Ask OnePilot about this business
        </h3>
        <p className="text-xs leading-relaxed text-slate-600">
          OnePilot answers questions grounded in the knowledge base, analyzes
          leads and business activity, and prepares emails and meeting
          proposals with full citations and tool traces.
        </p>
        <p className="flex items-center justify-center gap-1.5 text-xs text-slate-600">
          <ShieldCheck
            className="h-3.5 w-3.5 shrink-0 text-emerald-600"
            aria-hidden="true"
          />
          Consequential actions always wait for human approval.
        </p>
        {isDemo && (
          <p className="flex items-center justify-center gap-1.5 text-xs text-amber-800">
            <FlaskConical
              className="h-3.5 w-3.5 shrink-0"
              aria-hidden="true"
            />
            Demo actions are simulated — no real emails or calendar events are
            ever created.
          </p>
        )}
      </div>
      <div className="w-full max-w-lg space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Try one of these
        </p>
        <PromptSuggestions onSelect={onPrompt} disabled={disabled} />
      </div>
    </div>
  );
}
