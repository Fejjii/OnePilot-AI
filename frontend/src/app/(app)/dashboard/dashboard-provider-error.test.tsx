import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DashboardPage from "./page";
import { renderWithProviders } from "@/test-utils/render-with-providers";

vi.mock("@/lib/queries", () => ({
  useConversations: () => ({ isLoading: false, isError: false, data: { items: [], total: 0 } }),
  useDocuments: () => ({ isLoading: false, data: { total: 0 } }),
  useLeads: () => ({ isLoading: false, data: { total: 0 } }),
  useApprovals: () => ({ isLoading: false, data: { pending_count: 0 } }),
  useUsageSummary: () => ({ isLoading: false, isError: false, data: { quotas: [] } }),
  useProviderDiagnostics: () => ({
    isLoading: false,
    isError: true,
    data: undefined,
    refetch: vi.fn(),
  }),
}));

describe("Dashboard provider diagnostics errors", () => {
  it("shows a safe unavailable message when diagnostics fail", async () => {
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Provider diagnostics unavailable")).toBeInTheDocument();
    });
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
  });
});
