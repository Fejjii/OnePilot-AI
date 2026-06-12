import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AssistantMessageContent } from "./assistant-message-content";

const STRUCTURED_SAMPLE = `## Summary
NovaEdge offers a 30-day refund for annual plans.

## Key points
- Refunds apply within 30 days of purchase
- Monthly plans are non-refundable

## Evidence or sources
- [NovaEdge Refund Policy]: Annual subscriptions may be refunded within 30 days.

## Suggested next action
Contact NovaEdge support with your invoice to start a refund request.`;

describe("AssistantMessageContent", () => {
  it("renders structured sections without raw markdown headings", () => {
    render(<AssistantMessageContent content={STRUCTURED_SAMPLE} />);

    expect(screen.queryByText("## Summary")).not.toBeInTheDocument();
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.getByText(/30-day refund for annual plans/i)).toBeInTheDocument();
    expect(screen.getByText("Key points")).toBeInTheDocument();
    expect(screen.getByText(/Refunds apply within 30 days/i)).toBeInTheDocument();
    expect(screen.getByText("Evidence & sources")).toBeInTheDocument();
    expect(screen.getByText("NovaEdge Refund Policy")).toBeInTheDocument();
    expect(screen.getByText("Suggested next action")).toBeInTheDocument();
    expect(
      screen.getByText(/Contact NovaEdge support with your invoice/i),
    ).toBeInTheDocument();
  });

  it("renders web sources with external links", () => {
    render(
      <AssistantMessageContent
        content={[
          "## Summary",
          "Bitcoin is trading higher today.",
          "",
          "## Key points",
          "- Price momentum is positive",
          "",
          "## Evidence or sources",
          "- **Bitcoin Price** (https://example.com/btc): Trading near recent highs",
          "",
          "## Suggested next action",
          "Verify the price on a second source before acting.",
        ].join("\n")}
      />,
    );

    const link = screen.getByRole("link", { name: /bitcoin price/i });
    expect(link).toHaveAttribute("href", "https://example.com/btc");
  });

  it("renders email drafts in a readable layout", () => {
    render(
      <AssistantMessageContent
        content={
          "Subject: Demo follow-up\n\nHi Jordan,\n\nThanks again for joining the demo."
        }
      />,
    );

    expect(screen.getByText("Email draft")).toBeInTheDocument();
    expect(screen.getByText("Demo follow-up")).toBeInTheDocument();
    expect(screen.getByText(/Thanks again for joining the demo/i)).toBeInTheDocument();
  });

  it("keeps safety refusals compact as plain text", () => {
    render(
      <AssistantMessageContent
        content="I couldn't find enough information in the knowledge base to answer that confidently."
      />,
    );

    expect(
      screen.getByText(/couldn't find enough information/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("Summary")).not.toBeInTheDocument();
  });
});
