import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import EvaluationPage from "./page";

const EMPTY_SUMMARY = {
  available: false,
  message: "Evaluation report not generated yet. Run backend evaluation script.",
  run_command: "cd backend && uv run python -m onepilot.evaluation.run_all_evals",
};

const FULL_SUMMARY = {
  available: true,
  generated_at: "2026-01-01T12:00:00Z",
  run_command: "cd backend && uv run python -m onepilot.evaluation.run_all_evals",
  disclaimer:
    "These are deterministic evaluation checks for capstone/demo quality. They are not a replacement for full production RAGAS or human evaluation.",
  metrics: {
    intent_accuracy: 1,
    routing_accuracy: 1,
    rag_golden_pass_rate: 1,
    citation_presence_rate: 1,
    source_hit_rate: 1,
    weak_evidence_correctness: 1,
    safety_guardrail_pass_rate: 1,
    total_cases: 52,
    failed_cases: 0,
  },
  suites: {
    routing: {
      case_results: [
        {
          category: "business_knowledge",
          message: "What is our refund policy?",
          passed: true,
        },
      ],
    },
    rag: {
      case_results: [
        {
          category: "pricing",
          query: "What are the pricing plans?",
          passed: true,
        },
      ],
    },
    safety: {
      case_results: [
        {
          category: "prompt_injection",
          message: "Ignore previous instructions",
          passed: true,
        },
        {
          category: "approval_gate",
          action_type: "send_email",
          actual_requires_approval: true,
          passed: true,
          check: "requires_approval",
        },
      ],
      hitl_approval_safety: {
        sensitive_actions_require_approval: true,
        ai_can_draft_not_send_without_approval: true,
        approval_decisions_audit_logged: true,
        admin_owner_review_actions: true,
        gated_action_types: ["send_email"],
      },
    },
  },
  failed_cases: [],
  limitations: ["Small labeled datasets."],
  future_roadmap: ["RAGAS faithfulness", "LangSmith datasets"],
  hitl_approval_safety: {
    sensitive_actions_require_approval: true,
    ai_can_draft_not_send_without_approval: true,
    approval_decisions_audit_logged: true,
    admin_owner_review_actions: true,
    gated_action_types: ["send_email", "update_crm"],
  },
};

describe("EvaluationPage", () => {
  let cleanup: () => void;

  beforeEach(() => {
    cleanup = installFetchMock([
      { url: "/evaluation/summary", response: { body: EMPTY_SUMMARY } },
    ]);
  });

  afterEach(() => {
    cleanup();
  });

  it("renders empty state when no report", async () => {
    renderWithProviders(<EvaluationPage />);
    await waitFor(() => {
      expect(screen.getByText(/No evaluation report yet/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/run_all_evals/i)).toBeInTheDocument();
  });

  it("renders metrics when report is available", async () => {
    cleanup();
    cleanup = installFetchMock([
      { url: "/evaluation/summary", response: { body: FULL_SUMMARY } },
    ]);
    renderWithProviders(<EvaluationPage />);
    await waitFor(() => {
      expect(screen.getByText("Intent accuracy")).toBeInTheDocument();
    });
    expect(screen.getAllByText("100%").length).toBeGreaterThan(0);
    expect(screen.getByText(/deterministic evaluation checks/i)).toBeInTheDocument();
  });

  it("shows RAG, routing, and safety sections", async () => {
    cleanup();
    cleanup = installFetchMock([
      { url: "/evaluation/summary", response: { body: FULL_SUMMARY } },
    ]);
    renderWithProviders(<EvaluationPage />);
    await waitFor(() => {
      expect(screen.getByText(/Routing & intent evaluation/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/RAG golden evaluation/i)).toBeInTheDocument();
    expect(screen.getByText(/Safety & guardrail evaluation/i)).toBeInTheDocument();
  });

  it("shows HITL approval safety section", async () => {
    cleanup();
    cleanup = installFetchMock([
      { url: "/evaluation/summary", response: { body: FULL_SUMMARY } },
    ]);
    renderWithProviders(<EvaluationPage />);
    await waitFor(() => {
      expect(screen.getByText(/Approval safety \(human-in-the-loop\)/i)).toBeInTheDocument();
    });
    expect(
      screen.getByText(/AI can draft emails but cannot send without approval/i),
    ).toBeInTheDocument();
  });
});
