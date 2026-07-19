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

const EMPTY_CONVERSATIONS = {
  method: "GET" as const,
  url: "/conversations",
  response: { body: { items: [], total: 0 } },
};

const CONVERSATIONS_WITH_ONE = {
  method: "GET" as const,
  url: "/conversations",
  response: {
    body: {
      items: [
        {
          id: "conv_1",
          title: "Prior conversation",
          last_intent: "general_assistant",
          updated_at: "2026-07-19T00:00:00Z",
          created_at: "2026-07-19T00:00:00Z",
        },
      ],
      total: 1,
    },
  },
};

const CONV_DETAIL = {
  method: "GET" as const,
  url: "/conversations/conv_1",
  response: {
    body: {
      id: "conv_1",
      title: "Prior conversation",
      last_intent: "general_assistant",
      messages: [
        {
          id: "msg_u",
          role: "user",
          content: "Hello",
          intent: null,
          confidence: 0,
          citations: [],
          tool_calls: [],
          created_at: "2026-07-19T00:00:00Z",
        },
        {
          id: "msg_a",
          role: "assistant",
          content: "Hi from OnePilot.",
          intent: "general_assistant",
          confidence: 0.9,
          citations: [],
          tool_calls: [],
          created_at: "2026-07-19T00:00:01Z",
        },
      ],
    },
  },
};

const MOCK_PROVIDERS = {
  method: "GET" as const,
  url: "/providers",
  response: {
    body: {
      providers: [
        {
          name: "Gmail",
          category: "email",
          configured: true,
          healthy: true,
          active: true,
          fallback_used: false,
          mode: "mock",
          model: null,
          reason: null,
          last_checked_at: "2026-07-19T00:00:00Z",
          details: null,
        },
        {
          name: "Google Calendar",
          category: "calendar",
          configured: true,
          healthy: true,
          active: true,
          fallback_used: false,
          mode: "mock",
          model: null,
          reason: null,
          last_checked_at: "2026-07-19T00:00:00Z",
          details: null,
        },
        {
          name: "Qdrant",
          category: "vector",
          configured: false,
          healthy: true,
          active: true,
          fallback_used: true,
          mode: "local",
          model: null,
          reason: null,
          last_checked_at: "2026-07-19T00:00:00Z",
          details: null,
        },
      ],
      checked_at: "2026-07-19T00:00:00Z",
    },
  },
};

describe("WorkspacePage mobile navigation", () => {
  let restoreFetch: () => void = () => {};

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
    setMockNextLocation({ pathname: "/workspace", search: "" });
    enableRouterUrlSync();
    navigationMocks.replace.mockClear();
  });

  afterEach(() => {
    restoreFetch();
    window.localStorage.clear();
  });

  it("keeps the chat composer and prompt chips available on the Chat panel", async () => {
    restoreFetch = installFetchMock([EMPTY_CONVERSATIONS, MOCK_PROVIDERS]);
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByText(/ask onepilot about this business/i),
      ).toBeInTheDocument();
    });

    expect(screen.getByRole("textbox", { name: /message/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send message/i })).toBeInTheDocument();

    const list = screen.getByRole("list", { name: /suggested prompts/i });
    expect(
      within(list).getByRole("button", {
        name: PROMPT_SUGGESTIONS[0].label,
      }),
    ).toBeInTheDocument();
  });

  it("switches between Chat, History, and Details panels", async () => {
    restoreFetch = installFetchMock([
      CONV_DETAIL,
      CONVERSATIONS_WITH_ONE,
      MOCK_PROVIDERS,
    ]);
    setMockNextLocation({ search: "?conversation=conv_1" });
    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText("Hi from OnePilot.")).toBeInTheDocument();
    });

    const tablist = screen.getByRole("tablist", { name: /workspace panels/i });
    expect(tablist).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /history/i }));
    expect(screen.getByRole("tab", { name: /history/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(
      await screen.findByRole("button", { name: "Prior conversation" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /details/i }));
    expect(screen.getByRole("tab", { name: /details/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByText(/response details/i)).toBeInTheDocument();
    expect(screen.getByText(/ai transparency/i)).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /^chat$/i }));
    expect(screen.getByRole("textbox", { name: /message/i })).toBeInTheDocument();
    expect(screen.getByText("Hi from OnePilot.")).toBeInTheDocument();
  });

  it("returns to Chat after selecting a conversation from History", async () => {
    restoreFetch = installFetchMock([
      CONV_DETAIL,
      CONVERSATIONS_WITH_ONE,
      MOCK_PROVIDERS,
    ]);
    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    await user.click(await screen.findByRole("tab", { name: /history/i }));
    await user.click(
      await screen.findByRole("button", { name: "Prior conversation" }),
    );

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /^chat$/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });
    expect(screen.getByRole("textbox", { name: /message/i })).toBeInTheDocument();
  });

  it("preserves desktop three-panel class hooks for large screens", async () => {
    restoreFetch = installFetchMock([EMPTY_CONVERSATIONS, MOCK_PROVIDERS]);
    const { container } = renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByRole("tablist", { name: /workspace panels/i }),
      ).toBeInTheDocument();
    });

    expect(
      container.querySelector("#workspace-panel-history")?.className,
    ).toMatch(/lg:flex/);
    expect(
      container.querySelector("#workspace-panel-chat")?.className,
    ).toMatch(/lg:flex/);
    expect(
      container.querySelector("#workspace-panel-details")?.className,
    ).toMatch(/lg:flex/);

    const grid = container.querySelector(".lg\\:grid-cols-\\[280px_1fr_320px\\]");
    expect(grid).toBeTruthy();
  });

  it("surfaces approval review access from the chat column", async () => {
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/conversations/conv_new",
        response: {
          body: {
            id: "conv_new",
            title: "Draft",
            last_intent: "email_drafting",
            messages: [],
          },
        },
      },
      EMPTY_CONVERSATIONS,
      MOCK_PROVIDERS,
      {
        method: "POST",
        url: "/chat",
        response: {
          body: {
            conversation_id: "conv_new",
            message_id: "msg_a1",
            intent: "email_drafting",
            confidence: 0.8,
            final_response: "Draft prepared for approval.",
            citations: [],
            tool_calls: [],
            approval_required: true,
            approval_id: "apr_1",
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
          },
        },
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    const chip = await screen.findByRole("button", {
      name: "Draft a follow-up email",
    });
    await user.click(chip);

    const approvalLink = await screen.findByRole("link", {
      name: /review/i,
    });
    expect(approvalLink).toHaveAttribute("href", "/approvals?focus=apr_1");
  });
});
