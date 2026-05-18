"use client";

import {
  Building2,
  Sparkles,
  Cpu,
  Database,
  Activity,
  Server,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  CircleDashed,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PlanBadge } from "@/components/domain/plan-badge";
import { useAuth, isAdminRole } from "@/lib/auth";
import { useCurrentPlan, useHealth } from "@/lib/queries";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import {
  formatCurrencyCents,
  formatDateTime,
  formatNumber,
  titleize,
} from "@/lib/utils";

export default function SettingsPage() {
  const { user, refresh } = useAuth();
  const plan = useCurrentPlan();
  const health = useHealth();

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
          <CardTitle>Provider status</CardTitle>
          <span className="text-[11px] text-slate-500">
            Backend configuration reported by /health
          </span>
        </CardHeader>
        <CardContent>
          {health.isLoading ? (
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <CircleDashed className="h-3.5 w-3.5 animate-spin" />
              Checking…
            </div>
          ) : !health.data ? (
            <p className="text-xs text-slate-500">Provider status unavailable.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              <ProviderTile
                icon={Sparkles}
                name="OpenAI"
                enabled={health.data.providers.openai}
                fallback="Deterministic generation stub"
              />
              <ProviderTile
                icon={Database}
                name="Qdrant"
                enabled={health.data.providers.qdrant}
                fallback="In-memory cosine search"
              />
              <ProviderTile
                icon={Cpu}
                name="Redis"
                enabled={health.data.providers.redis}
                fallback="Process-local cache"
              />
              <ProviderTile
                icon={Activity}
                name="LangSmith"
                enabled={health.data.providers.langsmith}
                fallback="Inline trace steps"
              />
              <ProviderTile
                icon={Server}
                name="Database"
                enabled={health.data.providers.database}
                fallback="No fallback"
              />
            </div>
          )}
          {health.data && (
            <div className="mt-4 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
              <Badge tone="info">Environment: {health.data.env}</Badge>
              <span>App version v{health.data.version}</span>
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
              Integrations to Gmail, HubSpot, Calendar, Twilio, and Stripe are
              stubbed in this capstone.
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

function ProviderTile({
  icon: Icon,
  name,
  enabled,
  fallback,
}: {
  icon: typeof Sparkles;
  name: string;
  enabled: boolean;
  fallback: string;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2.5">
      <div className="flex items-start gap-2">
        <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-slate-100 text-slate-600">
          <Icon className="h-3.5 w-3.5" />
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-900">{name}</p>
          <p className="text-[11px] text-slate-500">
            {enabled ? "Configured (live)" : fallback}
          </p>
        </div>
      </div>
      {enabled ? (
        <Badge tone="success">Live</Badge>
      ) : (
        <Badge tone="warning">Fallback</Badge>
      )}
    </div>
  );
}
