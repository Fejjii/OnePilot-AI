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
          name: /one ai workspace for business knowledge and operations/i,
        }),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          /search company knowledge, research the web, work with leads/i,
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          /novaedge solutions is the preloaded sample company/i,
        ),
      ).toBeInTheDocument();
    });

    it("renders four capability groups below the hero", () => {
      renderLanding();
      expect(
        screen.getByRole("heading", { name: /what onepilot can do/i }),
      ).toBeInTheDocument();
      expect(screen.getByText(/knowledge & research/i)).toBeInTheDocument();
      expect(screen.getByText(/crm & leads/i)).toBeInTheDocument();
      expect(screen.getByText(/email & calendar/i)).toBeInTheDocument();
      expect(screen.getByText(/safe agentic execution/i)).toBeInTheDocument();
      expect(
        screen.queryByText(/draft a follow-up email to our most promising lead/i),
      ).not.toBeInTheDocument();
    });

    it("renders a compact operating-layer visual in the hero", () => {
      renderLanding();
      const operatingLayer = screen.getByRole("complementary", {
        name: /from scattered business tools/i,
      });
      expect(
        within(operatingLayer).getByText(/from scattered business tools/i),
      ).toBeInTheDocument();
      expect(
        within(operatingLayer).getByText(/to one intelligent operating layer/i),
      ).toBeInTheDocument();
      for (const layer of ["Understand", "Reason", "Execute", "Connect"]) {
        expect(within(operatingLayer).getByText(layer)).toBeInTheDocument();
      }
      for (const label of [
        "Knowledge",
        "RAG",
        "Memory",
        "Web",
        "Context",
        "Lead priority",
        "Agent workflows",
        "Tool calling",
        "Email",
        "Scheduling",
        "Follow-ups",
        "CRM actions",
        "Approvals",
        "Google Workspace",
        "APIs",
        "Payments",
        "Communications",
      ]) {
        expect(within(operatingLayer).getByText(label)).toBeInTheDocument();
      }
      expect(within(operatingLayer).getAllByText("CRM").length).toBe(2);
      expect(
        within(operatingLayer).getByText(
          "Grounded in context. Connected to tools. Controlled by humans.",
        ),
      ).toBeInTheDocument();
      expect(
        within(operatingLayer).getByText(
          /memory is available in authenticated private workspaces/i,
        ),
      ).toBeInTheDocument();
      expect(
        within(operatingLayer).getByLabelText(
          /authenticated \/ private workspace/i,
        ),
      ).toBeInTheDocument();
      expect(within(operatingLayer).getByText("Ready")).toBeInTheDocument();
      expect(
        within(operatingLayer).getByLabelText(/payments.*integration-ready/i),
      ).toBeInTheDocument();
      expect(
        within(operatingLayer).getByLabelText(
          /communications.*integration-ready/i,
        ),
      ).toBeInTheDocument();
      expect(
        within(operatingLayer).queryByText(/capability architecture/i),
      ).not.toBeInTheDocument();
      expect(within(operatingLayer).queryByText("Interaction")).not.toBeInTheDocument();
      expect(screen.queryByText(/^ask$/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/MCP/i)).not.toBeInTheDocument();
      expect(
        within(operatingLayer).queryByText(/HubSpot/i),
      ).not.toBeInTheDocument();
      expect(
        within(operatingLayer).queryByText(/Salesforce/i),
      ).not.toBeInTheDocument();
      expect(
        within(operatingLayer).queryByText(/Stripe/i),
      ).not.toBeInTheDocument();
      expect(
        within(operatingLayer).queryByText(/Slack/i),
      ).not.toBeInTheDocument();
      expect(
        within(operatingLayer).queryByText(/Twilio/i),
      ).not.toBeInTheDocument();
    });

    it("lists the technology stack behind engineering details", async () => {
      const user = userEvent.setup();
      renderLanding();
      expect(screen.queryByText("FastAPI")).not.toBeInTheDocument();

      await user.click(screen.getByText(/engineering details/i));
      const details = screen.getByText(/engineering details/i).closest("details");
      expect(details).not.toBeNull();
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
        expect(within(details as HTMLElement).getByText(tech)).toBeInTheDocument();
      }
    });

    it("distinguishes the public demo from the private live-Google track", () => {
      renderLanding();
      expect(
        screen.getByRole("heading", {
          name: /public demo vs live integrations/i,
        }),
      ).toBeInTheDocument();
      expect(screen.getByText(/^public$/i)).toBeInTheDocument();
      expect(screen.getByText(/private validated track/i)).toBeInTheDocument();
      expect(screen.getByText(/gmail simulated/i)).toBeInTheDocument();
      expect(screen.getByText(/calendar simulated/i)).toBeInTheDocument();
      expect(screen.getByText(/org-restricted live gmail/i)).toBeInTheDocument();
      expect(
        screen.getByText(/hubspot is a mock adapter today/i),
      ).toBeInTheDocument();
      expect(screen.queryByText(/send_email/i)).not.toBeInTheDocument();
    });

    it("communicates that the public demo is credential-free", () => {
      renderLanding();
      expect(
        screen.getAllByText(/no sign-up, no credentials/i).length,
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

    it("links View GitHub to the documented repository URL", () => {
      renderLanding();
      const githubLinks = screen.getAllByRole("link", { name: /github/i });
      expect(githubLinks.length).toBeGreaterThan(0);
      for (const link of githubLinks) {
        expect(link).toHaveAttribute(
          "href",
          "https://github.com/Fejjii/OnePilot-AI",
        );
      }
      expect(document.querySelector("#capabilities")).toBeInTheDocument();
      expect(document.querySelector("#public-vs-live")).toBeInTheDocument();
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
