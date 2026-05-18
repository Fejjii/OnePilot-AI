import { Activity } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/badge";

export function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  let tone: BadgeTone = "muted";
  let label = "Low confidence";
  if (value >= 0.75) {
    tone = "success";
    label = "High confidence";
  } else if (value >= 0.5) {
    tone = "info";
    label = "Medium confidence";
  } else if (value > 0) {
    tone = "warning";
    label = "Low confidence";
  }
  return (
    <Badge tone={tone} icon={<Activity className="h-3 w-3" />}>
      {label} · {pct}%
    </Badge>
  );
}
