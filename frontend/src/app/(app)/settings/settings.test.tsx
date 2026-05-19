import { screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import SettingsPage from "./page";
import { renderWithProviders } from "@/test-utils/render-with-providers";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: {
      user: { email: "test@example.com" },
      organization: {
        name: "Test Org",
        slug: "test-org",
        created_at: "2024-01-01T00:00:00Z",
      },
      role: "admin",
      plan: "free",
    },
    refresh: vi.fn(),
  }),
  isAdminRole: (role: string) => role === "admin" || role === "owner",
}));

vi.mock("@/lib/queries", () => ({
  useRuntimeModelConfig: () => ({
    isLoading: false,
    data: {
      chat_model: "gpt-4o-mini",
      embedding_model: "text-embedding-3-small",
      speech_model: "whisper-1",
      llm_status: "live",
      embeddings_status: "live",
      speech_status: "live",
      fallback_active: false,
      provider_mode: "mixed",
      cost_note:
        "OpenAI chat and embedding usage is metered per token; speech transcription is metered per audio minute.",
      configuration_source: "environment",
    },
  }),
  useCurrentPlan: () => ({
    isLoading: false,
    data: {
      plan: {
        name: "Free Plan",
        monthly_price_cents: 0,
        limits: {
          chat_messages: 100,
          rag_queries: 50,
          document_uploads: 10,
          storage_mb: 100,
          email_drafts: 20,
          lead_workflows: 5,
          tool_calls: 100,
          users: 3,
        },
      },
      subscription: {
        status: "active",
        renews_at: "2024-12-31T00:00:00Z",
      },
    },
  }),
  useProviderDiagnostics: () => ({
    isLoading: false,
    data: {
      providers: [
        {
          name: "OpenAI LLM",
          category: "llm",
          configured: true,
          healthy: true,
          active: true,
          fallback_used: false,
          mode: "live",
          model: "gpt-4o-mini",
          reason: null,
          last_checked_at: "2024-01-01T00:00:00Z",
          details: { provider: "openai" },
        },
        {
          name: "OpenAI Embeddings",
          category: "embeddings",
          configured: true,
          healthy: true,
          active: true,
          fallback_used: false,
          mode: "live",
          model: "text-embedding-3-small",
          reason: null,
          last_checked_at: "2024-01-01T00:00:00Z",
          details: { provider: "openai", dimension: 1536 },
        },
        {
          name: "Qdrant",
          category: "vector",
          configured: false,
          healthy: false,
          active: false,
          fallback_used: true,
          mode: "missing",
          model: null,
          reason: "QDRANT_URL not set",
          last_checked_at: "2024-01-01T00:00:00Z",
          details: { provider: "memory" },
        },
        {
          name: "Redis",
          category: "cache",
          configured: false,
          healthy: false,
          active: false,
          fallback_used: true,
          mode: "missing",
          model: null,
          reason: "REDIS_URL not set",
          last_checked_at: "2024-01-01T00:00:00Z",
          details: { fallback: "Process-local cache" },
        },
        {
          name: "Postgres",
          category: "database",
          configured: true,
          healthy: true,
          active: true,
          fallback_used: false,
          mode: "live",
          model: null,
          reason: null,
          last_checked_at: "2024-01-01T00:00:00Z",
          details: null,
        },
        {
          name: "LangSmith",
          category: "observability",
          configured: false,
          healthy: true,
          active: false,
          fallback_used: true,
          mode: "missing",
          model: null,
          reason: "LANGSMITH_API_KEY not set",
          last_checked_at: "2024-01-01T00:00:00Z",
          details: { fallback: "Local trace steps" },
        },
        {
          name: "Gmail",
          category: "email",
          configured: false,
          healthy: true,
          active: false,
          fallback_used: true,
          mode: "mock",
          model: null,
          reason: "GMAIL_CREDENTIALS_JSON not set, using mock provider",
          last_checked_at: "2024-01-01T00:00:00Z",
          details: { mock: true },
        },
        {
          name: "HubSpot",
          category: "crm",
          configured: false,
          healthy: true,
          active: false,
          fallback_used: true,
          mode: "mock",
          model: null,
          reason: "HUBSPOT_API_KEY not set, using mock provider",
          last_checked_at: "2024-01-01T00:00:00Z",
          details: { mock: true },
        },
      ],
      checked_at: "2024-01-01T00:00:00Z",
    },
  }),
}));

describe("SettingsPage", () => {
  it("renders AI model configuration section", async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("AI Model Configuration")).toBeInTheDocument();
      expect(screen.getByText("OPENAI_MODEL")).toBeInTheDocument();
      expect(screen.getByText("OPENAI_EMBEDDING_MODEL")).toBeInTheDocument();
      expect(screen.getByText("OPENAI_SPEECH_MODEL")).toBeInTheDocument();
      expect(screen.getByText(/metered per token/i)).toBeInTheDocument();
    });
  });

  it("explains environment-driven model configuration", async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/Model configuration is environment driven/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Editable model selection is planned/i),
      ).toBeInTheDocument();
    });
  });

  it("shows mocked provider and env-var copy", async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(
        screen.getAllByText(/Provider keys are configured through environment variables/i)
          .length,
      ).toBeGreaterThan(0);
      expect(
        screen.getAllByText(/Mock providers are used for capstone safe demos/i).length,
      ).toBeGreaterThan(0);
    });
  });

  it("describes LangSmith local and live tracing", async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/LangSmith supports live cloud tracing or local trace steps/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/LangSmith local trace steps when API key is set/i),
      ).toBeInTheDocument();
    });
  });

  it("renders provider diagnostics section", async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Runtime & Provider Diagnostics")).toBeInTheDocument();
    });
  });

  it("displays provider cards with correct statuses", async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("OpenAI LLM")).toBeInTheDocument();
      expect(screen.getByText("OpenAI Embeddings")).toBeInTheDocument();
      expect(screen.getByText("Qdrant")).toBeInTheDocument();
      expect(screen.getByText("Redis")).toBeInTheDocument();
    });

    const liveBadges = screen.getAllByText("Live");
    expect(liveBadges.length).toBeGreaterThan(0);

    const missingBadges = screen.getAllByText("Missing");
    expect(missingBadges.length).toBeGreaterThan(0);

    const mockBadges = screen.getAllByText("Mock");
    expect(mockBadges.length).toBeGreaterThan(0);
  });

  it("shows provider mode explanations", async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/Real provider configured and operational/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/Capstone-safe demo adapters/i)).toBeInTheDocument();
      expect(screen.getByText(/Deterministic in-process substitute/i)).toBeInTheDocument();
    });
  });

  it("displays last checked timestamp", async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Last checked:/i)).toBeInTheDocument();
    });
  });

  it("shows configured and healthy status icons", async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("OpenAI LLM")).toBeInTheDocument();
    });

    const configuredLabels = screen.getAllByText("Configured:");
    expect(configuredLabels.length).toBeGreaterThan(0);

    const healthyLabels = screen.getAllByText("Healthy:");
    expect(healthyLabels.length).toBeGreaterThan(0);
  });

  it("displays provider reasons when present", async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText(/QDRANT_URL not set/i)).toBeInTheDocument();
      expect(screen.getByText(/REDIS_URL not set/i)).toBeInTheDocument();
      expect(screen.getByText(/LANGSMITH_API_KEY not set/i)).toBeInTheDocument();
    });
  });
});
