import { ShieldAlert, ShieldCheck } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { titleize } from "@/lib/utils";

const RISK_TONES: Record<string, BadgeTone> = {
  low: "success",
  medium: "warning",
  high: "danger",
  critical: "danger",
};

export function RiskBadge({ level }: { level: string }) {
  const tone = RISK_TONES[level.toLowerCase()] ?? "neutral";
  const icon =
    level === "low" ? (
      <ShieldCheck className="h-3 w-3" />
    ) : (
      <ShieldAlert className="h-3 w-3" />
    );
  return (
    <Badge tone={tone} icon={icon}>
      {titleize(level)} risk
    </Badge>
  );
}
