import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import { AuthProvider } from "@/lib/auth";
import UsageAdminPage from "./page";

const ME = {
  user: {
    id: "usr_1",
    email: "admin@demo.com",
    full_name: "Admin User",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  organization: { id: "org_1", name: "Demo", slug: "demo", created_at: "", updated_at: "" },
  role: "admin",
  plan: "free",
};

const USAGE_SUMMARY = {
  organization_id: "org_1",
  plan_code: "free",
  quotas: [
    {
      feature: "chat_messages",
      used: 2,
      limit: 50,
      remaining: 48,
      period_start: "2026-05-01T00:00:00Z",
      period_end: "2026-06-01T00:00:00Z",
    },
  ],
  total_estimated_cost: 0.42,
};

const BILLING_SUMMARY = {
  organization_id: "org_1",
  current_plan: "free",
  billing_period: {
    start: "2026-05-01T00:00:00Z",
    end: "2026-06-01T00:00:00Z",
  },
  total_estimated_cost: 0.42,
  currency: "USD",
  usage_by_feature: [
    { feature: "chat_messages", event_count: 2, estimated_cost: 0.42 },
  ],
  usage_by_model: [{ model: "gpt-4o-mini", event_count: 2, estimated_cost: 0.42 }],
  tokens_by_model: [
    { model: "gpt-4o-mini", input_tokens: 100, output_tokens: 50, total_tokens: 150 },
  ],
  remaining_quota: USAGE_SUMMARY.quotas,
  overage_estimate: 0,
  top_users: [],
  billing_provider_mode: "mock",
  mock_mode: true,
};

const INVOICE_PREVIEW = {
  organization_id: "org_1",
  plan_code: "free",
  billing_period: BILLING_SUMMARY.billing_period,
  base_plan_price_cents: 0,
  estimated_usage_cost: 0.42,
  estimated_overage_cost: 0,
  total_estimated_due_cents: 42,
  currency: "USD",
  line_items: [
    {
      description: "Free plan (base)",
      quantity: 1,
      unit_amount_cents: 0,
      amount_cents: 0,
    },
    {
      description: "Estimated AI usage (tokens, speech, tools)",
      quantity: 1,
      unit_amount_cents: 42,
      amount_cents: 42,
    },
  ],
  mock_stripe: true,
  provider_status: "mock",
};

const CURRENT_PLAN = {
  plan: {
    code: "free",
    name: "Free",
    monthly_price_cents: 0,
    limits: {
      chat_messages: 50,
      rag_queries: 20,
      document_uploads: 5,
      storage_mb: 100,
      email_drafts: 10,
      lead_workflows: 5,
      tool_calls: 30,
      users: 1,
    },
  },
  subscription: {
    id: "sub_1",
    organization_id: "org_1",
    plan_code: "free",
    status: "active",
    started_at: "2026-05-01T00:00:00Z",
    renews_at: null,
  },
};

const BILLING_PLANS = {
  current_plan: "free",
  entitlements: {
    plan_code: "free",
    included_chat_messages: 50,
    included_rag_queries: 20,
    included_speech_minutes: 10,
    included_document_uploads: 5,
    included_storage_mb: 100,
    included_team_members: 1,
    base_price_cents: 0,
    overage_policy: "block_at_limit",
  },
  available_plans: [],
};

describe("UsageAdminPage billing", () => {
  let restoreFetch: () => void;

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
    restoreFetch = installFetchMock([
      { method: "GET", url: "/me", response: { body: ME } },
      { method: "GET", url: "/usage/summary", response: { body: USAGE_SUMMARY } },
      { method: "GET", url: "/billing/summary", response: { body: BILLING_SUMMARY } },
      { method: "GET", url: "/billing/invoice-preview", response: { body: INVOICE_PREVIEW } },
      { method: "GET", url: "/billing/plans", response: { body: BILLING_PLANS } },
      { method: "GET", url: "/plans/current", response: { body: CURRENT_PLAN } },
      { method: "GET", url: "/admin/usage-events", response: { body: { items: [], total: 0 } } },
      { method: "GET", url: "/admin/audit-logs", response: { body: { items: [], total: 0 } } },
    ]);
  });

  afterEach(() => {
    restoreFetch();
    window.localStorage.clear();
  });

  it("renders estimated cost from billing summary", async () => {
    renderWithProviders(
      <AuthProvider>
        <UsageAdminPage />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByText("Billing ready mock mode")).toBeTruthy();
      expect(screen.getByText("Estimated cost")).toBeTruthy();
      expect(screen.getAllByText(/0[,.]42/).length).toBeGreaterThan(0);
    });
  });

  it("renders current plan", async () => {
    renderWithProviders(
      <AuthProvider>
        <UsageAdminPage />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByText("Current plan")).toBeTruthy();
      expect(screen.getAllByText(/Free/i).length).toBeGreaterThan(0);
    });
  });

  it("renders invoice preview line items", async () => {
    renderWithProviders(
      <AuthProvider>
        <UsageAdminPage />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByText("Invoice preview")).toBeTruthy();
      expect(screen.getByText(/Estimated AI usage/)).toBeTruthy();
      expect(screen.getByText("Total estimated due")).toBeTruthy();
    });
  });

  it("shows mock Stripe status", async () => {
    renderWithProviders(
      <AuthProvider>
        <UsageAdminPage />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByText(/Mock Stripe/)).toBeTruthy();
      expect(screen.getByText(/Stripe integration mocked/)).toBeTruthy();
    });
  });

  it("renders quota bars", async () => {
    renderWithProviders(
      <AuthProvider>
        <UsageAdminPage />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByText("Plan quotas")).toBeTruthy();
      expect(screen.getByText(/2\s*\/\s*50/)).toBeTruthy();
    });
  });
});
