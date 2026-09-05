import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    expect(screen.queryByText("usr_1")).not.toBeInTheDocument();
    expect(screen.queryByText(/proposed payload/i)).not.toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /send pricing email to acme/i }));
    expect(screen.getByText(/engineering details/i)).toBeInTheDocument();
    expect(screen.queryByText("usr_1")).not.toBeInTheDocument();
    expect(screen.queryByText(/proposed payload/i)).not.toBeInTheDocument();
  });

  it("renders complete previews for seeded email and calendar payloads", async () => {
    restoreFetch();
    restoreFetch = installFetchMock([
      { method: "GET", url: "/me", response: { body: ME } },
      {
        method: "GET",
        url: "/approvals",
        response: {
          body: {
            items: [
              {
                id: "apv_email",
                organization_id: "org_demo",
                action_type: "send_email",
                title: "Send follow-up email to Brightline Analytics",
                description: "Draft a renewal follow-up to Sarah Chen.",
                proposed_payload: {
                  to: "sarah.chen@brightline.io",
                  subject: "NovaEdge Growth plan — next steps for Brightline",
                  body: "Hi Sarah — following up on your demo request.",
                },
                risk_level: "high",
                status: "pending",
                reason: "Seeded demo approval for reviewer walkthrough",
                created_by: "usr_1",
                reviewed_by: null,
                created_at: "2026-05-10T10:00:00Z",
                reviewed_at: null,
              },
              {
                id: "apv_cal",
                organization_id: "org_demo",
                action_type: "schedule_meeting",
                title: "Schedule discovery call with Northwind Legal",
                description: "Propose a 30-minute discovery call.",
                proposed_payload: {
                  summary: "Discovery call — approvals + knowledge base walkthrough",
                  start_time: "2026-09-15T09:00:00+00:00",
                  end_time: "2026-09-15T09:30:00+00:00",
                  timezone: "Europe/Berlin",
                  attendees: ["marcus.webb@northwindlegal.com"],
                },
                risk_level: "medium",
                status: "pending",
                reason: "Seeded demo approval for reviewer walkthrough",
                created_by: "usr_1",
                reviewed_by: null,
                created_at: "2026-05-10T09:00:00Z",
                reviewed_at: null,
              },
            ],
            total: 2,
            pending_count: 2,
          },
        },
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(
      <AuthProvider>
        <ApprovalsPage />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Send follow-up email to Brightline Analytics/),
      ).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", {
        name: /send follow-up email to brightline analytics/i,
      }),
    );
    expect(screen.getByText(/Email preview/i)).toBeInTheDocument();
    expect(screen.getByText(/sarah.chen@brightline.io/i)).toBeInTheDocument();
    expect(
      screen.getByText(/NovaEdge Growth plan — next steps for Brightline/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Hi Sarah — following up on your demo request/),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: /schedule discovery call with northwind legal/i,
      }),
    );
    expect(screen.getByText(/Calendar preview/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Discovery call — approvals \+ knowledge base walkthrough/),
    ).toBeInTheDocument();
    expect(screen.getByText(/marcus.webb@northwindlegal.com/i)).toBeInTheDocument();
    expect(screen.getByText(/2026-09-15T09:00:00\+00:00/)).toBeInTheDocument();
  });
});
