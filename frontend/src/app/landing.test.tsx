import "@/test-utils/next-mocks";
import { navigationMocks } from "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import { AuthProvider } from "@/lib/auth";
import { TOKEN_KEY } from "@/lib/api-client";
import LandingPage from "./page";

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

const UNAUTHENTICATED_ME = {
  method: "GET",
  url: "/me",
  response: {
    status: 401,
    body: { error: "unauthorized", message: "not signed in" },
  },
} as const;

function renderLanding() {
  return renderWithProviders(
    <AuthProvider>
      <LandingPage />
    </AuthProvider>,
  );
}

describe("LandingPage", () => {
  let restoreFetch: () => void;

  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    restoreFetch = installFetchMock([UNAUTHENTICATED_ME]);
  });

  afterEach(() => {
    restoreFetch();
  });

  describe("rendering", () => {
    it("renders the hero with the product value proposition", () => {
      renderLanding();
      expect(
        screen.getByRole("heading", {
          level: 1,
          name: /one workspace\. one ai copilot/i,
        }),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/ai operations platform for small businesses/i),
      ).toBeInTheDocument();
    });

    it("renders the capability, safety, and architecture sections", () => {
      renderLanding();
      expect(
        screen.getByRole("heading", { name: /what onepilot can do/i }),
      ).toBeInTheDocument();
      expect(screen.getByText(/ai workspace & chat/i)).toBeInTheDocument();
      expect(screen.getByText(/knowledge & retrieval/i)).toBeInTheDocument();
      expect(
        screen.getByText(/approvals & human control/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/business insights/i)).toBeInTheDocument();
      expect(
        screen.getByText(/gmail & calendar workflows/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/demo-safe by design/i)).toBeInTheDocument();
      expect(
        screen.getByRole("heading", {
          name: /the ai proposes\. humans approve\./i,
        }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: /under the hood/i }),
      ).toBeInTheDocument();
    });

    it("lists the technology stack for reviewers", () => {
      renderLanding();
      for (const tech of [
        "FastAPI",
        "Next.js",
        "LangGraph",
        "PostgreSQL",
        "Redis",
        "Qdrant",
        "Railway",
        "Vercel",
      ]) {
        expect(screen.getByText(tech)).toBeInTheDocument();
      }
    });

    it("communicates that demo actions are simulated and credential-free", () => {
      renderLanding();
      expect(
        screen.getAllByText(/no real emails/i).length,
      ).toBeGreaterThan(0);
      expect(
        screen.getAllByText(/no credentials/i).length,
      ).toBeGreaterThan(0);
    });

    it("contains no student-project or internal-development wording", () => {
      renderLanding();
      expect(screen.queryByText(/capstone/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/student/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/coursework/i)).not.toBeInTheDocument();
    });
  });

  describe("CTA navigation", () => {
    it("links Sign in to /login and Create a workspace to /register", () => {
      renderLanding();
      const signInLinks = screen.getAllByRole("link", { name: /sign in/i });
      expect(signInLinks.length).toBeGreaterThan(0);
      for (const link of signInLinks) {
        expect(link).toHaveAttribute("href", "/login");
      }
      const registerLinks = screen.getAllByRole("link", {
        name: /create a workspace/i,
      });
      expect(registerLinks.length).toBeGreaterThan(0);
      for (const link of registerLinks) {
        expect(link).toHaveAttribute("href", "/register");
      }
    });

    it("links View capabilities to the capabilities section", () => {
      renderLanding();
      const viewCapabilities = screen.getByRole("link", {
        name: /view capabilities/i,
      });
      expect(viewCapabilities).toHaveAttribute("href", "#capabilities");
      expect(
        document.querySelector("#capabilities"),
      ).toBeInTheDocument();
      expect(document.querySelector("#safety")).toBeInTheDocument();
      expect(document.querySelector("#architecture")).toBeInTheDocument();
    });

    it("shows Open dashboard instead of Sign in in the header when authenticated", async () => {
      restoreFetch();
      window.localStorage.setItem(TOKEN_KEY, "existing-token");
      restoreFetch = installFetchMock([
        { method: "GET", url: "/me", response: { status: 200, body: ME_RESPONSE } },
      ]);

      renderLanding();

      const dashboardLinks = await screen.findAllByRole("link", {
        name: /open dashboard/i,
      });
      expect(dashboardLinks.length).toBeGreaterThan(0);
      for (const link of dashboardLinks) {
        expect(link).toHaveAttribute("href", "/dashboard");
      }
      const header = screen.getByRole("banner");
      expect(
        within(header).queryByRole("link", { name: /sign in/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("demo entry", () => {
    it("starts a demo session and navigates to the dashboard", async () => {
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
              : {
                  status: 401,
                  body: { error: "unauthorized", message: "not signed in" },
                },
        },
      ]);

      const user = userEvent.setup();
      renderLanding();

      await user.click(
        screen.getByRole("button", { name: /try the live demo/i }),
      );

      await waitFor(() =>
        expect(navigationMocks.push).toHaveBeenCalledWith("/dashboard"),
      );
      expect(window.localStorage.getItem(TOKEN_KEY)).toBe("demo-token-123");
      expect(window.localStorage.getItem("onepilot_demo_mode")).toBe("1");
    });

    it("shows a clear error when the public demo is disabled", async () => {
      restoreFetch();
      restoreFetch = installFetchMock([
        {
          method: "POST",
          url: "/demo/start",
          response: {
            status: 403,
            body: { error: "forbidden", message: "demo disabled" },
          },
        },
        UNAUTHENTICATED_ME,
      ]);

      const user = userEvent.setup();
      renderLanding();

      await user.click(
        screen.getByRole("button", { name: /try the live demo/i }),
      );

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(/public demo is not enabled/i);
      expect(navigationMocks.push).not.toHaveBeenCalled();
      expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
    });

    it("shows a rate-limit error when too many demo sessions were started", async () => {
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
        UNAUTHENTICATED_ME,
      ]);

      const user = userEvent.setup();
      renderLanding();

      await user.click(
        screen.getByRole("button", { name: /try the live demo/i }),
      );

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(/too many demo sessions/i);
    });
  });

  describe("accessibility landmarks", () => {
    it("exposes header, navigation, main, footer, and a skip link", () => {
      renderLanding();
      expect(screen.getByRole("banner")).toBeInTheDocument();
      expect(
        screen.getByRole("navigation", { name: /primary$/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("main")).toBeInTheDocument();
      expect(screen.getByRole("contentinfo")).toBeInTheDocument();
      const skipLink = screen.getByRole("link", { name: /skip to content/i });
      expect(skipLink).toHaveAttribute("href", "#main-content");
      expect(document.querySelector("#main-content")).toBeInTheDocument();
    });

    it("toggles the mobile menu with correct aria state", async () => {
      const user = userEvent.setup();
      renderLanding();

      const toggle = screen.getByRole("button", { name: /open menu/i });
      expect(toggle).toHaveAttribute("aria-expanded", "false");

      await user.click(toggle);
      expect(
        screen.getByRole("button", { name: /close menu/i }),
      ).toHaveAttribute("aria-expanded", "true");
    });
  });
});
