import {
  Sparkles,
  BookOpen,
  Users,
  Mail,
  FileText,
  Wrench,
  AlertCircle,
  HelpCircle,
  Calendar,
  Globe,
  BarChart3,
  GitBranch,
  type LucideIcon,
} from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import type { Intent } from "@/types/api";
import { titleize } from "@/lib/utils";

const INTENT_META: Record<
  Intent | string,
  { tone: BadgeTone; icon: LucideIcon; label: string }
> = {
  general_assistant: { tone: "primary", icon: Sparkles, label: "General" },
  knowledge_search: { tone: "info", icon: BookOpen, label: "Knowledge" },
  web_search: { tone: "info", icon: Globe, label: "Web search" },
  web_and_knowledge: { tone: "info", icon: BookOpen, label: "Web + KB" },
  lead_support: { tone: "primary", icon: Users, label: "Lead" },
  email_drafting: { tone: "info", icon: Mail, label: "Email" },
  calendar_availability: { tone: "info", icon: Calendar, label: "Calendar" },
  calendar_scheduling: { tone: "info", icon: Calendar, label: "Scheduling" },
  calendar_and_email: { tone: "info", icon: Calendar, label: "Calendar + Email" },
  document_summary: { tone: "info", icon: FileText, label: "Summary" },
  workflow_action: { tone: "warning", icon: Wrench, label: "Workflow" },
  compound_workflow: { tone: "warning", icon: GitBranch, label: "Workflow" },
  workspace_insights: { tone: "primary", icon: BarChart3, label: "Insights" },
  out_of_scope: { tone: "muted", icon: AlertCircle, label: "Out of scope" },
  clarification: { tone: "neutral", icon: HelpCircle, label: "Clarify" },
};

export function IntentBadge({ intent }: { intent: Intent | string }) {
  const meta = INTENT_META[intent] ?? {
    tone: "neutral" as const,
    icon: HelpCircle,
    label: titleize(intent),
  };
  const Icon = meta.icon;
  return (
    <Badge tone={meta.tone} icon={<Icon className="h-3 w-3" />}>
      {meta.label}
    </Badge>
  );
}
