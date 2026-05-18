import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import DashboardPage from "./page";

const HEALTH = {
  status: "ok",
  app: "OnePilot AI",
  version: "0.1.0",
  env: "test",
  providers: {
    openai: false,
    qdrant: true,
    redis: false,
    langsmith: false,
    database: true,
  },
};

const PROVIDER_DIAGNOSTICS = {
  providers: [
    {
      name: "OpenAI LLM",
      category: "llm",
      configured: false,
      healthy: false,
      active: false,
      fallback_used: true,
      mode: "fallback",
      model: "fallback-v1",
      reason: "OPENAI_API_KEY not set",
      last_checked_at: "2024-01-01T00:00:00Z",
      details: { provider: "fallback" },
    },
    {
      name: "Qdrant",
      category: "vector",
      configured: true,
      healthy: true,
      active: true,
      fallback_used: false,
      mode: "live",
      model: null,
      reason: null,
      last_checked_at: "2024-01-01T00:00:00Z",
      details: { provider: "qdrant" },
    },
  ],
  checked_at: "2024-01-01T00:00:00Z",
};

describe("DashboardPage", () => {
  let restoreFetch: () => void;

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
    restoreFetch = installFetchMock([
      { method: "GET", url: "/health", response: { body: HEALTH } },
      { method: "GET", url: "/providers", response: { body: PROVIDER_DIAGNOSTICS } },
      {
        method: "GET",
        url: "/conversations",
        response: { body: { items: [], total: 0 } },
      },
      {
        method: "GET",
        url: "/documents",
        response: { body: { items: [], total: 3 } },
      },
      {
        method: "GET",
        url: "/leads",
        response: { body: { items: [], total: 7 } },
      },
      {
        method: "GET",
        url: "/approvals",
        response: { body: { items: [], total: 2, pending_count: 2 } },
      },
      {
        method: "GET",
        url: "/usage/summary",
        response: {
          body: {
            organization_id: "org_demo",
            plan_code: "pro",
            quotas: [],
            total_estimated_cost: 0,
          },
        },
      },
    ]);
  });

  afterEach(() => {
    restoreFetch();
    window.localStorage.clear();
  });

  it("renders metric cards and provider mode card", async () => {
    renderWithProviders(<DashboardPage />);

    expect(
      screen.getByRole("heading", { name: /dashboard/i }),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument(); // documents indexed
      expect(screen.getByText("7")).toBeInTheDocument(); // leads
    });

    expect(screen.getByText(/provider diagnostics/i)).toBeInTheDocument();
    expect(screen.getByText(/quick actions/i)).toBeInTheDocument();
  });
});
