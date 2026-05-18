import { cn, formatNumber, titleize } from "@/lib/utils";
import type { UsageQuota } from "@/types/api";

interface UsageProgressProps {
  quota: UsageQuota;
}

const UNLIMITED = -1;

export function UsageProgress({ quota }: UsageProgressProps) {
  const unlimited = quota.limit === UNLIMITED || quota.limit === 0;
  const ratio = unlimited
    ? 0
    : Math.min(1, quota.used / Math.max(1, quota.limit));
  const pct = Math.round(ratio * 100);

  let barColor = "bg-emerald-500";
  if (ratio >= 0.9) barColor = "bg-rose-500";
  else if (ratio >= 0.7) barColor = "bg-amber-500";

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-slate-900">
          {titleize(quota.feature)}
        </span>
        <span className="text-slate-500">
          {unlimited
            ? `${formatNumber(quota.used)} used`
            : `${formatNumber(quota.used)} / ${formatNumber(quota.limit)}`}
        </span>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className={cn("h-full rounded-full transition-all", barColor)}
          style={{ width: unlimited ? "8%" : `${pct}%` }}
        />
      </div>
      {!unlimited && (
        <p className="mt-1 text-[11px] text-slate-500">
          {pct}% of plan limit · {formatNumber(quota.remaining)} remaining
        </p>
      )}
      {unlimited && (
        <p className="mt-1 text-[11px] text-slate-500">Unlimited on this plan</p>
      )}
    </div>
  );
}
