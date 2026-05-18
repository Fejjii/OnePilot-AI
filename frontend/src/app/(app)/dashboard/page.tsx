"use client";

import Link from "next/link";
import {
  MessageSquare,
  BookOpen,
  Users,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Cpu,
  Database,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Mail,
  Search,
  Calendar,
  DollarSign,
  Users2,
  MessageSquare as TwilioIcon,
  Cloud,
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { MetricCard } from "@/components/ui/metric-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { UsageProgress } from "@/components/domain/usage-progress";
import { IntentBadge } from "@/components/domain/intent-badge";
import { Badge } from "@/components/ui/badge";
import {
  useApprovals,
  useConversations,
  useDocuments,
  useProviderDiagnostics,
  useLeads,
  useUsageSummary,
} from "@/lib/queries";
import { formatRelativeTime } from "@/lib/utils";
import type { ProviderDiagnostic, ProviderMode } from "@/types/api";

export default function DashboardPage() {
  const conversations = useConversations(0, 50);
  const documents = useDocuments();
  const leads = useLeads();
  const approvals = useApprovals();
  const usage = useUsageSummary();
  const diagnostics = useProviderDiagnostics();

  const conversationsLoading = conversations.isLoading;
  const documentsLoading = documents.isLoading;
  const leadsLoading = leads.isLoading;
  const approvalsLoading = approvals.isLoading;

  const coreProviders = diagnostics.data?.providers.filter(
    (p) =>
      p.category === "llm" ||
      p.category === "embeddings" ||
      p.category === "vector" ||
      p.category === "database"
  );
  const allCoreLive =
    coreProviders && coreProviders.every((p) => p.mode === "live");
  const hasMixedModes =
    diagnostics.data &&
    diagnostics.data.providers.some((p) => p.mode === "mock" || p.mode === "fallback");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Operational overview across knowledge, agent activity, leads, and approvals."
        actions={
          <Link href="/workspace">
            <Button leftIcon={<Sparkles className="h-4 w-4" />}>
              Open AI Workspace
            </Button>
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Conversations"
          value={conversations.data?.total ?? 0}
          icon={MessageSquare}
          isLoading={conversationsLoading}
          hint="All-time chat sessions"
        />
        <MetricCard
          label="Documents indexed"
          value={documents.data?.total ?? 0}
          icon={BookOpen}
          iconClassName="bg-emerald-50 text-emerald-600"
          isLoading={documentsLoading}
          hint="Searchable knowledge base"
        />
        <MetricCard
          label="Leads captured"
          value={leads.data?.total ?? 0}
          icon={Users}
          iconClassName="bg-sky-50 text-sky-600"
          isLoading={leadsLoading}
          hint="Pipeline-ready prospects"
        />
        <MetricCard
          label="Pending approvals"
          value={approvals.data?.pending_count ?? 0}
          icon={ShieldCheck}
          iconClassName="bg-amber-50 text-amber-600"
          isLoading={approvalsLoading}
          hint="Awaiting admin decision"
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>Recent agent activity</CardTitle>
              <Link
                href="/workspace"
                className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
              >
                View all →
              </Link>
            </CardHeader>
            <CardContent>
              {conversations.isError ? (
                <ErrorState onRetry={() => conversations.refetch()} />
              ) : conversationsLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div
                      key={i}
                      className="h-12 animate-pulse rounded-md bg-slate-100"
                    />
                  ))}
                </div>
              ) : !conversations.data || conversations.data.items.length === 0 ? (
                <EmptyState
                  icon={MessageSquare}
                  title="No conversations yet"
                  description="Start a conversation in the AI Workspace to see activity here."
                  action={
                    <Link href="/workspace">
                      <Button size="sm" leftIcon={<Plus className="h-3.5 w-3.5" />}>
                        New conversation
                      </Button>
                    </Link>
                  }
                />
              ) : (
                <ul className="divide-y divide-slate-100">
                  {conversations.data.items.slice(0, 6).map((c) => (
                    <li key={c.id}>
                      <Link
                        href={`/workspace?conversation=${c.id}`}
                        className="flex items-center justify-between gap-3 py-2.5 hover:bg-slate-50 -mx-1 px-1 rounded-md"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-slate-900">
                            {c.title}
                          </p>
                          <p className="text-[11px] text-slate-500">
                            Updated {formatRelativeTime(c.updated_at)}
                          </p>
                        </div>
                        {c.last_intent && <IntentBadge intent={c.last_intent} />}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Provider diagnostics</CardTitle>
              <Link
                href="/settings"
                className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
              >
                View details →
              </Link>
            </CardHeader>
            <CardContent>
              {diagnostics.isLoading ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div
                      key={i}
                      className="h-16 animate-pulse rounded-md bg-slate-100"
                    />
                  ))}
                </div>
              ) : !diagnostics.data ? (
                <ErrorState onRetry={() => diagnostics.refetch()} />
              ) : (
                <div className="space-y-3">
                  {hasMixedModes && (
                    <div className="rounded-md border border-amber-200 bg-amber-50/50 px-3 py-2">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                        <p className="text-[11px] text-amber-900">
                          {allCoreLive
                            ? "Core providers are live, but some SaaS providers are using mock adapters."
                            : "Mixed provider modes: Some providers are using fallback or mock implementations."}
                        </p>
                      </div>
                    </div>
                  )}
                  <div className="grid gap-2.5 sm:grid-cols-2">
                    {diagnostics.data.providers
                      .filter((p) =>
                        [
                          "llm",
                          "embeddings",
                          "vector",
                          "cache",
                          "observability",
                          "database",
                        ].includes(p.category)
                      )
                      .map((provider) => (
                        <ProviderCard key={provider.name} provider={provider} />
                      ))}
                  </div>
                  {hasMixedModes && (
                    <details className="group">
                      <summary className="cursor-pointer text-[11px] text-indigo-600 hover:text-indigo-700 font-medium">
                        Show SaaS provider status ({
                          diagnostics.data.providers.filter((p) =>
                            ["search", "email", "crm", "calendar", "sms", "billing"].includes(
                              p.category
                            )
                          ).length
                        })
                      </summary>
                      <div className="mt-2 grid gap-2.5 sm:grid-cols-2">
                        {diagnostics.data.providers
                          .filter((p) =>
                            ["search", "email", "crm", "calendar", "sms", "billing"].includes(
                              p.category
                            )
                          )
                          .map((provider) => (
                            <ProviderCard key={provider.name} provider={provider} compact />
                          ))}
                      </div>
                    </details>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>Usage this period</CardTitle>
              <Link
                href="/usage"
                className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
              >
                Details →
              </Link>
            </CardHeader>
            <CardContent>
              {usage.isError ? (
                <ErrorState onRetry={() => usage.refetch()} />
              ) : usage.isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div
                      key={i}
                      className="h-12 animate-pulse rounded-md bg-slate-100"
                    />
                  ))}
                </div>
              ) : !usage.data || usage.data.quotas.length === 0 ? (
                <EmptyState
                  title="No quota data"
                  description="Quotas appear here as the agent generates usage events."
                />
              ) : (
                <div className="space-y-2.5">
                  {usage.data.quotas.slice(0, 4).map((q) => (
                    <UsageProgress key={q.feature} quota={q} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick actions</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2">
              <QuickAction
                href="/workspace"
                icon={MessageSquare}
                title="Start a conversation"
                hint="Ask the AI grounded questions"
              />
              <QuickAction
                href="/knowledge"
                icon={BookOpen}
                title="Upload a document"
                hint="Index it for grounded answers"
              />
              <QuickAction
                href="/leads"
                icon={Users}
                title="Create a lead"
                hint="Track a new prospect"
              />
              <QuickAction
                href="/approvals"
                icon={ShieldCheck}
                title="Review approvals"
                hint="Decide on pending actions"
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function getStatusIcon(provider: ProviderDiagnostic) {
  if (!provider.healthy || provider.mode === "unhealthy") {
    return <AlertTriangle className="h-3.5 w-3.5 text-red-500" />;
  }
  if (provider.mode === "live") {
    return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />;
  }
  if (provider.mode === "local") {
    return <CheckCircle2 className="h-3.5 w-3.5 text-blue-500" />;
  }
  return <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />;
}

function getModeBadge(mode: ProviderMode, compact?: boolean) {
  const toneMap: Record<ProviderMode, "success" | "info" | "warning" | "danger"> = {
    live: "success",
    local: "info",
    mock: "warning",
    fallback: "warning",
    missing: "warning",
    unhealthy: "danger",
  };
  const labelMap: Record<ProviderMode, string> = {
    live: "Live",
    local: "Local",
    mock: "Mock",
    fallback: "Fallback",
    missing: "Missing",
    unhealthy: "Error",
  };
  
  if (compact) {
    return (
      <div className={`h-2 w-2 rounded-full ${
        mode === "live" ? "bg-emerald-500" :
        mode === "local" ? "bg-blue-500" :
        mode === "unhealthy" ? "bg-red-500" :
        "bg-amber-500"
      }`} />
    );
  }
  
  return <Badge tone={toneMap[mode]}>{labelMap[mode]}</Badge>;
}

function ProviderCard({
  provider,
  compact,
}: {
  provider: ProviderDiagnostic;
  compact?: boolean;
}) {
  const renderIcon = () => {
    const iconClassName = compact ? "h-3.5 w-3.5 text-slate-600 shrink-0" : "h-3.5 w-3.5";
    const iconMap: Record<string, React.ReactElement> = {
      "OpenAI LLM": <Sparkles className={iconClassName} />,
      "OpenAI Embeddings": <Cloud className={iconClassName} />,
      Qdrant: <Database className={iconClassName} />,
      Redis: <Cpu className={iconClassName} />,
      Postgres: <Database className={iconClassName} />,
      LangSmith: <Activity className={iconClassName} />,
      Serper: <Search className={iconClassName} />,
      Gmail: <Mail className={iconClassName} />,
      HubSpot: <Users2 className={iconClassName} />,
      "Google Calendar": <Calendar className={iconClassName} />,
      Twilio: <TwilioIcon className={iconClassName} />,
      Stripe: <DollarSign className={iconClassName} />,
    };
    return iconMap[provider.name] || <Activity className={iconClassName} />;
  };

  if (compact) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-2">
        <div className="flex items-center gap-2 min-w-0">
          {renderIcon()}
          <span className="text-[11px] font-medium text-slate-900 truncate">
            {provider.name}
          </span>
        </div>
        {getModeBadge(provider.mode, true)}
      </div>
    );
  }

  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2.5">
      <div className="flex items-start gap-2">
        <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-slate-100 text-slate-600">
          {renderIcon()}
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-900">{provider.name}</p>
          <p className="text-[10px] text-slate-500">
            {provider.mode === "live"
              ? provider.model || "Operational"
              : provider.reason?.split(",")[0] || titleize(provider.mode)}
          </p>
        </div>
      </div>
      {getStatusIcon(provider)}
    </div>
  );
}

function titleize(str: string) {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

interface QuickActionProps {
  href: string;
  icon: typeof Sparkles;
  title: string;
  hint: string;
}

function QuickAction({ href, icon: Icon, title, hint }: QuickActionProps) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2.5 transition-colors hover:border-indigo-300 hover:bg-indigo-50/30"
    >
      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-50 text-indigo-600">
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1">
        <p className="text-xs font-semibold text-slate-900">{title}</p>
        <p className="text-[10px] text-slate-500">{hint}</p>
      </div>
      <ArrowRight className="h-3.5 w-3.5 text-slate-300" />
    </Link>
  );
}
