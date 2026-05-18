import { Sparkles } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import type { PlanCode } from "@/types/api";
import { titleize } from "@/lib/utils";

const PLAN_TONES: Record<PlanCode, BadgeTone> = {
  free: "muted",
  pro: "primary",
  team: "info",
  business: "success",
};

export function PlanBadge({ plan }: { plan: PlanCode | string }) {
  const tone = (PLAN_TONES as Record<string, BadgeTone>)[plan] ?? "neutral";
  return (
    <Badge tone={tone} icon={<Sparkles className="h-3 w-3" />}>
      {titleize(plan)} plan
    </Badge>
  );
}
