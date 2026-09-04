import { describe, expect, it } from "vitest";
import { PROMPT_SUGGESTIONS } from "./prompt-suggestions";

describe("PROMPT_SUGGESTIONS", () => {
  it("covers distinct recruiter demo capabilities without near-duplicates", () => {
    const labels = PROMPT_SUGGESTIONS.map((item) => item.label);
    const prompts = PROMPT_SUGGESTIONS.map((item) => item.prompt);

    expect(labels).toEqual([
      "Summarize business activity",
      "Review pending approvals",
      "Search the knowledge base",
      "Analyze leads",
      "Draft a follow-up email",
      "Show this week's meetings",
      "Find open meeting times",
    ]);
    expect(new Set(labels).size).toBe(labels.length);
    expect(new Set(prompts).size).toBe(prompts.length);

    expect(prompts[0]).toMatch(/summarize our recent business activity/i);
    expect(prompts[1]).toMatch(/approvals are currently pending/i);
    expect(prompts[2]).toMatch(/escalation policy/i);
    expect(prompts[3]).toMatch(/most promising ones/i);
    expect(prompts[4]).toMatch(/most promising lead/i);
    expect(prompts[5]).toBe("Show my meetings this week.");
    expect(prompts[6]).toMatch(/calendar availability/i);
  });
});
