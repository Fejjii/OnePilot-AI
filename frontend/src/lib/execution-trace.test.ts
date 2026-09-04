import { describe, expect, it } from "vitest";
import {
  executionTraceFromChat,
  executionTraceFromMessage,
  isSafePublicText,
  mapInternalTraceSteps,
  publicUsageEntries,
  sanitizeExecutionTrace,
  toolBadgeLabel,
  uniqueToolLabels,
} from "./execution-trace";
import type { ChatResponse, MessageResponse } from "@/types/api";

describe("execution-trace", () => {
  it("maps internal steps to recruiter-facing labels and hides internals", () => {
    const mapped = mapInternalTraceSteps([
      { step: "classify_intent", detail: "reason=rules", duration_ms: 4 },
      { step: "route", detail: "email_assistant", duration_ms: 1 },
      { step: "recall_memory", detail: "enabled=true", duration_ms: 2 },
      { step: "execute_tool:email.draft", duration_ms: 20 },
      { step: "execute_tool:compound_workflow", duration_ms: 9 },
    ]);
    expect(mapped.map((step) => step.label)).toEqual([
      "Understanding request",
      "Drafting email",
    ]);
    expect(mapped.every((step) => step.detail == null)).toBe(true);
  });

  it("maps calendar tools to recruiter-facing steps", () => {
    const mapped = mapInternalTraceSteps([
      { step: "execute_tool:calendar.list_events", duration_ms: 5 },
      { step: "execute_tool:calendar.check_availability", duration_ms: 6 },
      { step: "execute_tool:calendar.create_event_request", duration_ms: 7 },
    ]);
    expect(mapped.map((step) => step.label)).toEqual([
      "Reading calendar",
      "Checking availability",
      "Preparing meeting",
    ]);
  });

  it("drops unknown or unsafe persisted traces", () => {
    const safe = sanitizeExecutionTrace([
      {
        key: "searching_the_web",
        label: "Searching the web",
        detail: "reason=hidden",
        duration_ms: 8,
      },
      {
        key: "hidden_reasoning",
        label: "Thinking about the prompt",
        duration_ms: 1,
      },
    ]);
    expect(safe).toEqual([
      {
        key: "searching_the_web",
        label: "Searching the web",
        detail: null,
        duration_ms: 8,
      },
    ]);
  });

  it("prefers persisted execution_trace on live chat responses", () => {
    const resp = {
      execution_trace: [
        {
          key: "reading_crm_context",
          label: "Reading CRM context",
          detail: null,
          duration_ms: 11,
        },
      ],
      trace_steps: [{ step: "classify_intent", duration_ms: 1 }],
    } as ChatResponse;
    expect(executionTraceFromChat(resp).map((step) => step.label)).toEqual([
      "Reading CRM context",
    ]);
  });

  it("historical messages without execution_trace render empty", () => {
    const msg = {
      execution_trace: undefined,
      tool_calls: [],
    } as unknown as MessageResponse;
    expect(executionTraceFromMessage(msg)).toEqual([]);
  });

  it("labels tools without leaking identifiers", () => {
    expect(toolBadgeLabel("rag.answer")).toBe("Knowledge");
    expect(toolBadgeLabel("calendar.create_event_request")).toBe("Calendar");
    expect(toolBadgeLabel("calendar.list_events")).toBe("Calendar");
    expect(toolBadgeLabel("mystery.tool")).toBe("Tool");
    expect(
      uniqueToolLabels([
        {
          tool_name: "email.draft",
          input_summary: "secret",
          output_summary: "out",
          duration_ms: 1,
        },
        {
          tool_name: "email.draft",
          input_summary: "secret",
          output_summary: "out",
          duration_ms: 2,
        },
      ]),
    ).toEqual(["Email"]);
  });

  it("rejects unsafe public text and token usage keys", () => {
    expect(isSafePublicText("Searching the web")).toBe(true);
    expect(isSafePublicText("Bearer token abc")).toBe(false);
    expect(isSafePublicText("See conv_abc123")).toBe(false);
    expect(
      publicUsageEntries({
        input_tokens: 12,
        output_tokens: 4,
        prompt_tokens: 12,
      }),
    ).toEqual([]);
  });
});
