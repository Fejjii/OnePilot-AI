import type { LucideIcon } from "lucide-react";
import { type ReactNode } from "react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center">
      {Icon && (
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-500">
          <Icon className="h-5 w-5" />
        </div>
      )}
      <div>
        <p className="text-sm font-semibold text-slate-900">{title}</p>
        {description && (
          <p className="mt-1 max-w-md text-xs text-slate-500">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}
