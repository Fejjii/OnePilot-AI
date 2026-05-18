import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import {
  blockRouterUrlSync,
  enableRouterUrlSync,
  navigationMocks,
  setMockNextLocation,
} from "@/test-utils/next-mocks";
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
  trace_steps: [
    { step: "router", detail: "intent=knowledge_search", intent: null, duration_ms: 4 },
  ],
  safety_flags: [],
  trace_mode: "local",
  trace_id: "local_trace_123",
  trace_url: null,
  span_count: 3,
};

const CONVERSATION_KNOWLEDGE = {
  id: "conv_knowledge",
  title: "What services does NovaEdge Solution…",
  last_intent: "knowledge_search",
  messages: [
    {
      id: "msg_user_k",
      role: "user",
      content: "What services does NovaEdge offer?",
      intent: null,
      confidence: 0,
      citations: [],
      tool_calls: [],
      created_at: "2024-01-01T00:00:00Z",
    },
    {
      id: "msg_k1",
      role: "assistant",
      content: "NovaEdge provides managed IT and security services.",
      intent: "knowledge_search",
      confidence: 0.88,
      citations: [
        {
          document_id: "doc_services",
          document_title: "NovaEdge Services Overview",
          section: "Overview",
          chunk_text: "Managed IT, security, and cloud…",
          relevance_score: 0.9,
        },
      ],
      tool_calls: [
        {
          tool_name: "knowledge.search",
          input_summary: "NovaEdge services",
          output_summary: "3 chunks retrieved",
          duration_ms: 120,
        },
      ],
      created_at: "2024-01-01T00:00:01Z",
      trace_mode: "local",
      trace_id: "local_k",
      trace_url: null,
    },
  ],
};

const CONVERSATION_GENERAL = {
  id: "conv_general",
  title: "General help chat",
  last_intent: "general_assistant",
  messages: [
    {
      id: "msg_user_g",
      role: "user",
      content: "What can you do?",
      intent: null,
      confidence: 0,
      citations: [],
      tool_calls: [],
      created_at: "2024-01-02T00:00:00Z",
    },
    {
      id: "msg_g1",
      role: "assistant",
      content: "I can help with general questions.",
      intent: "general_assistant",
      confidence: 0.75,
      citations: [],
      tool_calls: [
        {
          tool_name: "chat.general",
          input_summary: "What can you do?",
          output_summary: "Capability overview",
          duration_ms: 40,
        },
      ],
      created_at: "2024-01-02T00:00:01Z",
      trace_mode: "local",
    },
  ],
};

const CONVERSATION_LIST = {
  items: [
    {
      id: "conv_knowledge",
      title: CONVERSATION_KNOWLEDGE.title,
      last_intent: "knowledge_search",
      message_count: 2,
      last_message_at: "2024-01-01T00:00:01Z",
      updated_at: "2024-01-01T00:00:01Z",
    },
    {
      id: "conv_general",
      title: CONVERSATION_GENERAL.title,
      last_intent: "general_assistant",
      message_count: 2,
      last_message_at: "2024-01-02T00:00:01Z",
      updated_at: "2024-01-02T00:00:01Z",
    },
  ],
  total: 2,
};

function installTwoConversationMocks() {
  return installFetchMock([
    {
      method: "GET",
      url: "/conversations/conv_knowledge",
      response: { body: CONVERSATION_KNOWLEDGE },
    },
    {
      method: "GET",
      url: "/conversations/conv_general",
      response: { body: CONVERSATION_GENERAL },
    },
    {
      method: "GET",
      url: "/conversations",
      response: { body: CONVERSATION_LIST },
    },
  ]);
}

describe("WorkspacePage", () => {
  let restoreFetch: () => void;

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
    setMockNextLocation({ pathname: "/workspace", search: "" });
    enableRouterUrlSync();
    navigationMocks.replace.mockClear();
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/conversations/conv_new",
        response: {
          body: {
            id: "conv_new",
            title: "What is the escalation policy?",
            last_intent: "knowledge_search",
            messages: [
              {
                id: "msg_user1",
                role: "user",
                content: "What is the escalation policy?",
                intent: null,
                confidence: 0,
                citations: [],
                tool_calls: [],
                created_at: "2024-01-01T00:00:00Z",
              },
              {
                id: "msg_a1",
                role: "assistant",
                content: CHAT_RESPONSE.final_response,
                intent: CHAT_RESPONSE.intent,
                confidence: CHAT_RESPONSE.confidence,
                citations: CHAT_RESPONSE.citations,
                tool_calls: CHAT_RESPONSE.tool_calls,
                created_at: "2024-01-01T00:00:01Z",
                trace_mode: "local",
                trace_id: "local_trace_123",
                trace_url: null,
              },
            ],
          },
        },
      },
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

    expect(
      screen.getByText("What is the escalation policy?"),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByText(/NovaEdge Escalation Policy/i),
      ).toBeInTheDocument();
    });
  });

  it("displays trace mode for local tracing", async () => {
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

    await waitFor(() => {
      expect(screen.getByText(/trace mode/i)).toBeInTheDocument();
      expect(screen.getByText(/local/i)).toBeInTheDocument();
    });

    expect(
      screen.queryByText(/open langsmith trace/i),
    ).not.toBeInTheDocument();
  });

  it("displays trace mode with LangSmith URL when available", async () => {
    const langsmithResponse = {
      ...CHAT_RESPONSE,
      trace_mode: "langsmith",
      trace_url: "https://smith.langchain.com/public/12345",
    };

    restoreFetch();
    restoreFetch = installFetchMock([
      {
        method: "POST",
        url: "/chat",
        response: { body: langsmithResponse },
      },
      {
        method: "GET",
        url: "/conversations",
        response: { body: { items: [], total: 0 } },
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /ai workspace/i }),
      ).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/ask the ai assistant/i);
    await user.type(textarea, "test langsmith trace");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText(/trace mode/i)).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /open langsmith trace/i }),
      ).toBeInTheDocument();
    });
  });

  it("handles old messages without trace metadata gracefully", async () => {
    const oldConversation = {
      id: "conv_old",
      title: "Old conversation",
      last_intent: "general_assistant",
      messages: [
        {
          id: "msg_user_old",
          role: "user",
          content: "Old message",
          intent: null,
          confidence: 0,
          citations: [],
          tool_calls: [],
          created_at: "2023-01-01T00:00:00Z",
        },
        {
          id: "msg_assistant_old",
          role: "assistant",
          content: "Old response without trace metadata",
          intent: "general_assistant",
          confidence: 0.9,
          citations: [],
          tool_calls: [],
          created_at: "2023-01-01T00:00:01Z",
        },
      ],
    };

    restoreFetch();
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/conversations/conv_old",
        response: { body: oldConversation },
      },
      {
        method: "GET",
        url: "/conversations",
        response: {
          body: {
            items: [
              {
                id: "conv_old",
                title: "Old conversation",
                last_intent: "general_assistant",
                message_count: 2,
                last_message_at: "2023-01-01T00:00:01Z",
                updated_at: "2023-01-01T00:00:01Z",
              },
            ],
            total: 1,
          },
        },
      },
    ]);

    setMockNextLocation({ search: "?conversation=conv_old" });
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /ai workspace/i }),
      ).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText(/old conversation/i)).toBeInTheDocument();
    });
  });

  it("New Conversation clears messages and response details", async () => {
    restoreFetch();
    restoreFetch = installTwoConversationMocks();

    setMockNextLocation({ search: "?conversation=conv_general" });
    const user = userEvent.setup();
    const { rerender } = renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText(/chat\.general/i)).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", { name: /new conversation/i }),
    );

    await waitFor(() => {
      expect(navigationMocks.replace).toHaveBeenCalled();
    });

    setMockNextLocation({ pathname: "/workspace", search: "" });
    rerender(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText(/no response yet/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/chat\.general/i)).not.toBeInTheDocument();
    expect(screen.getByText(/ready when you are/i)).toBeInTheDocument();
  });

  it("switching from general to knowledge conversation updates response details", async () => {
    restoreFetch();
    restoreFetch = installTwoConversationMocks();

    setMockNextLocation({ search: "?conversation=conv_general" });
    const { rerender } = renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText(/chat\.general/i)).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/NovaEdge Services Overview/i),
    ).not.toBeInTheDocument();

    setMockNextLocation({ search: "?conversation=conv_knowledge" });
    rerender(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByText(/NovaEdge Services Overview/i),
      ).toBeInTheDocument();
    });
    expect(screen.queryByText(/chat\.general/i)).not.toBeInTheDocument();
    expect(screen.getByText(/knowledge\.search/i)).toBeInTheDocument();
  });

  it("switching from knowledge to general conversation updates trace tools", async () => {
    restoreFetch();
    restoreFetch = installTwoConversationMocks();

    setMockNextLocation({ search: "?conversation=conv_knowledge" });
    const { rerender } = renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByText(/NovaEdge Services Overview/i),
      ).toBeInTheDocument();
    });

    setMockNextLocation({ search: "?conversation=conv_general" });
    rerender(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText(/chat\.general/i)).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/NovaEdge Services Overview/i),
    ).not.toBeInTheDocument();
  });

  it("sidebar selection updates URL and response details for that conversation", async () => {
    restoreFetch();
    restoreFetch = installTwoConversationMocks();

    setMockNextLocation({ search: "?conversation=conv_general" });
    const user = userEvent.setup();
    const { rerender } = renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText(/chat\.general/i)).toBeInTheDocument();
    });

    await user.click(screen.getByText(/What services does NovaEdge Solution/i));

    expect(navigationMocks.replace).toHaveBeenCalledWith(
      expect.stringContaining("conversation=conv_knowledge"),
      expect.objectContaining({ scroll: false }),
    );

    setMockNextLocation({ search: "?conversation=conv_knowledge" });
    rerender(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByText(/NovaEdge Services Overview/i),
      ).toBeInTheDocument();
    });
    expect(screen.queryByText(/chat\.general/i)).not.toBeInTheDocument();
  });

  it("does not show stale in-flight response after switching conversations", async () => {
    restoreFetch();
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/conversations/conv_knowledge",
        response: { body: CONVERSATION_KNOWLEDGE },
      },
      {
        method: "GET",
        url: "/conversations/conv_general",
        response: { body: CONVERSATION_GENERAL },
      },
      {
        method: "GET",
        url: "/conversations",
        response: { body: CONVERSATION_LIST },
      },
      {
        method: "POST",
        url: "/chat",
        response: {
          body: {
            ...CHAT_RESPONSE,
            conversation_id: "conv_knowledge",
            message_id: "msg_new_g",
            intent: "general_assistant",
            final_response: "Stale general reply",
            citations: [],
            tool_calls: [
              {
                tool_name: "chat.general",
                input_summary: "hi",
                output_summary: "out",
                duration_ms: 1,
              },
            ],
            trace_steps: [
              {
                step: "router",
                detail: "message_class=capability_or_help route=general_chat",
                intent: null,
                duration_ms: 2,
              },
            ],
          },
        },
      },
    ]);

    setMockNextLocation({ search: "?conversation=conv_knowledge" });
    const user = userEvent.setup();
    const { rerender } = renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(
        screen.getByText(/NovaEdge Services Overview/i),
      ).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/ask the ai assistant/i);
    await user.type(textarea, "trigger stale send");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await user.click(screen.getByText(/General help chat/i));

    setMockNextLocation({ search: "?conversation=conv_general" });
    rerender(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText(/chat\.general/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Stale general reply/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/message_class=capability_or_help/i),
    ).not.toBeInTheDocument();
  });

  it("New Conversation clears UI immediately before URL searchParams update", async () => {
    restoreFetch();
    restoreFetch = installTwoConversationMocks();

    setMockNextLocation({ search: "?conversation=conv_general" });
    blockRouterUrlSync();

    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText(/chat\.general/i)).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", { name: /new conversation/i }),
    );

    await waitFor(() => {
      expect(screen.getByText(/no response yet/i)).toBeInTheDocument();
      expect(screen.getByText(/ready when you are/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/chat\.general/i)).not.toBeInTheDocument();
    expect(navigationMocks.replace).toHaveBeenCalledWith(
      "/workspace",
      expect.objectContaining({ scroll: false }),
    );
  });

  it("sidebar switch updates center and details before URL searchParams update", async () => {
    restoreFetch();
    restoreFetch = installTwoConversationMocks();

    setMockNextLocation({ search: "?conversation=conv_general" });
    blockRouterUrlSync();

    const user = userEvent.setup();
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText(/chat\.general/i)).toBeInTheDocument();
    });

    await user.click(screen.getByText(/What services does NovaEdge Solution/i));

    await waitFor(() => {
      expect(
        screen.getByText(/NovaEdge Services Overview/i),
      ).toBeInTheDocument();
    });
    expect(screen.queryByText(/chat\.general/i)).not.toBeInTheDocument();
    expect(screen.getByText(/knowledge\.search/i)).toBeInTheDocument();
  });

  it("does not render conversation detail when cached data id mismatches active id", async () => {
    restoreFetch();
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/conversations/conv_knowledge",
        response: {
          body: {
            ...CONVERSATION_GENERAL,
            id: "conv_general",
          },
        },
      },
      {
        method: "GET",
        url: "/conversations",
        response: { body: CONVERSATION_LIST },
      },
    ]);

    setMockNextLocation({ search: "?conversation=conv_knowledge" });
    renderWithProviders(<WorkspacePage />);

    await waitFor(() => {
      expect(screen.getByText(/no response yet/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/chat\.general/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/NovaEdge Services Overview/i),
    ).not.toBeInTheDocument();
  });

  it("first message after New Conversation creates conversation and updates URL", async () => {
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

    await waitFor(() => {
      expect(navigationMocks.replace).toHaveBeenCalledWith(
        expect.stringContaining("conversation=conv_new"),
        expect.objectContaining({ scroll: false }),
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText(/NovaEdge Escalation Policy/i),
      ).toBeInTheDocument();
    });
  });
});
