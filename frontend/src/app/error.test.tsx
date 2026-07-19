import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ErrorPage from "./error";

describe("Error boundary page", () => {
  it("renders a friendly message without exposing stack traces", () => {
    const error = Object.assign(new Error("Secret internal failure at /api/x"), {
      digest: "abc123",
      stack: "Error: Secret\n    at Object.<anonymous> (secret.ts:1:1)",
    });

    render(<ErrorPage error={error} reset={vi.fn()} />);

    expect(
      screen.getByRole("heading", { name: /something went wrong/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/unexpected problem loading this page/i)).toBeInTheDocument();
    expect(screen.queryByText(/Secret internal failure/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/secret\.ts/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/abc123/i)).not.toBeInTheDocument();
  });

  it("invokes reset when Try again is clicked", async () => {
    const reset = vi.fn();
    const user = userEvent.setup();
    render(
      <ErrorPage error={new Error("boom")} reset={reset} />,
    );

    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("offers a dashboard recovery action", () => {
    render(<ErrorPage error={new Error("boom")} reset={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: /go to dashboard/i }),
    ).toBeInTheDocument();
  });
});
