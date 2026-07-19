import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import MemoryPage from "./page";

const STATUS_ENABLED = {
  method: "GET" as const,
  url: "/memory/status",
  response: {
    body: {
      agent_memory_enabled: true,
      reason: "enabled",
      user_disabled: false,
      shared_demo_tenant: false,
      item_count: 1,
      max_items: 8,
      max_chars: 2000,
    },
  },
};

const LIST_ONE = {
  method: "GET" as const,
  url: "/memory",
  response: {
    body: {
      items: [
        {
          id: "mem_1",
          organization_id: "org_1",
          user_id: "usr_1",
          scope: "user",
          key: "pref_tone",
          value: "prefer concise answers",
          ttl_seconds: null,
          expires_at: null,
          created_at: "2026-07-19T00:00:00Z",
          updated_at: "2026-07-19T00:00:00Z",
        },
      ],
      total: 1,
    },
  },
};

describe("MemoryPage controls", () => {
  let restoreFetch: () => void = () => {};

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
  });

  afterEach(() => {
    restoreFetch();
    window.localStorage.clear();
  });

  it("shows status, clear control, and disable toggle", async () => {
    restoreFetch = installFetchMock([STATUS_ENABLED, LIST_ONE]);
    renderWithProviders(<MemoryPage />);

    await waitFor(() => {
      expect(screen.getByText(/agent memory is/i)).toBeInTheDocument();
    });
    expect(screen.getByText("pref_tone")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /clear my memory/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /disable agent memory/i }),
    ).toBeInTheDocument();
  });

  it("clears memory after confirmation", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    restoreFetch = installFetchMock([
      STATUS_ENABLED,
      LIST_ONE,
      {
        method: "DELETE",
        url: "/memory",
        response: { body: { deleted_count: 1 } },
      },
    ]);
    const user = userEvent.setup();
    renderWithProviders(<MemoryPage />);

    await screen.findByText("pref_tone");
    await user.click(screen.getByRole("button", { name: /clear my memory/i }));
    expect(confirmSpy).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("explains shared demo isolation", async () => {
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/memory/status",
        response: {
          body: {
            agent_memory_enabled: false,
            reason: "shared_demo_tenant",
            user_disabled: false,
            shared_demo_tenant: true,
            item_count: 0,
            max_items: 8,
            max_chars: 2000,
          },
        },
      },
      {
        method: "GET",
        url: "/memory",
        response: { body: { items: [], total: 0 } },
      },
    ]);
    renderWithProviders(<MemoryPage />);

    expect(
      await screen.findByText(/agent memory recall and auto-save are disabled/i),
    ).toBeInTheDocument();
  });
});
