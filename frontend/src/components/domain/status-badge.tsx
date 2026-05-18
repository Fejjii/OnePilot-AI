import { Badge, type BadgeTone } from "@/components/ui/badge";
import { titleize } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  /**
   * Optional override of tone lookup; useful when the same status string has
   * different meaning depending on context.
   */
  tone?: BadgeTone;
}

const STATUS_TONES: Record<string, BadgeTone> = {
  // approvals
  pending: "warning",
  approved: "success",
  rejected: "danger",
  needs_more_info: "info",
  // leads
  new: "info",
  qualified: "primary",
  contacted: "info",
  proposal: "primary",
  won: "success",
  lost: "danger",
  // documents
  indexed: "success",
  processing: "info",
  failed: "danger",
  ready: "success",
  // subscriptions
  active: "success",
  trialing: "primary",
  past_due: "warning",
  cancelled: "muted",
};

export function StatusBadge({ status, tone }: StatusBadgeProps) {
  const finalTone = tone ?? STATUS_TONES[status.toLowerCase()] ?? "neutral";
  return <Badge tone={finalTone}>{titleize(status)}</Badge>;
}
