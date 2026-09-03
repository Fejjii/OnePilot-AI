import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { IntentBadge } from "./intent-badge";

const CASES: Array<[string, string]> = [
  ["general_assistant", "General"],
  ["knowledge_search", "Knowledge"],
  ["web_search", "Web search"],
  ["web_and_knowledge", "Web + KB"],
  ["lead_support", "Lead"],
  ["email_drafting", "Email"],
  ["calendar_availability", "Calendar"],
  ["calendar_scheduling", "Scheduling"],
  ["calendar_and_email", "Calendar + Email"],
  ["document_summary", "Summary"],
  ["workflow_action", "Workflow"],
  ["compound_workflow", "Workflow"],
  ["workspace_insights", "Insights"],
  ["out_of_scope", "Out of scope"],
  ["clarification", "Clarify"],
];

describe("IntentBadge", () => {
  it.each(CASES)("renders recruiter label for %s", (intent, label) => {
    render(<IntentBadge intent={intent} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});
