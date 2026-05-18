import { screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import DashboardPage from "./page";
import { renderWithProviders } from "@/test-utils/render-with-providers";

vi.mock("@/lib/queries", () => ({
  useConversations: () => ({
    isLoading: false,
    isError: false,
    data: {
      items: [],
      total: 0,
    },
  }),
  useDocuments: () => ({
    isLoading: false,
    data: { total: 0 },
  }),
  useLeads: () => ({
    isLoading: false,
    data: { total: 0 },
  }),
  useApprovals: () => ({
    isLoading: false,
    data: { pending_count: 0 },
  }),
  useUsageSummary: () => ({
    isLoading: false,
    isError: false,
    data: {
      quotas: [],
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
          name: "Qdrant",
          category: "vector",
          configured: false,
          healthy: false,
          active: false,
          fallback_used: true,
          mode: "fallback",
          model: null,
          reason: "QDRANT_URL not set",
          last_checked_at: "2024-01-01T00:00:00Z",
          details: { provider: "memory" },
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
      ],
      checked_at: "2024-01-01T00:00:00Z",
    },
  }),
}));

describe("DashboardPage", () => {
  it("renders provider diagnostics card", async () => {
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Provider diagnostics")).toBeInTheDocument();
    });
  });

  it("displays mixed provider mode warning when applicable", async () => {
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/Mixed provider modes/i) ||
          screen.getByText(/Some providers are using fallback/i) ||
          screen.getByText(/some SaaS providers are using mock adapters/i)
      ).toBeInTheDocument();
    });
  });

  it("shows core provider status", async () => {
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("OpenAI LLM")).toBeInTheDocument();
      expect(screen.getByText("Qdrant")).toBeInTheDocument();
    });
  });

  it("displays SaaS provider status in collapsible section", async () => {
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Show SaaS provider status/i)).toBeInTheDocument();
    });
  });

  it("links to settings page for detailed view", async () => {
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      const links = screen.getAllByRole("link", { name: /View details/i });
      expect(links.length).toBeGreaterThan(0);
    });
  });
});
