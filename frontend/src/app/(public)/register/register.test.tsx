import "@/test-utils/next-mocks";
import { navigationMocks } from "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import { AuthProvider } from "@/lib/auth";
import { TOKEN_KEY } from "@/lib/api-client";
import RegisterPage from "./page";

const ME_RESPONSE = {
  user: {
    id: "usr_1",
    email: "owner@example.com",
    full_name: "Owner",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  organization: {
    id: "org_1",
    name: "Acme",
    slug: "acme",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  role: "owner",
  plan: "starter",
};

describe("RegisterPage", () => {
  let restoreFetch: () => void = () => {};

  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/me",
        response: {
          status: 401,
          body: { error: "unauthorized", message: "not signed in" },
        },
      },
    ]);
  });

  afterEach(() => {
    restoreFetch();
  });

  it("renders the create-workspace form for guests", async () => {
    renderWithProviders(
      <AuthProvider>
        <RegisterPage />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /create/i }),
      ).toBeInTheDocument();
    });
  });

  it("redirects authenticated users to the dashboard", async () => {
    window.localStorage.setItem(TOKEN_KEY, "existing-token");
    restoreFetch();
    restoreFetch = installFetchMock([
      { method: "GET", url: "/me", response: { body: ME_RESPONSE } },
    ]);

    renderWithProviders(
      <AuthProvider>
        <RegisterPage />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(navigationMocks.replace).toHaveBeenCalledWith("/dashboard"),
    );
  });
});
