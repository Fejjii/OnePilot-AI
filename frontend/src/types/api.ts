// Typed contracts for backend responses. These mirror the FastAPI schemas under
// backend/src/onepilot/schemas/. They are intentionally permissive about extra
// fields so backend additions do not break the UI.

export type Role = "owner" | "admin" | "member" | "viewer";

export type PlanCode = "free" | "pro" | "team" | "business";

export type ApprovalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "needs_more_info";

export type Intent =
  | "general_assistant"
  | "knowledge_search"
  | "lead_support"
  | "email_drafting"
  | "document_summary"
  | "workflow_action"
  | "out_of_scope"
  | "clarification";

export type UsageFeature =
  | "chat_messages"
  | "rag_queries"
  | "document_uploads"
  | "storage_mb"
  | "email_drafts"
  | "lead_workflows"
  | "tool_calls"
  | "users";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface MeResponse {
  user: User;
  organization: Organization;
  role: Role;
  plan: PlanCode;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface ApiError {
  error: string;
  message: string;
}

// Health & providers

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  env: string;
  providers: {
    openai: boolean;
    qdrant: boolean;
    redis: boolean;
    langsmith: boolean;
    database: boolean;
  };
}

// Chat & conversations

export interface Citation {
  document_id: string;
  document_title: string;
  section?: string | null;
  chunk_text: string;
  relevance_score: number;
}

export interface ToolCallTrace {
  tool_name: string;
  input_summary: string;
  output_summary: string;
  duration_ms: number;
}

export interface TraceStep {
  step: string;
  detail?: string | null;
  intent?: Intent | null;
  duration_ms: number;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  intent: Intent;
  confidence: number;
  final_response: string;
  citations: Citation[];
  tool_calls: ToolCallTrace[];
  approval_required: boolean;
  approval_id?: string | null;
  usage: Record<string, unknown>;
  trace_steps: TraceStep[];
  safety_flags: string[];
}

export interface MessageResponse {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  intent?: string | null;
  confidence: number;
  citations: Citation[];
  tool_calls: ToolCallTrace[];
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  last_intent?: string | null;
  message_count: number;
  last_message_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  items: ConversationSummary[];
  total: number;
}

export interface ConversationDetailResponse {
  id: string;
  title: string;
  last_intent?: string | null;
  messages: MessageResponse[];
}

// Knowledge / RAG

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_title: string;
  section?: string | null;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_found: number;
  weak_evidence: boolean;
  fallback_used: boolean;
}

export interface AnswerCitation {
  chunk_id: string;
  document_id: string;
  document_title: string;
  section?: string | null;
  score: number;
}

export interface AnswerResponse {
  query: string;
  answer: string;
  confidence: number;
  citations: AnswerCitation[];
  weak_evidence: boolean;
  fallback_used: boolean;
  model: string;
}

// Documents

export interface DocumentResponse {
  id: string;
  organization_id: string;
  filename: string;
  title: string;
  content_type: string;
  size_bytes: number;
  chunk_count: number;
  status: string;
  source: string;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentResponse[];
  total: number;
}

export interface DocumentChunkResponse {
  id: string;
  document_id: string;
  ordinal: number;
  section?: string | null;
  content: string;
  token_count: number;
}

export interface DocumentDetailResponse extends DocumentResponse {
  chunks: DocumentChunkResponse[];
}

// Leads

export interface LeadResponse {
  id: string;
  organization_id: string;
  name: string;
  company?: string | null;
  email?: string | null;
  status: string;
  source?: string | null;
  urgency: string;
  intent?: string | null;
  pain_point?: string | null;
  summary?: string | null;
  recommended_next_action?: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface LeadListResponse {
  items: LeadResponse[];
  total: number;
}

export interface LeadCreate {
  name: string;
  email?: string | null;
  company?: string | null;
  source?: string | null;
  urgency?: string;
  intent?: string | null;
  pain_point?: string | null;
  summary?: string | null;
  recommended_next_action?: string | null;
  status?: string;
}

// Approvals

export interface ApprovalResponse {
  id: string;
  organization_id: string;
  action_type: string;
  title: string;
  description: string;
  proposed_payload: Record<string, unknown>;
  risk_level: string;
  status: ApprovalStatus;
  reason: string;
  created_by: string;
  reviewed_by?: string | null;
  created_at: string;
  reviewed_at?: string | null;
}

export interface ApprovalListResponse {
  items: ApprovalResponse[];
  total: number;
  pending_count: number;
}

export interface ApprovalDecisionRequest {
  status: ApprovalStatus;
  reason?: string | null;
}

// Memory

export interface MemoryItemResponse {
  id: string;
  organization_id: string;
  user_id?: string | null;
  scope: string;
  key: string;
  value: string;
  ttl_seconds?: number | null;
  expires_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryListResponse {
  items: MemoryItemResponse[];
  total: number;
}

export interface MemoryWriteRequest {
  scope: string;
  key: string;
  value: string;
  ttl_seconds?: number | null;
}

// Audit / Usage

export interface AuditLogResponse {
  id: string;
  organization_id: string;
  user_id?: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  detail?: Record<string, unknown> | null;
  ip_address?: string | null;
  created_at: string;
}

export interface AuditListResponse {
  items: AuditLogResponse[];
  total: number;
}

export interface UsageEventResponse {
  id: string;
  organization_id: string;
  user_id?: string | null;
  feature: UsageFeature | string;
  model?: string | null;
  provider?: string | null;
  input_tokens: number;
  output_tokens: number;
  estimated_cost: number;
  fallback_used: boolean;
  tool_calls: number;
  latency_ms: number;
  created_at: string;
}

export interface UsageEventListResponse {
  items: UsageEventResponse[];
  total: number;
}

export interface UsageQuota {
  feature: UsageFeature | string;
  used: number;
  limit: number;
  remaining: number;
  period_start: string;
  period_end: string;
}

export interface UsageSummaryResponse {
  organization_id: string;
  plan_code: PlanCode | string;
  quotas: UsageQuota[];
  total_estimated_cost: number;
}

// Plans

export interface PlanLimits {
  chat_messages: number;
  rag_queries: number;
  document_uploads: number;
  storage_mb: number;
  email_drafts: number;
  lead_workflows: number;
  tool_calls: number;
  users: number;
}

export interface PlanResponse {
  code: PlanCode;
  name: string;
  monthly_price_cents: number;
  limits: PlanLimits;
}

export interface SubscriptionResponse {
  id: string;
  organization_id: string;
  plan_code: PlanCode;
  status: "active" | "cancelled" | "past_due" | "trialing";
  started_at: string;
  renews_at?: string | null;
}

export interface CurrentPlanResponse {
  plan: PlanResponse;
  subscription: SubscriptionResponse;
}
