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
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { MetricCard } from "@/components/ui/metric-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { UsageProgress } from "@/components/domain/usage-progress";
import { IntentBadge } from "@/components/domain/intent-badge";
import {
  useApprovals,
  useConversations,
  useDocuments,
  useHealth,
  useLeads,
  useUsageSummary,
} from "@/lib/queries";
import { formatRelativeTime } from "@/lib/utils";

export default function DashboardPage() {
  const conversations = useConversations(0, 50);
  const documents = useDocuments();
  const leads = useLeads();
  const approvals = useApprovals();
  const usage = useUsageSummary();
  const health = useHealth();

  const conversationsLoading = conversations.isLoading;
  const documentsLoading = documents.isLoading;
  const leadsLoading = leads.isLoading;
  const approvalsLoading = approvals.isLoading;

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
              <CardTitle>Provider mode</CardTitle>
              <span className="text-[11px] text-slate-500">
                Backend reports providers in /health
              </span>
            </CardHeader>
            <CardContent>
              {health.isLoading ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div
                      key={i}
                      className="h-16 animate-pulse rounded-md bg-slate-100"
                    />
                  ))}
                </div>
              ) : !health.data ? (
                <ErrorState onRetry={() => health.refetch()} />
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  <ProviderRow
                    name="OpenAI"
                    icon={Sparkles}
                    enabled={health.data.providers.openai}
                    fallbackLabel="Deterministic stub"
                  />
                  <ProviderRow
                    name="Qdrant vector store"
                    icon={Database}
                    enabled={health.data.providers.qdrant}
                    fallbackLabel="In-memory cosine search"
                  />
                  <ProviderRow
                    name="Redis cache"
                    icon={Cpu}
                    enabled={health.data.providers.redis}
                    fallbackLabel="Process cache"
                  />
                  <ProviderRow
                    name="LangSmith tracing"
                    icon={Activity}
                    enabled={health.data.providers.langsmith}
                    fallbackLabel="Local trace steps"
                  />
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

interface ProviderRowProps {
  name: string;
  icon: typeof Sparkles;
  enabled: boolean;
  fallbackLabel: string;
}

function ProviderRow({ name, icon: Icon, enabled, fallbackLabel }: ProviderRowProps) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2.5">
      <div className="flex items-start gap-2">
        <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-slate-100 text-slate-600">
          <Icon className="h-3.5 w-3.5" />
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-900">{name}</p>
          <p className="text-[10px] text-slate-500">
            {enabled ? "Live provider" : fallbackLabel}
          </p>
        </div>
      </div>
      {enabled ? (
        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
      ) : (
        <AlertTriangle className="h-4 w-4 text-amber-500" />
      )}
    </div>
  );
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
