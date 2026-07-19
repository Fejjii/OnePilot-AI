"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type {
  ApprovalDecisionRequest,
  ApprovalListResponse,
  ApprovalResponse,
  ApprovalStatus,
  AuditListResponse,
  ChatResponse,
  ConversationDetailResponse,
  ConversationListResponse,
  CurrentPlanResponse,
  DocumentDetailResponse,
  DocumentListResponse,
  DocumentResponse,
  HealthResponse,
  LanguagePreference,
  ProviderDiagnosticResponse,
  RuntimeModelConfigResponse,
  LeadCreate,
  LeadListResponse,
  LeadResponse,
  MemoryItemResponse,
  MemoryListResponse,
  MemoryWriteRequest,
  AnswerResponse,
  BillingPlansResponse,
  BillingSummaryResponse,
  InvoicePreviewResponse,
  UsageEventListResponse,
  UsageSummaryResponse,
  EvaluationSummaryResponse,
} from "@/types/api";

export const queryKeys = {
  health: ["health"] as const,
  providerDiagnostics: ["providers", "diagnostics"] as const,
  runtimeModelConfig: ["runtime", "config"] as const,
  usageSummary: ["usage", "summary"] as const,
  billingSummary: ["billing", "summary"] as const,
  billingInvoice: ["billing", "invoice-preview"] as const,
  billingPlans: ["billing", "plans"] as const,
  conversations: (offset = 0, limit = 50) =>
    ["conversations", { offset, limit }] as const,
  conversation: (id: string) => ["conversation", id] as const,
  documents: ["documents"] as const,
  document: (id: string) => ["document", id] as const,
  approvals: (filters: { status?: string | null; offset?: number } = {}) =>
    ["approvals", filters] as const,
  approval: (id: string) => ["approval", id] as const,
  leads: (filters: { status?: string | null } = {}) =>
    ["leads", filters] as const,
  lead: (id: string) => ["lead", id] as const,
  memory: (scope?: string | null) => ["memory", { scope: scope ?? null }] as const,
  auditLogs: (offset = 0) => ["audit-logs", { offset }] as const,
  usageEvents: (offset = 0) => ["usage-events", { offset }] as const,
  currentPlan: ["plan", "current"] as const,
  evaluationSummary: ["evaluation", "summary"] as const,
};

// --- Health -----------------------------------------------------------------

export function useHealth(opts?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => api.get<HealthResponse>("/health"),
    refetchInterval: 60_000,
    staleTime: 30_000,
    ...opts,
  });
}

export function useProviderDiagnostics(opts?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.providerDiagnostics,
    queryFn: () => api.get<ProviderDiagnosticResponse>("/providers"),
    refetchInterval: 60_000,
    staleTime: 30_000,
    ...opts,
  });
}

export function useRuntimeModelConfig(opts?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.runtimeModelConfig,
    queryFn: () => api.get<RuntimeModelConfigResponse>("/runtime/config"),
    refetchInterval: 60_000,
    staleTime: 30_000,
    ...opts,
  });
}

// --- Usage ------------------------------------------------------------------

export function useUsageSummary() {
  return useQuery({
    queryKey: queryKeys.usageSummary,
    queryFn: () => api.get<UsageSummaryResponse>("/usage/summary"),
  });
}

export function useBillingSummary() {
  return useQuery({
    queryKey: queryKeys.billingSummary,
    queryFn: () => api.get<BillingSummaryResponse>("/billing/summary"),
  });
}

export function useBillingInvoicePreview() {
  return useQuery({
    queryKey: queryKeys.billingInvoice,
    queryFn: () => api.get<InvoicePreviewResponse>("/billing/invoice-preview"),
  });
}

export function useBillingPlans() {
  return useQuery({
    queryKey: queryKeys.billingPlans,
    queryFn: () => api.get<BillingPlansResponse>("/billing/plans"),
  });
}

// --- Current plan -----------------------------------------------------------

export function useCurrentPlan() {
  return useQuery({
    queryKey: queryKeys.currentPlan,
    queryFn: () => api.get<CurrentPlanResponse>("/plans/current"),
  });
}

// --- Conversations & Chat ---------------------------------------------------

export function useConversations(offset = 0, limit = 50) {
  return useQuery({
    queryKey: queryKeys.conversations(offset, limit),
    queryFn: () =>
      api.get<ConversationListResponse>("/conversations", {
        query: { offset, limit },
      }),
  });
}

export function useConversation(
  id: string | null,
  opts?: Omit<UseQueryOptions<ConversationDetailResponse>, "queryKey" | "queryFn">,
) {
  return useQuery<ConversationDetailResponse>({
    queryKey: queryKeys.conversation(id ?? "none"),
    queryFn: () =>
      api.get<ConversationDetailResponse>(`/conversations/${id}`),
    enabled: !!id,
    // Never show a previous conversation's cache while the id is changing.
    staleTime: 0,
    ...opts,
  });
}

export interface ChatInput {
  message: string;
  conversation_id?: string | null;
  context?: Record<string, unknown>;
  language_preference?: LanguagePreference;
}

export function useChatMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ChatInput) =>
      api.post<ChatResponse>("/chat", input),
    onSuccess: (data) => {
      // Invalidate conversation list and the specific conversation so the UI
      // refreshes with the new messages.
      qc.invalidateQueries({ queryKey: ["conversations"] });
      qc.invalidateQueries({
        queryKey: queryKeys.conversation(data.conversation_id),
      });
      qc.invalidateQueries({ queryKey: queryKeys.usageSummary });
      qc.invalidateQueries({ queryKey: ["approvals"] });
    },
  });
}

export function useConversationDeleteMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) =>
      api.delete<void>(`/conversations/${conversationId}`),
    onMutate: async (conversationId) => {
      await qc.cancelQueries({ queryKey: ["conversations"] });
      const previous = qc.getQueriesData<{ items: { id: string }[]; total: number }>({
        queryKey: ["conversations"],
      });
      qc.setQueriesData<{ items: { id: string }[]; total: number }>(
        { queryKey: ["conversations"] },
        (old) => {
          if (!old) return old;
          const items = old.items.filter((c) => c.id !== conversationId);
          return { ...old, items, total: Math.max(0, old.total - 1) };
        },
      );
      return { previous };
    },
    onError: (_err, _id, context) => {
      context?.previous?.forEach(([key, data]) => {
        qc.setQueryData(key, data);
      });
    },
    onSuccess: (_data, conversationId) => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      qc.removeQueries({ queryKey: queryKeys.conversation(conversationId) });
    },
  });
}

// --- Documents --------------------------------------------------------------

export function useDocuments() {
  return useQuery({
    queryKey: queryKeys.documents,
    queryFn: () => api.get<DocumentListResponse>("/documents"),
  });
}

export function useDocument(id: string | null) {
  return useQuery<DocumentDetailResponse>({
    queryKey: queryKeys.document(id ?? "none"),
    queryFn: () =>
      api.get<DocumentDetailResponse>(`/documents/${id}`, {
        query: { include_chunks: true },
      }),
    enabled: !!id,
  });
}

export function useDocumentUploadMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.upload<DocumentResponse>("/documents/upload", form);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.documents });
    },
  });
}

export function useDocumentDeleteMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/documents/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.documents });
    },
  });
}

export function useAnswerMutation() {
  return useMutation({
    mutationFn: (input: { query: string; top_k?: number }) =>
      api.post<AnswerResponse>("/knowledge/answer", input),
  });
}

// --- Approvals --------------------------------------------------------------

interface ApprovalFilters {
  status?: string | null;
  offset?: number;
  limit?: number;
}

export function useApprovals(filters: ApprovalFilters = {}) {
  return useQuery({
    queryKey: queryKeys.approvals(filters),
    queryFn: () =>
      api.get<ApprovalListResponse>("/approvals", {
        query: {
          status: filters.status ?? undefined,
          offset: filters.offset ?? 0,
          limit: filters.limit ?? 50,
        },
      }),
  });
}

export function useApprovalDecisionMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      decision,
    }: {
      id: string;
      decision: ApprovalDecisionRequest;
    }) => api.post<ApprovalResponse>(`/approvals/${id}/decision`, decision),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["approvals"] });
      qc.invalidateQueries({ queryKey: ["audit-logs"] });
    },
  });
}

export type { ApprovalStatus };

// --- Leads ------------------------------------------------------------------

export function useLeads(filters: { status?: string | null } = {}) {
  return useQuery({
    queryKey: queryKeys.leads(filters),
    queryFn: () =>
      api.get<LeadListResponse>("/leads", {
        query: { status: filters.status ?? undefined },
      }),
  });
}

export function useLeadCreateMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LeadCreate) => api.post<LeadResponse>("/leads", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
  });
}

// --- Memory -----------------------------------------------------------------

export function useMemoryList(scope?: string | null) {
  return useQuery({
    queryKey: queryKeys.memory(scope),
    queryFn: () =>
      api.get<MemoryListResponse>("/memory", {
        query: { scope: scope ?? undefined },
      }),
  });
}

export function useMemoryWriteMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MemoryWriteRequest) =>
      api.post<MemoryItemResponse>("/memory", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memory"] });
    },
  });
}

export function useMemoryDeleteMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ scope, key }: { scope: string; key: string }) =>
      api.delete<void>(`/memory/${scope}/${encodeURIComponent(key)}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memory"] });
    },
  });
}

// --- Admin ------------------------------------------------------------------

export function useAuditLogs(offset = 0) {
  return useQuery({
    queryKey: queryKeys.auditLogs(offset),
    queryFn: () =>
      api.get<AuditListResponse>("/admin/audit-logs", {
        query: { offset, limit: 50 },
      }),
  });
}

export function useUsageEvents(offset = 0) {
  return useQuery({
    queryKey: queryKeys.usageEvents(offset),
    queryFn: () =>
      api.get<UsageEventListResponse>("/admin/usage-events", {
        query: { offset, limit: 50 },
      }),
  });
}

// --- Evaluation -------------------------------------------------------------

export function useEvaluationSummary() {
  return useQuery({
    queryKey: queryKeys.evaluationSummary,
    queryFn: () => api.get<EvaluationSummaryResponse>("/evaluation/summary"),
    staleTime: 60_000,
  });
}
