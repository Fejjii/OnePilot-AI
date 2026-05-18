"use client";

import {
  Building2,
  Sparkles,
  Cpu,
  Database,
  Activity,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  CircleDashed,
  Lock,
  Mail,
  Search,
  Calendar,
  DollarSign,
  MessageSquare,
  Users2,
  Cloud,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PlanBadge } from "@/components/domain/plan-badge";
import { useAuth, isAdminRole } from "@/lib/auth";
import { useCurrentPlan, useProviderDiagnostics } from "@/lib/queries";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { ProviderDiagnostic, ProviderMode } from "@/types/api";
import {
  formatCurrencyCents,
  formatDateTime,
  formatNumber,
  titleize,
} from "@/lib/utils";

export default function SettingsPage() {
  const { user, refresh } = useAuth();
  const plan = useCurrentPlan();
  const diagnostics = useProviderDiagnostics();

  if (!user) return null;

  const handleSeedDemoData = async () => {
    try {
      await api.post("/demo/seed_current_org", {});
      toast.success("Demo data seeded successfully!");
      refresh();
    } catch (error) {
      toast.error("Failed to seed demo data.");
      console.error("Failed to seed demo data:", error);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Workspace details, plan information, provider status, and security notes."
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Organization</CardTitle>
            <span className="text-[11px] text-slate-500">From /me</span>
          </CardHeader>
          <CardContent className="space-y-3">
            <Row icon={Building2} label="Name" value={user.organization.name} />
            <Row icon={Sparkles} label="Slug" value={user.organization.slug} mono />
            <Row
              icon={Activity}
              label="Created"
              value={formatDateTime(user.organization.created_at)}
            />
            <Row icon={ShieldCheck} label="Your role" value={titleize(user.role)} />
            <Row icon={Lock} label="Email" value={user.user.email} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Plan</CardTitle>
            <PlanBadge plan={user.plan} />
          </CardHeader>
          <CardContent>
            {plan.isLoading ? (
              <p className="text-xs text-slate-500">Loading plan…</p>
            ) : plan.data ? (
              <div className="space-y-3">
                <Row
                  icon={Sparkles}
                  label="Plan name"
                  value={plan.data.plan.name}
                />
                <Row
                  icon={Activity}
                  label="Monthly price"
                  value={
                    plan.data.plan.monthly_price_cents === 0
                      ? "Free"
                      : formatCurrencyCents(
                          plan.data.plan.monthly_price_cents,
                        ) + " / month"
                  }
                />
                <Row
                  icon={ShieldCheck}
                  label="Subscription status"
                  value={titleize(plan.data.subscription.status)}
                />
                <Row
                  icon={Activity}
                  label="Renews"
                  value={
                    plan.data.subscription.renews_at
                      ? formatDateTime(plan.data.subscription.renews_at)
                      : "—"
                  }
                />
                <div className="rounded-md border border-slate-200 bg-slate-50/40 p-3">
                  <p className="mb-2 text-[10px] uppercase tracking-wide text-slate-400">
                    Plan limits
                  </p>
                  <ul className="grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(plan.data.plan.limits).map(([k, v]) => (
                      <li key={k} className="flex justify-between gap-2">
                        <span className="text-slate-600">{titleize(k)}</span>
                        <span className="font-mono text-slate-900">
                          {v === -1 ? "∞" : formatNumber(v)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">No plan data available.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Runtime & Provider Diagnostics</CardTitle>
          <span className="text-[11px] text-slate-500">
            Detailed provider status from /providers
          </span>
        </CardHeader>
        <CardContent>
          {diagnostics.isLoading ? (
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <CircleDashed className="h-3.5 w-3.5 animate-spin" />
              Checking provider health…
            </div>
          ) : !diagnostics.data ? (
            <p className="text-xs text-slate-500">Provider diagnostics unavailable.</p>
          ) : (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {diagnostics.data.providers.map((provider) => (
                  <ProviderCard key={provider.name} provider={provider} />
                ))}
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50/40 p-3">
                <p className="mb-1.5 text-[10px] uppercase tracking-wide text-slate-400">
                  Provider modes explained
                </p>
                <ul className="space-y-1 text-[11px] text-slate-600">
                  <li>
                    <span className="font-semibold text-emerald-600">Live:</span> Real
                    provider is configured and operational
                  </li>
                  <li>
                    <span className="font-semibold text-blue-600">Local:</span> Using
                    local implementation (e.g., LangSmith local trace steps)
                  </li>
                  <li>
                    <span className="font-semibold text-amber-600">Mock:</span> Mock
                    provider for development (credentials not configured)
                  </li>
                  <li>
                    <span className="font-semibold text-amber-600">Fallback:</span>{" "}
                    Using deterministic fallback provider
                  </li>
                  <li>
                    <span className="font-semibold text-red-600">Unhealthy:</span>{" "}
                    Provider configured but connection failed
                  </li>
                </ul>
              </div>
              <p className="text-[11px] text-slate-500">
                Last checked: {formatDateTime(diagnostics.data.checked_at)}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {isAdminRole(user.role) && (
        <Card>
          <CardHeader>
            <CardTitle>Admin Actions</CardTitle>
            <span className="text-[11px] text-slate-500">
              Actions available to administrators.
            </span>
          </CardHeader>
          <CardContent>
            <Button onClick={handleSeedDemoData}>
              Seed demo data for current organization
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Security & data handling</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-xs text-slate-700">
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 text-emerald-500" />
              All data is scoped per organization. Cross-tenant reads are
              forbidden in repositories and services.
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 text-emerald-500" />
              Risky actions (email send, lead update, workflow execute) are
              gated by human approvals.
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 text-emerald-500" />
              The agent grounds answers in your knowledge base and returns
              citations with every response.
            </li>
            <li className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 text-amber-500" />
              Tokens are currently stored in <span className="font-mono">localStorage</span>.
              In production, prefer HTTP-only cookies set by the backend.
            </li>
            <li className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 text-amber-500" />
              SaaS providers (Gmail, HubSpot, Calendar, Twilio, Stripe, Serper)
              are provider-ready but use mock adapters unless real credentials
              are configured.
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({
  icon: Icon,
  label,
  value,
  mono,
}: {
  icon: typeof Sparkles;
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-slate-200 bg-white px-3 py-2">
      <div className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-100 text-slate-600">
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-wide text-slate-400">
          {label}
        </p>
        <p
          className={
            "truncate text-xs font-medium text-slate-900 " +
            (mono ? "font-mono" : "")
          }
        >
          {value}
        </p>
      </div>
    </div>
  );
}

function getModeBadge(mode: ProviderMode) {
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
    unhealthy: "Unhealthy",
  };
  return <Badge tone={toneMap[mode]}>{labelMap[mode]}</Badge>;
}

function ProviderCard({ provider }: { provider: ProviderDiagnostic }) {
  const renderIcon = () => {
    const iconClassName = "h-3.5 w-3.5";
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
      Twilio: <MessageSquare className={iconClassName} />,
      Stripe: <DollarSign className={iconClassName} />,
    };
    return iconMap[provider.name] || <Activity className={iconClassName} />;
  };
  
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-slate-100 text-slate-600">
            {renderIcon()}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-slate-900">{provider.name}</p>
            <p className="text-[10px] uppercase tracking-wide text-slate-400">
              {provider.category}
            </p>
          </div>
        </div>
        {getModeBadge(provider.mode)}
      </div>
      
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">Configured:</span>
          {provider.configured ? (
            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
          ) : (
            <AlertTriangle className="h-3 w-3 text-amber-500" />
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">Healthy:</span>
          {provider.healthy ? (
            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
          ) : (
            <AlertTriangle className="h-3 w-3 text-amber-500" />
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">Active:</span>
          {provider.active ? (
            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
          ) : (
            <AlertTriangle className="h-3 w-3 text-slate-400" />
          )}
        </div>
        {provider.model && (
          <div className="col-span-2 flex items-center gap-1.5">
            <span className="text-slate-500">Model:</span>
            <span className="font-mono text-slate-700">{provider.model}</span>
          </div>
        )}
      </div>
      
      {provider.reason && (
        <p className="text-[11px] text-slate-600 italic border-t border-slate-100 pt-2">
          {provider.reason}
        </p>
      )}
    </div>
  );
}
