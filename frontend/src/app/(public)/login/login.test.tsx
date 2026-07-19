import "@/test-utils/next-mocks";
import { navigationMocks } from "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import { AuthProvider } from "@/lib/auth";
import { TOKEN_KEY } from "@/lib/api-client";
import LoginPage from "./page";

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

describe("LoginPage", () => {
  let restoreFetch: () => void;

  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    restoreFetch = installFetchMock([
      { method: "GET", url: "/me", response: { status: 401, body: { error: "unauthorized", message: "not signed in" } } },
    ]);
  });

  afterEach(() => {
    restoreFetch();
  });

  it("renders the sign-in form", async () => {
    renderWithProviders(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("validates required fields", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() =>
      expect(screen.getByText(/valid email address/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/password is required/i)).toBeInTheDocument();
  });

  it("renders the Try the demo action without credential hints", () => {
    renderWithProviders(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );
    expect(
      screen.getByRole("button", { name: /try the demo/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Demo1234/)).not.toBeInTheDocument();
  });

  it("enters a demo session with one click and navigates to the dashboard", async () => {
    restoreFetch();
    let authenticated = false;
    restoreFetch = installFetchMock([
      {
        method: "POST",
        url: "/demo/start",
        response: () => {
          authenticated = true;
          return {
            status: 200,
            body: {
              access_token: "demo-token-123",
              token_type: "bearer",
              expires_at: "2026-12-31T00:00:00Z",
              organization_name: "OnePilot AI",
              demo_mode: true,
              simulated_providers: true,
            },
          };
        },
      },
      {
        method: "GET",
        url: "/me",
        response: () =>
          authenticated
            ? { status: 200, body: ME_RESPONSE }
            : { status: 401, body: { error: "unauthorized", message: "not signed in" } },
      },
    ]);

    const user = userEvent.setup();
    renderWithProviders(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.click(screen.getByRole("button", { name: /try the demo/i }));

    await waitFor(() =>
      expect(navigationMocks.push).toHaveBeenCalledWith("/dashboard"),
    );
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("demo-token-123");
    expect(window.localStorage.getItem("onepilot_demo_mode")).toBe("1");
  });

  it("shows a clear message when the public demo is disabled", async () => {
    restoreFetch();
    restoreFetch = installFetchMock([
      {
        method: "POST",
        url: "/demo/start",
        response: {
          status: 403,
          body: { error: "forbidden", message: "The public demo is not enabled on this server." },
        },
      },
      { method: "GET", url: "/me", response: { status: 401, body: { error: "unauthorized", message: "not signed in" } } },
    ]);

    const user = userEvent.setup();
    renderWithProviders(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.click(screen.getByRole("button", { name: /try the demo/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/public demo is not enabled/i),
      ).toBeInTheDocument(),
    );
    expect(navigationMocks.push).not.toHaveBeenCalled();
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("shows a rate-limit message when too many demo sessions were started", async () => {
    restoreFetch();
    restoreFetch = installFetchMock([
      {
        method: "POST",
        url: "/demo/start",
        response: {
          status: 429,
          body: { error: "RATE_LIMIT_EXCEEDED", message: "Rate limit exceeded" },
        },
      },
      { method: "GET", url: "/me", response: { status: 401, body: { error: "unauthorized", message: "not signed in" } } },
    ]);

    const user = userEvent.setup();
    renderWithProviders(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.click(screen.getByRole("button", { name: /try the demo/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/too many demo sessions/i),
      ).toBeInTheDocument(),
    );
  });
});
