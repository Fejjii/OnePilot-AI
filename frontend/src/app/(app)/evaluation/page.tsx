"use client";

import {
  ClipboardCheck,
  ShieldCheck,
  Route,
  BookOpen,
  AlertTriangle,
  Terminal,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";
import { Badge } from "@/components/ui/badge";
import { DataTable, type Column } from "@/components/ui/data-table";
import { useEvaluationSummary } from "@/lib/queries";
import { formatDateTime } from "@/lib/utils";
import type { EvaluationMetrics, HitlApprovalSafety } from "@/types/api";

function pct(value: number | undefined) {
  if (value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

export default function EvaluationPage() {
  const { data, isLoading, isError, refetch } = useEvaluationSummary();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Evaluation & Quality"
          description="Deterministic checks for routing, RAG, and safety — automated quality gates."
        />
        <LoadingSkeleton lines={6} />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState
        title="Could not load evaluation summary"
        description="Ensure the backend is running and try again."
        onRetry={() => refetch()}
      />
    );
  }

  if (!data?.available) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Evaluation & Quality"
          description="Deterministic checks for routing, RAG, and safety — automated quality gates."
        />
        <EmptyState
          icon={ClipboardCheck}
          title="No evaluation report yet"
          description={
            data?.message ??
            "Run the offline evaluation script to generate reports/evaluation/latest.json."
          }
        />
        <RunEvalCard command={data?.run_command} />
        <ReviewerCopy />
        <RoadmapSection items={data?.future_roadmap} />
      </div>
    );
  }

  const metrics = data.metrics as EvaluationMetrics;
  const routingSuite = data.suites?.routing as Record<string, unknown> | undefined;
  const ragSuite = data.suites?.rag as Record<string, unknown> | undefined;
  const safetySuite = data.suites?.safety as Record<string, unknown> | undefined;
  const hitl = data.hitl_approval_safety;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Evaluation & Quality"
        description="Deterministic checks for routing, RAG, and safety — automated quality gates."
        badge={
          data.generated_at ? (
            <Badge tone="muted" className="text-xs font-normal">
              Last run: {formatDateTime(data.generated_at)}
            </Badge>
          ) : undefined
        }
      />

      {data.disclaimer && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {data.disclaimer}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Intent accuracy" value={pct(metrics.intent_accuracy)} icon={Route} />
        <MetricCard label="Routing accuracy" value={pct(metrics.routing_accuracy)} icon={Route} />
        <MetricCard label="RAG golden pass" value={pct(metrics.rag_golden_pass_rate)} icon={BookOpen} />
        <MetricCard
          label="Safety pass rate"
          value={pct(metrics.safety_guardrail_pass_rate)}
          icon={ShieldCheck}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Source hit rate" value={pct(metrics.source_hit_rate)} icon={BookOpen} />
        <MetricCard
          label="Citation presence"
          value={pct(metrics.citation_presence_rate)}
          icon={BookOpen}
        />
        <MetricCard
          label="Weak-evidence correctness"
          value={pct(metrics.weak_evidence_correctness)}
          icon={AlertTriangle}
        />
        <MetricCard
          label="Failed cases"
          value={metrics.failed_cases}
          hint={`${metrics.total_cases} total cases`}
          icon={AlertTriangle}
          iconClassName={metrics.failed_cases > 0 ? "bg-rose-50 text-rose-600" : undefined}
        />
      </div>

      <RunEvalCard command={data.run_command} />

      <SuiteTable
        title="Routing & intent evaluation"
        description="Two-stage classifier: message class → intent."
        rows={(routingSuite?.case_results as Array<Record<string, unknown>>) ?? []}
        columns={routingColumns}
      />

      <SuiteTable
        title="RAG golden evaluation"
        description="Offline keyword scoring over NovaEdge demo docs."
        rows={(ragSuite?.case_results as Array<Record<string, unknown>>) ?? []}
        columns={ragColumns}
      />

      <SuiteTable
        title="Safety & guardrail evaluation"
        description="Prompt injection, approval bypass, and HITL policy checks."
        rows={(safetySuite?.case_results as Array<Record<string, unknown>>) ?? []}
        columns={safetyColumns}
      />

      {data.failed_cases && data.failed_cases.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-rose-600" />
              Failed cases
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-slate-700">
              {data.failed_cases.map((fc, i) => (
                <li key={i} className="rounded-md border border-rose-100 bg-rose-50/50 px-3 py-2">
                  <span className="font-medium text-rose-800">[{String(fc.suite)}]</span>{" "}
                  {String(fc.message ?? fc.query ?? fc.category ?? JSON.stringify(fc))}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <HitlSection
        hitl={hitl}
        safetyCases={safetySuite?.case_results as Array<Record<string, unknown>>}
      />

      <ReviewerCopy />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4 text-indigo-600" />
            Limitations & production scaling
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-slate-600">
          <ul className="list-disc space-y-1 pl-5">
            {(data.limitations ?? []).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p>
            In production, this harness would run in CI on every release, feed dashboards, and
            complement human review — not replace it.
          </p>
        </CardContent>
      </Card>

      <RoadmapSection items={data.future_roadmap} />
    </div>
  );
}

function RunEvalCard({ command }: { command?: string | null }) {
  const cmd = command ?? "cd backend && uv run python -m onepilot.evaluation.run_all_evals";
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Terminal className="h-4 w-4" />
          Regenerate evaluation report
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-2 text-sm text-slate-600">
          Reports are written to{" "}
          <code className="text-xs">backend/reports/evaluation/latest.json</code>. The API reads
          the file — it does not run evals on request.
        </p>
        <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100">{cmd}</pre>
      </CardContent>
    </Card>
  );
}

function ReviewerCopy() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">What is tested</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 text-sm text-slate-600 md:grid-cols-2">
        <div>
          <p className="font-medium text-slate-900">Covered today</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Agent routing (message class + intent)</li>
            <li>RAG golden queries (retrieval heuristics + citations)</li>
            <li>Safety guardrails and approval gating policies</li>
            <li>494+ backend pytest cases (auth, RAG, tools, approvals)</li>
          </ul>
        </div>
        <div>
          <p className="font-medium text-slate-900">Not a replacement for</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Full RAGAS faithfulness / relevancy scoring</li>
            <li>LangSmith dataset regression at scale</li>
            <li>Human evaluation of tone and edge cases</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

function RoadmapSection({ items }: { items?: string[] }) {
  if (!items?.length) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Future: RAGAS & LangSmith</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function HitlSection({
  hitl,
  safetyCases,
}: {
  hitl?: HitlApprovalSafety | null;
  safetyCases?: Array<Record<string, unknown>>;
}) {
  const approvalCases = (safetyCases ?? []).filter((c) => c.check === "requires_approval");
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          Approval safety (human-in-the-loop)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-slate-600">
        <ul className="list-disc space-y-1 pl-5">
          <li>Sensitive actions require approval before execution.</li>
          <li>AI can draft emails but cannot send without approval.</li>
          <li>Approval decisions are audit-logged for compliance review.</li>
          <li>Admin and Owner roles review pending actions in the Approvals queue.</li>
        </ul>
        {hitl && (
          <p className="text-xs text-slate-500">
            Gated actions: {hitl.gated_action_types.join(", ")}
          </p>
        )}
        {approvalCases.length > 0 && (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <p className="font-medium text-slate-800">Policy eval cases</p>
            <ul className="mt-2 space-y-1 text-xs">
              {approvalCases.map((c) => (
                <li key={String(c.action_type)}>
                  {String(c.action_type)} → requires approval:{" "}
                  {c.actual_requires_approval ? "yes" : "no"}
                  {c.passed ? " ✓" : " ✗"}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

type EvalRow = Record<string, unknown>;

const routingColumns: Column<EvalRow>[] = [
  { key: "category", header: "Category", render: (r) => String(r.category ?? "") },
  { key: "message", header: "Message", render: (r) => String(r.message ?? "").slice(0, 48) },
  {
    key: "passed",
    header: "Pass",
    render: (r) => (
      <Badge tone={r.passed ? "success" : "danger"}>{r.passed ? "Pass" : "Fail"}</Badge>
    ),
  },
];

const ragColumns: Column<EvalRow>[] = [
  { key: "category", header: "Category", render: (r) => String(r.category ?? "") },
  { key: "query", header: "Query", render: (r) => String(r.query ?? "").slice(0, 56) },
  {
    key: "passed",
    header: "Pass",
    render: (r) => (
      <Badge tone={r.passed ? "success" : "danger"}>{r.passed ? "Pass" : "Fail"}</Badge>
    ),
  },
];

const safetyColumns: Column<EvalRow>[] = [
  { key: "category", header: "Category", render: (r) => String(r.category ?? "") },
  {
    key: "message",
    header: "Case",
    render: (r) => String(r.message ?? r.action_type ?? "").slice(0, 48),
  },
  {
    key: "passed",
    header: "Pass",
    render: (r) => (
      <Badge tone={r.passed ? "success" : "danger"}>{r.passed ? "Pass" : "Fail"}</Badge>
    ),
  },
];

function SuiteTable({
  title,
  description,
  rows,
  columns,
}: {
  title: string;
  description: string;
  rows: EvalRow[];
  columns: Column<EvalRow>[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <p className="text-sm text-slate-500">{description}</p>
      </CardHeader>
      <CardContent className="p-0">
        <DataTable<EvalRow>
          rows={rows}
          columns={columns}
          getKey={(row) =>
            `${String(row.category)}-${String(row.message ?? row.query ?? row.action_type ?? "")}`
          }
          emptyTitle="No case results"
          emptyDescription="Regenerate the evaluation report to populate this table."
        />
      </CardContent>
    </Card>
  );
}
