import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
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
  let restoreFetch: () => void;

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
    restoreFetch = installFetchMock([
      { method: "GET", url: "/leads", response: { body: LEADS } },
    ]);
  });

  afterEach(() => {
    restoreFetch();
    window.localStorage.clear();
  });

  it("renders the leads table with status and urgency", async () => {
    renderWithProviders(<LeadsPage />);
    await waitFor(() => {
      expect(screen.getByText(/Jane Buyer/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Acme Corp/)).toBeInTheDocument();
    // "Qualified" appears in the status filter <option> and the status badge.
    expect(screen.getAllByText(/Qualified/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("High").length).toBeGreaterThan(0);
  });
});
