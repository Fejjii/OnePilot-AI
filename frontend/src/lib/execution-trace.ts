import type {
  ChatResponse,
  ExecutionTraceStep,
  MessageResponse,
  ToolCallTrace,
  TraceStep,
} from "@/types/api";

const STEP_LABELS: Record<string, string> = {
  understanding_request: "Understanding request",
  reading_crm_context: "Reading CRM context",
  searching_company_knowledge: "Searching company knowledge",
  retrieving_rag_evidence: "Retrieving RAG evidence",
  searching_the_web: "Searching the web",
  drafting_email: "Drafting email",
  checking_calendar: "Checking calendar",
  finding_meeting_times: "Finding meeting times",
  creating_approval: "Creating approval",
  reviewing_workspace: "Reviewing workspace activity",
  drafting_reply: "Drafting reply",
  asking_clarification: "Asking for clarification",
  checking_request_scope: "Checking request scope",
  safety_check: "Safety check",
};

const INTERNAL_STEP_TO_KEY: Record<string, string> = {
  classify_message: "understanding_request",
  classify_intent: "understanding_request",
  safety_check: "safety_check",
  "execute_tool:rag.answer": "retrieving_rag_evidence",
  "execute_tool:email.draft": "drafting_email",
  "execute_tool:calendar.check_availability": "checking_calendar",
  "execute_tool:calendar.suggest_slots": "finding_meeting_times",
  "execute_tool:calendar.create_event_request": "creating_approval",
  "execute_tool:lead.support": "reading_crm_context",
  "execute_tool:external.web_search": "searching_the_web",
  "execute_tool:workspace.insights": "reviewing_workspace",
  "execute_tool:chat.general": "drafting_reply",
  "execute_tool:clarification": "asking_clarification",
  "execute_tool:out_of_scope": "checking_request_scope",
};

const TOOL_LABELS: Record<string, string> = {
  "rag.answer": "Knowledge",
  "knowledge.search": "Knowledge",
  "email.draft": "Email",
  "calendar.check_availability": "Calendar",
  "calendar.suggest_slots": "Calendar",
  "calendar.create_event_request": "Calendar",
  "lead.support": "CRM",
  "external.web_search": "Web",
  "workspace.insights": "Insights",
  "chat.general": "Chat",
};

const HIDDEN_INTERNAL_STEPS = new Set([
  "resolve_language",
  "recall_memory",
  "route",
  "router",
  "persist_memory",
  "finalize_response",
  "guardrail",
]);

const COMPOUND_INTERNAL_STEPS = new Set([
  "execute_tool:calendar_and_email",
  "execute_tool:compound_workflow",
  "execute_tool:web_and_knowledge",
]);

const UNSAFE_TEXT =
  /\b(api[_-]?key|password|secret|token|authorization|bearer|credential|traceback|exception|system prompt|hidden reasoning|chain.of.thought)\b|reason=|class=|message_class=|sk-[A-Za-z0-9]{8,}|eyJ[A-Za-z0-9_-]{10,}\.|@(?:example|[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b|\b(?:msg|conv|org|usr|user|approval|lead)_[A-Za-z0-9]+\b/i;

export function toolBadgeLabel(toolName: string, explicit?: string | null): string {
  if (explicit && isSafePublicText(explicit)) return explicit;
  if (TOOL_LABELS[toolName]) return TOOL_LABELS[toolName];
  if (toolName.startsWith("calendar.")) return "Calendar";
  if (toolName.startsWith("email.")) return "Email";
  return "Tool";
}

export function uniqueToolLabels(toolCalls: ToolCallTrace[]): string[] {
  const labels: string[] = [];
  const seen = new Set<string>();
  for (const tool of toolCalls) {
    const label = toolBadgeLabel(tool.tool_name, tool.label);
    if (seen.has(label)) continue;
    seen.add(label);
    labels.push(label);
  }
  return labels;
}

export function isSafePublicText(value: string | null | undefined): boolean {
  if (!value) return false;
  const text = value.trim();
  if (!text || text.length > 160) return false;
  return !UNSAFE_TEXT.test(text);
}

export function sanitizeExecutionTrace(
  steps: ExecutionTraceStep[] | null | undefined,
): ExecutionTraceStep[] {
  if (!steps?.length) return [];
  const seen = new Set<string>();
  const safe: ExecutionTraceStep[] = [];
  for (const step of steps) {
    const key = step.key?.trim();
    const expected = key ? STEP_LABELS[key] : undefined;
    if (!key || !expected || seen.has(key)) continue;
    seen.add(key);
    const detail =
      step.detail && isSafePublicText(step.detail) ? step.detail.trim() : null;
    safe.push({
      key,
      label: expected,
      detail,
      duration_ms: Math.max(0, Number(step.duration_ms) || 0),
    });
  }
  return safe;
}

export function mapInternalTraceSteps(
  traceSteps: TraceStep[] | null | undefined,
): ExecutionTraceStep[] {
  if (!traceSteps?.length) return [];
  const seen = new Set<string>();
  const mapped: ExecutionTraceStep[] = [];
  for (const step of traceSteps) {
    const name = step.step;
    if (!name || HIDDEN_INTERNAL_STEPS.has(name) || COMPOUND_INTERNAL_STEPS.has(name)) {
      continue;
    }
    const key = INTERNAL_STEP_TO_KEY[name];
    const label = key ? STEP_LABELS[key] : undefined;
    if (!key || !label || seen.has(key)) continue;
    seen.add(key);
    mapped.push({
      key,
      label,
      detail: null,
      duration_ms: Math.max(0, Number(step.duration_ms) || 0),
    });
  }
  return mapped;
}

export function executionTraceFromChat(resp: ChatResponse): ExecutionTraceStep[] {
  const persisted = sanitizeExecutionTrace(resp.execution_trace);
  if (persisted.length > 0) return persisted;
  return mapInternalTraceSteps(resp.trace_steps);
}

export function executionTraceFromMessage(
  msg: MessageResponse,
): ExecutionTraceStep[] {
  return sanitizeExecutionTrace(msg.execution_trace);
}

const HIDDEN_USAGE_KEYS = new Set([
  "input_tokens",
  "output_tokens",
  "total_tokens",
  "tokens",
  "prompt_tokens",
  "completion_tokens",
  "model",
  "provider",
]);

export function publicUsageEntries(
  usage: Record<string, unknown> | null | undefined,
): Array<[string, string]> {
  if (!usage) return [];
  const entries: Array<[string, string]> = [];
  for (const [key, value] of Object.entries(usage)) {
    if (HIDDEN_USAGE_KEYS.has(key) || /token/i.test(key)) continue;
    const text = String(value);
    if (!isSafePublicText(text)) continue;
    entries.push([key, text]);
  }
  return entries;
}
