import { Activity } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/badge";

const WEAK_EVIDENCE_MAX = 0.6;

export function ConfidenceBadge({
  value,
  weakEvidence = false,
}: {
  value: number;
  weakEvidence?: boolean;
}) {
  const effective = weakEvidence ? Math.min(value, WEAK_EVIDENCE_MAX) : value;
  const pct = Math.round(effective * 100);
  let tone: BadgeTone = "muted";
  let label = "Low confidence";
  if (weakEvidence) {
    tone = effective >= 0.5 ? "warning" : "warning";
    label = effective >= 0.5 ? "Medium confidence" : "Low confidence";
  } else if (effective >= 0.75) {
    tone = "success";
    label = "High confidence";
  } else if (effective >= 0.5) {
    tone = "info";
    label = "Medium confidence";
  } else if (effective > 0) {
    tone = "warning";
    label = "Low confidence";
  }
  return (
    <Badge tone={tone} icon={<Activity className="h-3 w-3" />}>
      {label} · {pct}%
    </Badge>
  );
}
