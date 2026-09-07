import { Activity, BookOpen } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/badge";

const WEAK_EVIDENCE_MAX = 0.6;

export function groundedSourceLabel(citationCount: number): string {
  if (citationCount === 1) {
    return "Grounded in 1 source";
  }
  return `Grounded in ${citationCount} sources`;
}

export function ConfidenceBadge({
  value,
  weakEvidence = false,
  citationCount,
  showRawScore = false,
}: {
  value: number;
  weakEvidence?: boolean;
  citationCount?: number;
  showRawScore?: boolean;
}) {
  const effective = weakEvidence ? Math.min(value, WEAK_EVIDENCE_MAX) : value;
  const pct = Math.round(effective * 100);

  if (!showRawScore && !weakEvidence && (citationCount ?? 0) > 0) {
    return (
      <Badge tone="success" icon={<BookOpen className="h-3 w-3" />}>
        {groundedSourceLabel(citationCount ?? 0)}
      </Badge>
    );
  }

  if (!showRawScore && weakEvidence) {
    return (
      <Badge tone="warning" icon={<Activity className="h-3 w-3" />}>
        Weak evidence
      </Badge>
    );
  }

  let tone: BadgeTone = "muted";
  let label = "Low confidence";
  if (weakEvidence) {
    tone = "warning";
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
