import "@/test-utils/next-mocks";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils/render-with-providers";
import { installFetchMock } from "@/test-utils/mock-fetch";
import { AuthProvider } from "@/lib/auth";
import LoginPage from "./page";

describe("LoginPage", () => {
  let restoreFetch: () => void;

  beforeEach(() => {
    window.localStorage.clear();
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
});
