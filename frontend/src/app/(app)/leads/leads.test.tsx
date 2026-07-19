import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import LeadsPage from "./page";

const LEADS = {
  items: [
    {
      id: "lead_1",
      organization_id: "org_demo",
      name: "Jane Buyer",
      company: "Acme Corp",
      email: "jane@acme.com",
      status: "qualified",
      source: "chat",
      urgency: "high",
      intent: "demo",
      pain_point: "Manual workflow is slow",
      summary: "Wants a demo of approvals",
      recommended_next_action: "Book 30-min intro call",
      created_by: "usr_1",
      created_at: "2026-05-10T10:00:00Z",
      updated_at: "2026-05-10T10:00:00Z",
    },
  ],
  total: 1,
};

describe("LeadsPage", () => {
  let restoreFetch: () => void = () => {};

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
  });

  afterEach(() => {
    restoreFetch();
    window.localStorage.clear();
  });

  it("renders the leads table with status and urgency", async () => {
    restoreFetch = installFetchMock([
      { method: "GET", url: "/leads", response: { body: LEADS } },
    ]);
    renderWithProviders(<LeadsPage />);
    await waitFor(() => {
      expect(screen.getByText(/Jane Buyer/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Acme Corp/)).toBeInTheDocument();
    expect(screen.getAllByText(/Qualified/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("High").length).toBeGreaterThan(0);
  });

  it("shows a loading state while leads are fetching", () => {
    const original = globalThis.fetch;
    globalThis.fetch = vi.fn(
      () => new Promise(() => {
        /* intentionally pending */
      }),
    ) as typeof fetch;
    restoreFetch = () => {
      globalThis.fetch = original;
    };

    renderWithProviders(<LeadsPage />);
    // TableSkeleton renders pulse placeholders while the query is pending.
    expect(document.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
    expect(screen.queryByText(/Jane Buyer/)).not.toBeInTheDocument();
    expect(screen.queryByText(/no leads yet/i)).not.toBeInTheDocument();
  });

  it("shows an empty state when there are no leads", async () => {
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/leads",
        response: { body: { items: [], total: 0 } },
      },
    ]);
    renderWithProviders(<LeadsPage />);
    await waitFor(() => {
      expect(screen.getByText(/no leads yet/i)).toBeInTheDocument();
    });
    expect(
      screen.getByText(/create one manually/i),
    ).toBeInTheDocument();
  });

  it("shows an error state with retry when the leads API fails", async () => {
    let calls = 0;
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/leads",
        response: () => {
          calls += 1;
          if (calls === 1) {
            return {
              status: 500,
              body: { error: "internal_error", message: "boom" },
            };
          }
          return { body: LEADS };
        },
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText(/could not load leads/i)).toBeInTheDocument();
    });
    // Failed fetch must not be mistaken for the empty state.
    expect(screen.queryByText(/no leads yet/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /try again/i }));

    await waitFor(() => {
      expect(screen.getByText(/Jane Buyer/)).toBeInTheDocument();
    });
    expect(calls).toBe(2);
  });
});
