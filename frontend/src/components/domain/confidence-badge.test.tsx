import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBadge } from "./confidence-badge";

describe("ConfidenceBadge", () => {
  it("shows grounded source copy instead of a raw score when citations exist", () => {
    render(<ConfidenceBadge value={0.25} citationCount={1} />);
    expect(screen.getByText(/grounded in 1 source/i)).toBeInTheDocument();
    expect(screen.queryByText(/25%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/low confidence/i)).not.toBeInTheDocument();
  });

  it("shows raw confidence only when explicitly requested", () => {
    render(<ConfidenceBadge value={0.85} showRawScore />);
    expect(screen.getByText(/high confidence/i)).toBeInTheDocument();
    expect(screen.getByText(/85%/)).toBeInTheDocument();
  });

  it("caps display when weak evidence is flagged", () => {
    render(<ConfidenceBadge value={0.85} weakEvidence showRawScore />);
    expect(screen.queryByText(/high confidence/i)).not.toBeInTheDocument();
    expect(screen.getByText(/60%/)).toBeInTheDocument();
  });

  it("uses weak-evidence copy in recruiter-facing mode", () => {
    render(<ConfidenceBadge value={0.85} weakEvidence />);
    expect(screen.getByText(/weak evidence/i)).toBeInTheDocument();
    expect(screen.queryByText(/85%/)).not.toBeInTheDocument();
  });
});
