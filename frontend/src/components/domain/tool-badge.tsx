import {
  BookOpen,
  Calendar,
  Globe,
  Mail,
  MessageSquare,
  Users,
  BarChart3,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { toolBadgeLabel } from "@/lib/execution-trace";

const TOOL_META: Record<string, { tone: BadgeTone; icon: LucideIcon }> = {
  Knowledge: { tone: "info", icon: BookOpen },
  Email: { tone: "info", icon: Mail },
  Calendar: { tone: "info", icon: Calendar },
  CRM: { tone: "primary", icon: Users },
  Web: { tone: "info", icon: Globe },
  Insights: { tone: "primary", icon: BarChart3 },
  Chat: { tone: "neutral", icon: MessageSquare },
  Tool: { tone: "muted", icon: Wrench },
};

interface ToolBadgeProps {
  toolName?: string;
  label?: string | null;
}

export function ToolBadge({ toolName = "", label }: ToolBadgeProps) {
  const resolved = toolBadgeLabel(toolName, label);
  const meta = TOOL_META[resolved] ?? TOOL_META.Tool;
  const Icon = meta.icon;
  return (
    <Badge tone={meta.tone} icon={<Icon className="h-3 w-3" />}>
      {resolved}
    </Badge>
  );
}
