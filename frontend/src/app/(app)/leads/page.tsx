"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import {
  Users,
  Plus,
  Mail,
  Building2,
  Zap,
  Target,
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Modal } from "@/components/ui/modal";
import { Drawer } from "@/components/ui/drawer";
import {
  Input,
  Label,
  Select,
  Textarea,
  FieldError,
} from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/ui/error-state";
import { StatusBadge } from "@/components/domain/status-badge";
import { DataTable, type Column } from "@/components/ui/data-table";
import { ApiRequestError } from "@/lib/api-client";
import { useLeadCreateMutation, useLeads } from "@/lib/queries";
import { formatRelativeTime, titleize } from "@/lib/utils";
import type { LeadResponse } from "@/types/api";

const STATUS_OPTIONS = ["new", "contacted", "qualified", "proposal", "won", "lost"] as const;
const URGENCY_OPTIONS = ["low", "medium", "high"] as const;

const leadSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Invalid email").or(z.literal("")).optional(),
  company: z.string().optional(),
  source: z.string().optional(),
  urgency: z.enum(URGENCY_OPTIONS),
  intent: z.string().optional(),
  pain_point: z.string().optional(),
  summary: z.string().optional(),
  recommended_next_action: z.string().optional(),
  status: z.enum(STATUS_OPTIONS),
});

type LeadForm = z.infer<typeof leadSchema>;

export default function LeadsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [urgencyFilter, setUrgencyFilter] = useState<string>("");
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<LeadResponse | null>(null);

  const leads = useLeads({ status: statusFilter || undefined });
  const items = leads.data?.items ?? [];

  const filtered = urgencyFilter
    ? items.filter((l) => l.urgency === urgencyFilter)
    : items;

  const columns: Column<LeadResponse>[] = [
    {
      key: "name",
      header: "Lead",
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-slate-900">{row.name}</p>
          <p className="truncate text-[11px] text-slate-500">
            {row.email ?? "—"}
          </p>
        </div>
      ),
    },
    {
      key: "company",
      header: "Company",
      render: (row) => (
        <span className="text-sm text-slate-700">{row.company ?? "—"}</span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "urgency",
      header: "Urgency",
      render: (row) => <UrgencyPill level={row.urgency} />,
    },
    {
      key: "intent",
      header: "Intent",
      render: (row) =>
        row.intent ? (
          <Badge tone="primary">{titleize(row.intent)}</Badge>
        ) : (
          <span className="text-xs text-slate-400">—</span>
        ),
    },
    {
      key: "updated",
      header: "Updated",
      render: (row) => (
        <span className="text-xs text-slate-500">
          {formatRelativeTime(row.updated_at)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Leads"
        description="Prospects captured from chat, forms, and the lead-support intent."
        actions={
          <Button
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={() => setCreateOpen(true)}
          >
            New lead
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>All leads</CardTitle>
          <div className="flex items-center gap-2">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-8 text-xs"
            >
              <option value="">All statuses</option>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {titleize(s)}
                </option>
              ))}
            </Select>
            <Select
              value={urgencyFilter}
              onChange={(e) => setUrgencyFilter(e.target.value)}
              className="h-8 text-xs"
            >
              <option value="">All urgency</option>
              {URGENCY_OPTIONS.map((u) => (
                <option key={u} value={u}>
                  {titleize(u)}
                </option>
              ))}
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {leads.isError ? (
            <div className="p-4">
              <ErrorState
                title="Could not load leads"
                description="The leads list is temporarily unavailable. Check your connection and try again."
                onRetry={() => void leads.refetch()}
              />
            </div>
          ) : (
            <DataTable<LeadResponse>
              rows={filtered}
              columns={columns}
              getKey={(row) => row.id}
              onRowClick={(row) => setSelected(row)}
              isLoading={leads.isLoading}
              emptyTitle="No leads yet"
              emptyDescription="When the agent captures a lead, or you create one manually, it appears here."
            />
          )}
        </CardContent>
      </Card>

      <LeadDetailDrawer
        lead={selected}
        onClose={() => setSelected(null)}
      />
      <CreateLeadModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />
    </div>
  );
}

function UrgencyPill({ level }: { level: string }) {
  const tone =
    level === "high" ? "danger" : level === "medium" ? "warning" : "success";
  return <Badge tone={tone}>{titleize(level)}</Badge>;
}

interface LeadDetailDrawerProps {
  lead: LeadResponse | null;
  onClose: () => void;
}

function LeadDetailDrawer({ lead, onClose }: LeadDetailDrawerProps) {
  if (!lead) return null;
  return (
    <Drawer
      open={!!lead}
      onClose={onClose}
      title={lead.name}
      description={lead.company ?? "No company specified"}
      footer={
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={lead.status} />
          <UrgencyPill level={lead.urgency} />
          {lead.intent && (
            <Badge tone="primary">{titleize(lead.intent)}</Badge>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs">
          <DetailField icon={Mail} label="Email" value={lead.email ?? "—"} />
          <DetailField
            icon={Building2}
            label="Source"
            value={lead.source ? titleize(lead.source) : "—"}
          />
        </div>

        {lead.pain_point && (
          <Section title="Pain point" icon={Zap}>
            <p className="text-sm text-slate-700">{lead.pain_point}</p>
          </Section>
        )}

        {lead.summary && (
          <Section title="Summary" icon={Users}>
            <p className="whitespace-pre-wrap text-sm text-slate-700">
              {lead.summary}
            </p>
          </Section>
        )}

        {lead.recommended_next_action && (
          <Section title="Recommended next action" icon={Target}>
            <p className="rounded-md border border-indigo-100 bg-indigo-50/40 p-3 text-sm text-indigo-900">
              {lead.recommended_next_action}
            </p>
          </Section>
        )}

        <div className="border-t border-slate-100 pt-3 text-[11px] text-slate-500">
          Created {formatRelativeTime(lead.created_at)} · Updated{" "}
          {formatRelativeTime(lead.updated_at)}
        </div>
      </div>
    </Drawer>
  );
}

function DetailField({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Mail;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
      <p className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-slate-400">
        <Icon className="h-3 w-3" />
        {label}
      </p>
      <p className="mt-0.5 truncate text-xs font-medium text-slate-900">
        {value}
      </p>
    </div>
  );
}

function Section({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: typeof Mail;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <Icon className="h-3.5 w-3.5" />
        {title}
      </h4>
      {children}
    </section>
  );
}

interface CreateLeadModalProps {
  open: boolean;
  onClose: () => void;
}

function CreateLeadModal({ open, onClose }: CreateLeadModalProps) {
  const create = useLeadCreateMutation();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<LeadForm>({
    resolver: zodResolver(leadSchema),
    defaultValues: {
      name: "",
      email: "",
      company: "",
      source: "manual",
      urgency: "medium",
      intent: "",
      pain_point: "",
      summary: "",
      recommended_next_action: "",
      status: "new",
    },
  });

  async function onSubmit(values: LeadForm) {
    try {
      await create.mutateAsync({
        ...values,
        email: values.email || null,
        company: values.company || null,
        source: values.source || null,
        intent: values.intent || null,
        pain_point: values.pain_point || null,
        summary: values.summary || null,
        recommended_next_action: values.recommended_next_action || null,
      });
      toast.success("Lead created");
      reset();
      onClose();
    } catch (err) {
      const msg =
        err instanceof ApiRequestError ? err.message : "Could not create lead";
      toast.error("Failed to create lead", { description: msg });
    }
  }

  return (
    <Modal
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title="Create lead"
      description="Capture a prospect manually. The agent can also create leads via the lead-support intent."
      size="lg"
      footer={
        <>
          <Button
            variant="outline"
            onClick={() => {
              reset();
              onClose();
            }}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            form="create-lead-form"
            loading={isSubmitting}
          >
            Create lead
          </Button>
        </>
      }
    >
      <form
        id="create-lead-form"
        className="grid grid-cols-1 gap-3 sm:grid-cols-2"
        onSubmit={handleSubmit(onSubmit)}
      >
        <div className="sm:col-span-1">
          <Label htmlFor="name">Name *</Label>
          <Input id="name" {...register("name")} placeholder="Jane Buyer" />
          <FieldError message={errors.name?.message} />
        </div>
        <div className="sm:col-span-1">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" {...register("email")} placeholder="jane@example.com" />
          <FieldError message={errors.email?.message} />
        </div>
        <div className="sm:col-span-1">
          <Label htmlFor="company">Company</Label>
          <Input id="company" {...register("company")} placeholder="Acme Inc." />
        </div>
        <div className="sm:col-span-1">
          <Label htmlFor="source">Source</Label>
          <Input id="source" {...register("source")} placeholder="manual, website, chat…" />
        </div>
        <div>
          <Label htmlFor="status">Status</Label>
          <Select id="status" {...register("status")}>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {titleize(s)}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="urgency">Urgency</Label>
          <Select id="urgency" {...register("urgency")}>
            {URGENCY_OPTIONS.map((u) => (
              <option key={u} value={u}>
                {titleize(u)}
              </option>
            ))}
          </Select>
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor="intent">Intent</Label>
          <Input id="intent" {...register("intent")} placeholder="evaluation, demo, integration" />
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor="pain_point">Pain point</Label>
          <Textarea
            id="pain_point"
            rows={2}
            {...register("pain_point")}
            placeholder="What problem are they trying to solve?"
          />
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor="summary">Summary</Label>
          <Textarea
            id="summary"
            rows={3}
            {...register("summary")}
            placeholder="Context for the next call or email"
          />
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor="recommended_next_action">Recommended next action</Label>
          <Input
            id="recommended_next_action"
            {...register("recommended_next_action")}
            placeholder="Send pricing PDF, book intro call…"
          />
        </div>
      </form>
    </Modal>
  );
}
