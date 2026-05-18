import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import { AuthProvider } from "@/lib/auth";
import ApprovalsPage from "./page";

const APPROVALS = {
  items: [
    {
      id: "app_1",
      organization_id: "org_demo",
      action_type: "email_send",
      title: "Send pricing email to Acme",
      description: "Send the standard onboarding email with attached PDF.",
      proposed_payload: { to: "buyer@acme.com", subject: "Welcome" },
      risk_level: "high",
      status: "pending",
      reason: "",
      created_by: "usr_1",
      reviewed_by: null,
      created_at: "2026-05-10T10:00:00Z",
      reviewed_at: null,
    },
  ],
  total: 1,
  pending_count: 1,
};

const ME = {
  user: {
    id: "usr_1",
    email: "admin@demo.com",
    full_name: "Admin User",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  organization: {
    id: "org_demo",
    name: "Demo Org",
    slug: "demo-org",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  role: "admin",
  plan: "pro",
};

describe("ApprovalsPage", () => {
  let restoreFetch: () => void;

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
    restoreFetch = installFetchMock([
      { method: "GET", url: "/me", response: { body: ME } },
      { method: "GET", url: "/approvals", response: { body: APPROVALS } },
    ]);
  });

  afterEach(() => {
    restoreFetch();
    window.localStorage.clear();
  });

  it("renders the pending approval inbox with risk badge", async () => {
    renderWithProviders(
      <AuthProvider>
        <ApprovalsPage />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Send pricing email to Acme/)).toBeInTheDocument();
    });
    expect(screen.getAllByText(/high risk/i).length).toBeGreaterThan(0);
  });
});
