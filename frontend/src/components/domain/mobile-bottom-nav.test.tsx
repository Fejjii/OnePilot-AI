import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import { setMockNextLocation } from "@/test-utils/next-mocks";
import { MobileBottomNav } from "./mobile-bottom-nav";

describe("MobileBottomNav", () => {
  let restoreFetch: () => void = () => {};

  beforeEach(() => {
    window.localStorage.setItem("onepilot_token", "test-token");
    setMockNextLocation({ pathname: "/workspace", search: "" });
  });

  afterEach(() => {
    restoreFetch();
    window.localStorage.clear();
  });

  it("renders primary destinations with Chat marked current on workspace", () => {
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/approvals",
        response: { body: { items: [], total: 0, pending_count: 0 } },
      },
    ]);

    renderWithProviders(<MobileBottomNav onOpenMenu={() => {}} />);

    expect(screen.getByRole("navigation", { name: /primary/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^chat$/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: /approvals/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /knowledge/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /leads/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /open navigation menu/i }),
    ).toBeInTheDocument();
  });

  it("marks Approvals current and shows pending count", async () => {
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/approvals",
        response: { body: { items: [], total: 2, pending_count: 2 } },
      },
    ]);
    setMockNextLocation({ pathname: "/approvals", search: "" });

    renderWithProviders(<MobileBottomNav onOpenMenu={() => {}} />);

    expect(screen.getByRole("link", { name: /approvals/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      await screen.findByLabelText(/2 pending approvals/i),
    ).toBeInTheDocument();
  });

  it("invokes onOpenMenu from More", async () => {
    restoreFetch = installFetchMock([
      {
        method: "GET",
        url: "/approvals",
        response: { body: { items: [], total: 0, pending_count: 0 } },
      },
    ]);
    const onOpenMenu = vi.fn();
    const user = userEvent.setup();

    renderWithProviders(<MobileBottomNav onOpenMenu={onOpenMenu} />);
    await user.click(
      screen.getByRole("button", { name: /open navigation menu/i }),
    );
    expect(onOpenMenu).toHaveBeenCalledTimes(1);
  });
});
