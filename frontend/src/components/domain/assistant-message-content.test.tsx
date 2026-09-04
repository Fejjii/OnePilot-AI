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

  it("renders upcoming meetings without availability copy", () => {
    render(
      <AssistantMessageContent
        content={[
          "Upcoming meetings this week:",
          "1. Discovery call with Sarah Chen — Friday, 5 September, 10:00 to 10:30",
          "   Sarah Chen · Brightline Analytics",
          "Times shown in Europe/Berlin.",
        ].join("\n")}
      />,
    );

    expect(screen.getByText("Upcoming meetings")).toBeInTheDocument();
    expect(screen.getByText(/Discovery call with Sarah Chen/i)).toBeInTheDocument();
    expect(screen.getByText(/Brightline Analytics/i)).toBeInTheDocument();
    expect(screen.queryByText(/open times, not existing meetings/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/provider mode/i)).not.toBeInTheDocument();
  });

  it("renders available slots as open times, not meetings", () => {
    render(
      <AssistantMessageContent
        content={[
          "Available time slots:",
          "These are open times, not existing meetings.",
          "1. Friday, 5 September, 09:00 to 09:30",
          "Times shown in Europe/Berlin.",
        ].join("\n")}
      />,
    );

    expect(screen.getByText("Available time slots")).toBeInTheDocument();
    expect(
      screen.getByText(/open times, not existing meetings/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Discovery call/i)).not.toBeInTheDocument();
  });

  it("hides provider jargon on meeting proposals", () => {
    render(
      <AssistantMessageContent
        content={[
          "Title: Follow-up meeting",
          "Date and time: Monday, 11 May, 10:00 to 10:30",
          "Timezone: Europe/Berlin",
          "Approval status: pending",
          "Next action: Review and approve to create this meeting.",
        ].join("\n")}
      />,
    );

    expect(screen.getByText("Meeting proposal")).toBeInTheDocument();
    expect(screen.getByText("Follow-up meeting")).toBeInTheDocument();
    expect(screen.queryByText(/provider mode/i)).not.toBeInTheDocument();
  });
});
