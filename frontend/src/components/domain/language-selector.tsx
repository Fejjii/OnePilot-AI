"use client";

import type { LanguagePreference } from "@/types/api";

export const LANGUAGE_OPTIONS: {
  value: LanguagePreference;
  label: string;
}[] = [
  { value: "auto", label: "Auto" },
  { value: "en", label: "English" },
  { value: "de", label: "German" },
  { value: "fr", label: "French" },
  { value: "es", label: "Spanish" },
];

export const LANGUAGE_LABELS: Record<string, string> = {
  en: "English",
  de: "German",
  fr: "French",
  es: "Spanish",
  auto: "Auto",
};

interface LanguageSelectorProps {
  value: LanguagePreference;
  onChange: (value: LanguagePreference) => void;
  disabled?: boolean;
  id?: string;
  className?: string;
  compact?: boolean;
}

/** Response-language preference for AI Workspace chat. */
export function LanguageSelector({
  value,
  onChange,
  disabled = false,
  id = "language-preference",
  className = "",
  compact = false,
}: LanguageSelectorProps) {
  return (
    <div
      className={`flex items-center gap-2 ${className}`}
      data-testid="language-selector"
    >
      <label
        htmlFor={id}
        className={
          compact
            ? "sr-only"
            : "shrink-0 text-[11px] font-medium text-slate-500"
        }
      >
        Response language
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value as LanguagePreference)}
        disabled={disabled}
        aria-label="Response language"
        className="min-w-[7.5rem] rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs font-medium text-slate-700 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-50"
      >
        {LANGUAGE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
