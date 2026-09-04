import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ToolBadge } from "./tool-badge";

describe("ToolBadge", () => {
  it("maps known tools to recruiter-facing labels", () => {
    const { rerender } = render(<ToolBadge toolName="rag.answer" />);
    expect(screen.getByText("Knowledge")).toBeInTheDocument();
    rerender(<ToolBadge toolName="lead.support" />);
    expect(screen.getByText("CRM")).toBeInTheDocument();
    rerender(<ToolBadge toolName="external.web_search" />);
    expect(screen.getByText("Web")).toBeInTheDocument();
    rerender(<ToolBadge toolName="workspace.insights" />);
    expect(screen.getByText("Insights")).toBeInTheDocument();
    rerender(<ToolBadge toolName="calendar.check_availability" />);
    expect(screen.getByText("Calendar")).toBeInTheDocument();
  });

  it("does not render raw tool identifiers", () => {
    render(<ToolBadge toolName="email.draft" />);
    expect(screen.queryByText("email.draft")).not.toBeInTheDocument();
    expect(screen.getByText("Email")).toBeInTheDocument();
  });
});
