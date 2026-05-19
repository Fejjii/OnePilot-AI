import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBadge } from "./confidence-badge";

describe("ConfidenceBadge", () => {
  it("shows high confidence for strong answers", () => {
    render(<ConfidenceBadge value={0.85} />);
    expect(screen.getByText(/high confidence/i)).toBeInTheDocument();
    expect(screen.getByText(/85%/)).toBeInTheDocument();
  });

  it("caps display when weak evidence is flagged", () => {
    render(<ConfidenceBadge value={0.85} weakEvidence />);
    expect(screen.queryByText(/high confidence/i)).not.toBeInTheDocument();
    expect(screen.getByText(/60%/)).toBeInTheDocument();
  });
});
