import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import WorkspacePage from "./page";

const CHAT_RESPONSE = {
  conversation_id: "conv_new",
  message_id: "msg_a1",
  intent: "knowledge_search",
  confidence: 0.85,
  final_response: "Here is what I found in NovaEdge docs.",
  citations: [
    {
      document_id: "doc_1",
      document_title: "NovaEdge Escalation Policy",
      section: "Tiers",
      chunk_text: "Tier 1 responds within 4 hours…",
      relevance_score: 0.92,
    },
  ],
  tool_calls: [],
  approval_required: false,
  approval_id: null,
  usage: { input_tokens: 120, output_tokens: 80 },
  trace_steps: [{ step: "router", detail: "intent=knowledge_search", intent: null, duration_ms: 4 }],
  safety_flags: [],
};

describe("WorkspacePage", () => {
  let restoreFetch: () => void;

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/conversations",
        response: { body: { items: [], total: 0 } },
      },
      {
        method: "POST",
        url: "/chat",
        response: { body: CHAT_RESPONSE },
      },
    ]);
  });

  afterEach(() => {
    restoreFetch();
    window.localStorage.clear();
  });

  it("submits a message and shows the assistant response with citations", async () => {
    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /ai workspace/i }),
      ).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/ask the ai assistant/i);
    await user.type(textarea, "What is the escalation policy?");
    await user.click(screen.getByRole("button", { name: /send/i }));

    // Pending user bubble appears immediately.
    expect(
      screen.getByText("What is the escalation policy?"),
    ).toBeInTheDocument();

    // After mutation resolves, citation should appear in the details panel.
    await waitFor(() => {
      expect(
        screen.getByText(/NovaEdge Escalation Policy/i),
      ).toBeInTheDocument();
    });
  });
});
