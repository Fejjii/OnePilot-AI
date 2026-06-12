import { describe, it, expect } from "vitest";
import {
  parseEvidenceContent,
  parseSourceLine,
  parseStructuredResponse,
} from "./parse-structured-response";

const STRUCTURED_SAMPLE = `## Summary
NovaEdge offers a 30-day refund for annual plans.

## Key points
- Refunds apply within 30 days of purchase
- Monthly plans are non-refundable
- Contact support to initiate a refund

## Evidence or sources
- [NovaEdge Refund Policy]: Annual subscriptions may be refunded within 30 days.

## Suggested next action
Contact NovaEdge support with your invoice to start a refund request.`;

describe("parseStructuredResponse", () => {
  it("parses standard knowledge sections", () => {
    const parsed = parseStructuredResponse(STRUCTURED_SAMPLE);
    expect(parsed.kind).toBe("structured");
    if (parsed.kind !== "structured") return;

    expect(parsed.sections.map((section) => section.id)).toEqual([
      "summary",
      "key-points",
      "evidence",
      "next-action",
    ]);
    expect(parsed.sections[0].content).toContain("30-day refund");
    expect(parsed.sections[1].items).toHaveLength(3);
  });

  it("parses calendar meeting proposals as structured cards", () => {
    const parsed = parseStructuredResponse(
      [
        "Title: Demo call",
        "Date and time: 2026-06-13T15:00:00 – 2026-06-13T15:30:00",
        "Timezone: Europe/Berlin",
        "Approval status: pending",
        "Provider mode: live",
        "Next action: Review and approve to create the calendar event.",
      ].join("\n"),
    );
    expect(parsed.kind).toBe("meeting-proposal");
    if (parsed.kind !== "meeting-proposal") return;
    expect(parsed.proposal.title).toBe("Demo call");
    expect(parsed.proposal.startTime).toContain("15:00:00");
    expect(parsed.proposal.timezone).toBe("Europe/Berlin");
    expect(parsed.proposal.approvalStatus).toBe("pending");
  });

  it("parses email drafts without markdown headings", () => {
    const parsed = parseStructuredResponse(
      "Subject: Follow-up on demo\n\nHi Alex,\n\nThanks for your time today.",
    );
    expect(parsed.kind).toBe("email");
    if (parsed.kind !== "email") return;
    expect(parsed.subject).toBe("Follow-up on demo");
    expect(parsed.body).toContain("Thanks for your time");
  });

  it("falls back to plain text for short answers", () => {
    const parsed = parseStructuredResponse(
      "I couldn't find enough information in the knowledge base to answer that confidently.",
    );
    expect(parsed.kind).toBe("plain");
  });

  it("parses compound workflow sections and keeps nested research markdown", () => {
    const parsed = parseStructuredResponse(
      [
        "## External market research",
        "## Summary",
        "Market demand is rising.",
        "",
        "## Key points",
        "- Automation adoption is accelerating",
        "",
        "## Draft email preview",
        "Subject: Trends update",
        "",
        "Hello team,",
        "",
        "## Meeting proposal",
        "Meeting proposal: Strategy sync",
      ].join("\n"),
    );

    expect(parsed.kind).toBe("compound");
    if (parsed.kind !== "compound") return;
    expect(parsed.sections.map((section) => section.id)).toEqual([
      "external-research",
      "email-preview",
      "meeting-proposal",
    ]);
    expect(parsed.sections[0].content).toContain("## Summary");
    expect(parsed.sections[0].content).toContain("Automation adoption");
  });
});

describe("parseSourceLine", () => {
  it("extracts web source title, url, and snippet", () => {
    const source = parseSourceLine(
      "- **Bitcoin Price** (https://example.com/btc): Trading near recent highs [published: 2024-01-01]",
    );
    expect(source.title).toBe("Bitcoin Price");
    expect(source.url).toBe("https://example.com/btc");
    expect(source.snippet).toContain("Trading near");
    expect(source.published).toBe("2024-01-01");
  });
});

describe("parseEvidenceContent", () => {
  it("groups internal and web evidence subsections", () => {
    const evidence = parseEvidenceContent(
      [
        "**Internal knowledge**",
        "- [NovaEdge Services Overview]: Managed IT and security",
        "",
        "**Web sources**",
        "- **Trend Report** (https://example.com): SMB automation is growing",
      ].join("\n"),
    );

    expect(evidence.subsections).toHaveLength(2);
    expect(evidence.subsections[0].label).toBe("Internal knowledge");
    expect(evidence.subsections[1].items[0].title).toBe("Trend Report");
  });
});
