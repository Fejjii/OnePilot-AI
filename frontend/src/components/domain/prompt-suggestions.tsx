"use client";

import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  BookOpen,
  CalendarClock,
  CalendarDays,
  Mail,
  ShieldCheck,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface PromptSuggestion {
  /** Short chip label shown to the user. */
  label: string;
  /** Full prompt submitted to the agent when the chip is activated. */
  prompt: string;
  icon: LucideIcon;
}

/**
 * Starter prompts for first-time reviewers. Each chip exercises a distinct
 * capability against seeded demo data. Email drafting stays behind human
 * approval; Gmail/Calendar side effects are simulated in the public demo.
 */
export const PROMPT_SUGGESTIONS: readonly PromptSuggestion[] = [
  {
    label: "Summarize business activity",
    prompt:
      "Summarize our recent business activity across leads, approvals, and conversations.",
    icon: BarChart3,
  },
  {
    label: "Review pending approvals",
    prompt: "Which approvals are currently pending and what do they cover?",
    icon: ShieldCheck,
  },
  {
    label: "Search the knowledge base",
    prompt: "What does our knowledge base say about the escalation policy?",
    icon: BookOpen,
  },
  {
    label: "Analyze leads",
    prompt: "Analyze our current leads and highlight the most promising ones.",
    icon: Users,
  },
  {
    label: "Draft a follow-up email",
    prompt:
      "Draft a follow-up email to our most promising lead about scheduling an intro call.",
    icon: Mail,
  },
  {
    label: "Show this week's meetings",
    prompt: "Show my meetings this week.",
    icon: CalendarDays,
  },
  {
    label: "Find open meeting times",
    prompt:
      "Check my calendar availability for a 30-minute intro call this week.",
    icon: CalendarClock,
  },
];

interface PromptSuggestionsProps {
  /** Called with the full prompt text when a chip is activated. */
  onSelect: (prompt: string) => void;
  disabled?: boolean;
  className?: string;
}

/**
 * Accessible chip row of suggested starter prompts. Chips are native buttons,
 * so keyboard activation (Tab + Enter/Space) and screen-reader semantics work
 * without extra wiring; activating a chip submits the prompt immediately.
 */
export function PromptSuggestions({
  onSelect,
  disabled = false,
  className,
}: PromptSuggestionsProps) {
  return (
    <ul
      aria-label="Suggested prompts"
      className={cn(
        "flex flex-wrap justify-center gap-2 max-sm:justify-stretch",
        className,
      )}
    >
      {PROMPT_SUGGESTIONS.map(({ label, prompt, icon: Icon }) => (
        <li key={label} className="max-sm:min-w-0">
          <button
            type="button"
            disabled={disabled}
            title={prompt}
            onClick={() => onSelect(prompt)}
            className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Icon className="h-3.5 w-3.5 shrink-0 text-indigo-500" aria-hidden="true" />
            <span className="truncate">{label}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
