import { cn } from "@/lib/utils";
import { type ReactNode } from "react";

type Tone =
  | "neutral"
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "muted";

const TONES: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-700 border-slate-200",
  primary: "bg-indigo-50 text-indigo-700 border-indigo-200",
  success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warning: "bg-amber-50 text-amber-800 border-amber-200",
  danger: "bg-rose-50 text-rose-700 border-rose-200",
  info: "bg-sky-50 text-sky-700 border-sky-200",
  muted: "bg-slate-50 text-slate-500 border-slate-200",
};

interface BadgeProps {
  tone?: Tone;
  className?: string;
  children: ReactNode;
  icon?: ReactNode;
}

export function Badge({ tone = "neutral", className, children, icon }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        TONES[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}

export type BadgeTone = Tone;
