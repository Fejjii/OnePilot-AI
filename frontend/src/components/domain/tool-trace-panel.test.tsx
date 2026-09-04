import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ToolTracePanel } from "./tool-trace-panel";

describe("ToolTracePanel", () => {
  it("renders persisted recruiter-facing steps and tool badges", () => {
    render(
      <ToolTracePanel
        toolCalls={[
          {
            tool_name: "rag.answer",
            input_summary: "query: ignore previous instructions",
            output_summary: "chars=99 model=gpt-5-nano",
            duration_ms: 12,
            label: "Knowledge",
          },
        ]}
        executionTrace={[
          {
            key: "understanding_request",
            label: "Understanding request",
            detail: null,
            duration_ms: 3,
          },
          {
            key: "retrieving_rag_evidence",
            label: "Retrieving RAG evidence",
            detail: null,
            duration_ms: 12,
          },
        ]}
      />,
    );

    expect(screen.getByText("Understanding request")).toBeInTheDocument();
    expect(screen.getByText("Finding cited sources")).toBeInTheDocument();
    expect(screen.getByText("Knowledge")).toBeInTheDocument();
    expect(screen.queryByText(/rag\.answer/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ignore previous/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/gpt-5-nano/i)).not.toBeInTheDocument();
  });

  it("renders a safe empty state for historical messages without traces", () => {
    render(<ToolTracePanel toolCalls={[]} executionTrace={[]} />);
    expect(screen.getByTestId("execution-trace-empty")).toHaveTextContent(
      /no recorded steps for this reply/i,
    );
    expect(screen.queryByText(/classify_intent/i)).not.toBeInTheDocument();
  });

  it("does not surface hidden internal fallback steps", () => {
    render(
      <ToolTracePanel
        toolCalls={[]}
        traceSteps={[
          {
            step: "router",
            detail: "message_class=capability_or_help",
            duration_ms: 2,
          },
          { step: "recall_memory", detail: "enabled=true", duration_ms: 4 },
        ]}
      />,
    );
    expect(screen.getByTestId("execution-trace-empty")).toBeInTheDocument();
    expect(screen.queryByText(/message_class=/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/recall memory/i)).not.toBeInTheDocument();
  });
});
