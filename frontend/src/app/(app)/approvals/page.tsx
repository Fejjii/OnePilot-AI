"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import {
  ShieldCheck,
  Check,
  X,
  MessageSquare,
  ShieldAlert,
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/loading-skeleton";
import { Modal } from "@/components/ui/modal";
import { Select, Textarea, Label } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/domain/status-badge";
import { RiskBadge } from "@/components/domain/risk-badge";
import { ApprovalCard } from "@/components/domain/approval-card";
import { useApprovalDecisionMutation, useApprovals } from "@/lib/queries";
import { useAuth, isAdminRole } from "@/lib/auth";
import { ApiRequestError } from "@/lib/api-client";
import {
  cn,
  formatDateTime,
  formatRelativeTime,
  titleize,
} from "@/lib/utils";
import type { ApprovalResponse, ApprovalStatus } from "@/types/api";

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "needs_more_info", label: "Needs info" },
];

export default function ApprovalsPage() {
  return (
    <Suspense fallback={<ApprovalsSkeleton />}>
      <ApprovalsInner />
    </Suspense>
  );
}

function ApprovalsSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Skeleton className="h-[480px]" />
        <Skeleton className="h-[480px]" />
      </div>
    </div>
  );
}

function ApprovalsInner() {
  const { user } = useAuth();
  const isAdmin = isAdminRole(user?.role);
  const searchParams = useSearchParams();
  const focusId = searchParams.get("focus");

  // If a focus id is present we show all statuses so the linked approval is
  // findable; otherwise default to pending. This is render-derived (no effect).
  const [statusFilter, setStatusFilter] = useState<string>(
    focusId ? "" : "pending",
  );
  const approvals = useApprovals({ status: statusFilter || undefined });
  const items = useMemo(
    () => approvals.data?.items ?? [],
    [approvals.data],
  );

  const [selectedIdState, setSelectedIdState] = useState<string | null>(focusId);

  // React-recommended way to react to a value change without an effect.
  const [prevFocusId, setPrevFocusId] = useState<string | null>(focusId);
  if (prevFocusId !== focusId) {
    setPrevFocusId(focusId);
    if (focusId) setSelectedIdState(focusId);
  }

  const selectedId = selectedIdState;
  const selected = useMemo(
    () => items.find((i) => i.id === selectedId) ?? null,
    [items, selectedId],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Approvals"
        description="Human-in-the-loop gating for risky actions proposed by the agent."
        badge={
          <Badge tone="warning">
            {approvals.data?.pending_count ?? 0} pending
          </Badge>
        }
      />

      {!isAdmin && (
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <p>
            You are signed in as <span className="font-semibold capitalize">{user?.role}</span>.
            Decision actions are only available to admins and owners.
          </p>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Inbox</CardTitle>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-8 text-xs"
            >
              {STATUS_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </Select>
          </CardHeader>
          <CardContent className="space-y-2">
            {approvals.isError ? (
              <ErrorState onRetry={() => approvals.refetch()} />
            ) : approvals.isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-20 w-full" />
                ))}
              </div>
            ) : items.length === 0 ? (
              <EmptyState
                icon={ShieldCheck}
                title="No approvals here"
                description="When the agent proposes a sensitive action it appears here for review."
              />
            ) : (
              items.map((approval) => (
                <ApprovalCard
                  key={approval.id}
                  approval={approval}
                  active={approval.id === selectedId}
                  onClick={() => setSelectedIdState(approval.id)}
                />
              ))
            )}
          </CardContent>
        </Card>

        <ApprovalDetail
          approval={selected}
          isAdmin={isAdmin}
          onClear={() => setSelectedIdState(null)}
        />
      </div>
    </div>
  );
}

interface ApprovalDetailProps {
  approval: ApprovalResponse | null;
  isAdmin: boolean;
  onClear: () => void;
}

function ApprovalDetail({ approval, isAdmin, onClear }: ApprovalDetailProps) {
  const [decisionModal, setDecisionModal] = useState<ApprovalStatus | null>(null);

  if (!approval) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Request details</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={MessageSquare}
            title="Select a request"
            description="Pick a request from the inbox to inspect its proposed payload and take action."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{approval.title}</CardTitle>
        <button
          onClick={onClear}
          className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          aria-label="Close detail"
        >
          <X className="h-4 w-4" />
        </button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={approval.status} />
          <RiskBadge level={approval.risk_level} />
          <Badge tone="info">{titleize(approval.action_type)}</Badge>
        </div>

        {approval.description && (
          <p className="rounded-md border border-slate-200 bg-slate-50/40 p-3 text-sm leading-relaxed text-slate-700">
            {approval.description}
          </p>
        )}

        <section>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Proposed payload
          </h4>
          <pre className="max-h-72 overflow-auto rounded-md border border-slate-200 bg-slate-950 px-3 py-2 text-[11px] leading-relaxed text-slate-200 thin-scrollbar">
            {JSON.stringify(approval.proposed_payload, null, 2)}
          </pre>
        </section>

        <div className="grid grid-cols-2 gap-3 text-[11px]">
          <Field label="Created" value={formatRelativeTime(approval.created_at)} />
          <Field
            label="Reviewed"
            value={
              approval.reviewed_at
                ? `${formatRelativeTime(approval.reviewed_at)} (${formatDateTime(
                    approval.reviewed_at,
                  )})`
                : "—"
            }
          />
          <Field label="Created by" value={approval.created_by} mono />
          <Field
            label="Reviewed by"
            value={approval.reviewed_by ?? "—"}
            mono
          />
        </div>

        {approval.reason && (
          <div className="rounded-md border border-slate-200 bg-white p-3 text-xs">
            <p className="text-[10px] uppercase tracking-wide text-slate-400">
              Reason
            </p>
            <p className="mt-1 text-slate-700">{approval.reason}</p>
          </div>
        )}

        {isAdmin && approval.status === "pending" && (
          <div className={cn("flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3")}>
            <Button
              variant="primary"
              leftIcon={<Check className="h-3.5 w-3.5" />}
              onClick={() => setDecisionModal("approved")}
            >
              Approve
            </Button>
            <Button
              variant="danger"
              leftIcon={<X className="h-3.5 w-3.5" />}
              onClick={() => setDecisionModal("rejected")}
            >
              Reject
            </Button>
            <Button
              variant="outline"
              leftIcon={<MessageSquare className="h-3.5 w-3.5" />}
              onClick={() => setDecisionModal("needs_more_info")}
            >
              Needs more info
            </Button>
          </div>
        )}

        {decisionModal && (
          <DecisionModal
            approval={approval}
            decision={decisionModal}
            onClose={() => setDecisionModal(null)}
          />
        )}
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
      <p className="text-[10px] uppercase tracking-wide text-slate-400">{label}</p>
      <p
        className={cn(
          "mt-0.5 truncate text-xs font-medium text-slate-900",
          mono && "font-mono",
        )}
      >
        {value}
      </p>
    </div>
  );
}

interface DecisionModalProps {
  approval: ApprovalResponse;
  decision: ApprovalStatus;
  onClose: () => void;
}

function DecisionModal({ approval, decision, onClose }: DecisionModalProps) {
  const mutation = useApprovalDecisionMutation();
  const [reason, setReason] = useState("");

  const title =
    decision === "approved"
      ? "Approve request"
      : decision === "rejected"
        ? "Reject request"
        : "Request more info";

  async function submit() {
    try {
      await mutation.mutateAsync({
        id: approval.id,
        decision: { status: decision, reason: reason || null },
      });
      toast.success("Decision recorded", {
        description: `${approval.title} → ${titleize(decision)}`,
      });
      onClose();
    } catch (err) {
      const msg =
        err instanceof ApiRequestError
          ? err.message
          : "Could not submit decision";
      toast.error("Failed", { description: msg });
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={title}
      description={approval.title}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant={decision === "rejected" ? "danger" : "primary"}
            loading={mutation.isPending}
            onClick={submit}
          >
            Confirm {titleize(decision)}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <div className="rounded-md border border-slate-200 bg-slate-50/40 p-3 text-xs text-slate-700">
          <p>
            This will record an audit-log entry on the approval and mark its
            status as <span className="font-semibold">{titleize(decision)}</span>.
            No external systems will be touched.
          </p>
        </div>
        <div>
          <Label htmlFor="reason">Reason (optional)</Label>
          <Textarea
            id="reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain why for the audit trail…"
          />
        </div>
      </div>
    </Modal>
  );
}
