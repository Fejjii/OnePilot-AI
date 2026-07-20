import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import {
  enableRouterUrlSync,
  navigationMocks,
  setMockNextLocation,
} from "@/test-utils/next-mocks";
import { PROMPT_SUGGESTIONS } from "@/components/domain/prompt-suggestions";
import WorkspacePage from "./page";

const CONV_NEW_DETAIL = {
  method: "GET" as const,
  url: "/conversations/conv_new",
  response: {
    body: {
      id: "conv_new",
      title: "New conversation",
      last_intent: "general_assistant",
      messages: [],
    },
  },
};

const EMPTY_CONVERSATIONS = {
  method: "GET" as const,
  url: "/conversations",
  response: { body: { items: [], total: 0 } },
};

const CHAT_RESPONSE = {
  conversation_id: "conv_new",
  message_id: "msg_a1",
  intent: "general_assistant",
  confidence: 0.8,
  final_response: "Here is a summary of recent activity.",
  citations: [],
  tool_calls: [],
  approval_required: false,
  approval_id: null,
  usage: {},
  trace_steps: [],
  safety_flags: [],
  trace_mode: "local",
  trace_id: "t1",
  trace_url: null,
  span_count: 1,
  detected_language: "en",
  response_language: "en",
  language_preference: "auto",
};

function providerDiagnostic(
  name: string,
  category: string,
  mode: string,
  healthy = true,
) {
  return {
    name,
    category,
    configured: true,
    healthy,
    active: true,
    fallback_used: mode === "fallback",
    mode,
    model: null,
    reason: null,
    last_checked_at: "2026-07-19T00:00:00Z",
    details: null,
  };
}

const MOCK_PROVIDERS = {
  method: "GET" as const,
  url: "/providers",
  response: {
    body: {
      providers: [
        providerDiagnostic("Gmail", "email", "mock"),
        providerDiagnostic("Google Calendar", "calendar", "mock"),
        providerDiagnostic("Qdrant", "vector", "local"),
      ],
      checked_at: "2026-07-19T00:00:00Z",
    },
  },
};

describe("WorkspacePage guided experience", () => {
  let restoreFetch: () => void = () => {};

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
    setMockNextLocation({ pathname: "/workspace", search: "" });
    enableRouterUrlSync();
    navigationMocks.replace.mockClear();
    navigationMocks.push.mockClear();
  });

  afterEach(() => {
    restoreFetch();
    window.localStorage.clear();
  });

  it("renders all suggested prompt chips in the empty state", async () => {
    restoreFetch = installFetchMock([EMPTY_CONVERSATIONS]);
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByText(/ask onepilot about this business/i),
      ).toBeInTheDocument();
    });

    const list = screen.getByRole("list", { name: /suggested prompts/i });
    for (const suggestion of PROMPT_SUGGESTIONS) {
      expect(
        within(list).getByRole("button", { name: suggestion.label }),
      ).toBeInTheDocument();
    }
    expect(
      screen.getByText(/wait for human approval/i),
    ).toBeInTheDocument();
  });

  it("submits the full prompt when a chip is clicked", async () => {
    let capturedBody: Record<string, unknown> | null = null;
    restoreFetch = installFetchMock([
      CONV_NEW_DETAIL,
      EMPTY_CONVERSATIONS,
      {
        method: "POST",
        url: "/chat",
        response: ({ body }) => {
          capturedBody = body as Record<string, unknown>;
          return { body: CHAT_RESPONSE };
        },
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    const chip = await screen.findByRole("button", {
      name: "Summarize business activity",
    });
    await user.click(chip);

    await waitFor(() => {
      expect(capturedBody?.message).toBe(
        "Summarize our recent business activity across leads, approvals, and conversations.",
      );
    });
    await waitFor(() => {
      expect(
        screen.getByText(/here is a summary of recent activity/i),
      ).toBeInTheDocument();
    });
  });

  it("supports keyboard activation of prompt chips", async () => {
    let capturedBody: Record<string, unknown> | null = null;
    restoreFetch = installFetchMock([
      CONV_NEW_DETAIL,
      EMPTY_CONVERSATIONS,
      {
        method: "POST",
        url: "/chat",
        response: ({ body }) => {
          capturedBody = body as Record<string, unknown>;
          return { body: CHAT_RESPONSE };
        },
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    const chip = await screen.findByRole("button", {
      name: "Review pending approvals",
    });
    chip.focus();
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(capturedBody?.message).toBe(
        "Which approvals are currently pending and what do they cover?",
      );
    });
  });

  it("shows simulated Gmail/Calendar and retrieval badges from provider diagnostics", async () => {
    restoreFetch = installFetchMock([EMPTY_CONVERSATIONS, MOCK_PROVIDERS]);
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByRole("status", { name: /workspace integration status/i }),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Gmail: Simulated")).toBeInTheDocument();
    expect(screen.getByText("Calendar: Simulated")).toBeInTheDocument();
    expect(
      screen.getByText("Knowledge retrieval: Fallback ready"),
    ).toBeInTheDocument();
  });

  it("labels missing Qdrant with in-memory fallback as Fallback ready", async () => {
    restoreFetch = installFetchMock([
      EMPTY_CONVERSATIONS,
      {
        method: "GET",
        url: "/providers",
        response: {
          body: {
            providers: [
              providerDiagnostic("Gmail", "email", "mock"),
              providerDiagnostic("Google Calendar", "calendar", "mock"),
              {
                ...providerDiagnostic("Qdrant", "vector", "missing", false),
                configured: false,
                active: false,
                fallback_used: true,
                details: { provider: "memory" },
              },
            ],
            checked_at: "2026-07-19T00:00:00Z",
          },
        },
      },
    ]);
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByText("Knowledge retrieval: Fallback ready"),
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByText("Knowledge retrieval: Unavailable"),
    ).not.toBeInTheDocument();
  });

  it("labels live integrations as Live", async () => {
    restoreFetch = installFetchMock([
      EMPTY_CONVERSATIONS,
      {
        method: "GET",
        url: "/providers",
        response: {
          body: {
            providers: [
              providerDiagnostic("Gmail", "email", "live"),
              providerDiagnostic("Google Calendar", "calendar", "live"),
              providerDiagnostic("Qdrant", "vector", "live"),
            ],
            checked_at: "2026-07-19T00:00:00Z",
          },
        },
      },
    ]);
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText("Gmail: Live")).toBeInTheDocument();
    });
    expect(screen.getByText("Calendar: Live")).toBeInTheDocument();
    expect(
      screen.getByText("Knowledge retrieval: Vector search"),
    ).toBeInTheDocument();
  });

  it("shows demo-mode badge and simulated-actions messaging in demo sessions", async () => {
    window.localStorage.setItem("onepilot_demo_mode", "1");
    restoreFetch = installFetchMock([EMPTY_CONVERSATIONS, MOCK_PROVIDERS]);
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByText(/demo mode — actions simulated/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText(/no real emails or calendar events are ever created/i),
    ).toBeInTheDocument();
  });

  it("renders no status strip when diagnostics are unavailable and not in demo mode", async () => {
    restoreFetch = installFetchMock([EMPTY_CONVERSATIONS]);
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByText(/ask onepilot about this business/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("status", { name: /workspace integration status/i }),
    ).not.toBeInTheDocument();
  });

  it("shows an inline recoverable error with retry when send fails", async () => {
    let chatCalls = 0;
    restoreFetch = installFetchMock([
      CONV_NEW_DETAIL,
      EMPTY_CONVERSATIONS,
      {
        method: "POST",
        url: "/chat",
        response: () => {
          chatCalls += 1;
          if (chatCalls === 1) {
            return {
              status: 500,
              body: { error: "internal_error", message: "Upstream failure" },
            };
          }
          return { body: CHAT_RESPONSE };
        },
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    const textarea = await screen.findByPlaceholderText(
      /ask the ai assistant/i,
    );
    await user.type(textarea, "summarize activity");
    await user.click(screen.getByRole("button", { name: /send/i }));

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText(/message not sent/i)).toBeInTheDocument();
    expect(within(alert).getByText(/upstream failure/i)).toBeInTheDocument();

    await user.click(within(alert).getByRole("button", { name: /try again/i }));

    await waitFor(() => {
      expect(chatCalls).toBe(2);
      expect(
        screen.getByText(/here is a summary of recent activity/i),
      ).toBeInTheDocument();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a session-expired state on 401 and routes to sign-in", async () => {
    restoreFetch = installFetchMock([
      CONV_NEW_DETAIL,
      EMPTY_CONVERSATIONS,
      {
        method: "POST",
        url: "/chat",
        response: {
          status: 401,
          body: { error: "unauthorized", message: "Token expired" },
        },
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    const textarea = await screen.findByPlaceholderText(
      /ask the ai assistant/i,
    );
    await user.type(textarea, "hello");
    await user.click(screen.getByRole("button", { name: /send/i }));

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText(/session expired/i)).toBeInTheDocument();

    await user.click(
      within(alert).getByRole("button", { name: /go to sign-in/i }),
    );
    expect(navigationMocks.push).toHaveBeenCalledWith("/login");
    expect(window.localStorage.getItem("onepilot_token")).toBeNull();
  });

  it("shows an empty-result notice when the agent returns no text", async () => {
    restoreFetch = installFetchMock([
      CONV_NEW_DETAIL,
      EMPTY_CONVERSATIONS,
      {
        method: "POST",
        url: "/chat",
        response: { body: { ...CHAT_RESPONSE, final_response: "" } },
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    const textarea = await screen.findByPlaceholderText(
      /ask the ai assistant/i,
    );
    await user.type(textarea, "unusual request");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/completed without a text answer/i),
      ).toBeInTheDocument();
    });
  });

  it("replaces the empty state and chips once a chip prompt resolves", async () => {
    restoreFetch = installFetchMock([
      CONV_NEW_DETAIL,
      EMPTY_CONVERSATIONS,
      { method: "POST", url: "/chat", response: { body: CHAT_RESPONSE } },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    const chip = await screen.findByRole("button", { name: "Analyze leads" });
    await user.click(chip);

    await waitFor(() => {
      expect(
        screen.getByText(/here is a summary of recent activity/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("list", { name: /suggested prompts/i }),
    ).not.toBeInTheDocument();
  });
});
