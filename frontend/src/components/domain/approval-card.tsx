import { Clock } from "lucide-react";
import type { ApprovalResponse } from "@/types/api";
import { StatusBadge } from "./status-badge";
import { RiskBadge } from "./risk-badge";
import { formatRelativeTime, titleize } from "@/lib/utils";

interface ApprovalCardProps {
  approval: ApprovalResponse;
  onClick?: () => void;
  active?: boolean;
}

export function ApprovalCard({ approval, onClick, active }: ApprovalCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "block w-full rounded-lg border bg-white p-3 text-left transition-colors hover:border-indigo-300 hover:bg-indigo-50/30 " +
        (active
          ? "border-indigo-400 ring-2 ring-indigo-200"
          : "border-slate-200")
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold text-slate-900">{approval.title}</p>
        <StatusBadge status={approval.status} />
        <RiskBadge level={approval.risk_level} />
      </div>
      <p className="mt-1 text-xs text-slate-500">
        {titleize(approval.action_type)}
      </p>
      {approval.description && (
        <p className="mt-1 line-clamp-2 text-xs text-slate-600">
          {approval.description}
        </p>
      )}
      <div className="mt-2 flex items-center gap-1 text-[11px] text-slate-400">
        <Clock className="h-3 w-3" />
        {formatRelativeTime(approval.created_at)}
      </div>
    </button>
  );
}
