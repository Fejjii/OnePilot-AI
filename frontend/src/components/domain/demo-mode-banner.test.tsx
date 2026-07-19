import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import { AuthProvider } from "@/lib/auth";
import { TOKEN_KEY } from "@/lib/api-client";
import { DemoModeBanner } from "./demo-mode-banner";

const ME_RESPONSE = {
  user: {
    id: "usr_demo_admin",
    email: "admin@onepilot.ai",
    full_name: "Demo Admin",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  organization: {
    id: "org_demo_onepilot",
    name: "OnePilot AI",
    slug: "onepilot-ai-demo",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  role: "owner",
  plan: "business",
};

describe("DemoModeBanner", () => {
  let restoreFetch: () => void;

  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    restoreFetch();
  });

  it("shows the simulated-actions banner during an authenticated demo session", async () => {
    window.localStorage.setItem(TOKEN_KEY, "demo-token");
    window.localStorage.setItem("onepilot_demo_mode", "1");
    restoreFetch = installFetchMock([
      { method: "GET", url: "/me", response: { status: 200, body: ME_RESPONSE } },
    ]);

    renderWithProviders(
      <AuthProvider>
        <DemoModeBanner />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(screen.getByRole("status")).toBeInTheDocument(),
    );
    expect(screen.getByText(/demo mode/i)).toBeInTheDocument();
    expect(
      screen.getByText(/no real emails or events are ever sent/i),
    ).toBeInTheDocument();
  });

  it("stays hidden for regular authenticated sessions", async () => {
    window.localStorage.setItem(TOKEN_KEY, "normal-token");
    restoreFetch = installFetchMock([
      { method: "GET", url: "/me", response: { status: 200, body: ME_RESPONSE } },
    ]);

    renderWithProviders(
      <AuthProvider>
        <DemoModeBanner />
      </AuthProvider>,
    );

    // Wait for auth to settle, then confirm nothing rendered.
    await waitFor(() =>
      expect(screen.queryByRole("status")).not.toBeInTheDocument(),
    );
  });

  it("stays hidden when the demo session has expired (401)", async () => {
    window.localStorage.setItem(TOKEN_KEY, "expired-demo-token");
    window.localStorage.setItem("onepilot_demo_mode", "1");
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/me",
        response: { status: 401, body: { error: "unauthorized", message: "expired" } },
      },
    ]);

    renderWithProviders(
      <AuthProvider>
        <DemoModeBanner />
      </AuthProvider>,
    );

    await waitFor(() => {
      // Expired session must clear both the token and the demo flag.
      expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
    });
    expect(window.localStorage.getItem("onepilot_demo_mode")).toBeNull();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
