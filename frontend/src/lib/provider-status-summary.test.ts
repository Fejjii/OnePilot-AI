import { describe, it, expect } from "vitest";
import { summarizeProviderStatus } from "./provider-status-summary";
import type { ProviderDiagnostic } from "@/types/api";

function provider(
  name: string,
  category: string,
  mode: string,
  healthy = true,
): ProviderDiagnostic {
  return {
    name,
    category: category as ProviderDiagnostic["category"],
    configured: true,
    healthy,
    active: true,
    fallback_used: mode === "fallback",
    mode: mode as ProviderDiagnostic["mode"],
    model: null,
    reason: null,
    last_checked_at: "2026-07-19T00:00:00Z",
    details: null,
  };
}

describe("summarizeProviderStatus", () => {
  it("fails gracefully when diagnostics are unavailable", () => {
    expect(summarizeProviderStatus(null).label).toBe(
      "Provider status unavailable",
    );
    expect(summarizeProviderStatus([]).tone).toBe("muted");
  });

  it("labels public-demo mock Gmail/Calendar as simulated integrations", () => {
    const summary = summarizeProviderStatus([
      provider("Gmail", "email", "mock"),
      provider("Google Calendar", "calendar", "mock"),
      provider("Qdrant", "vector", "local"),
      provider("OpenAI LLM", "llm", "fallback"),
      provider("Postgres", "database", "live"),
    ]);
    expect(summary.label).toBe("Simulated integrations");
    expect(summary.detail).toContain("Gmail: Simulated");
    expect(summary.detail).toContain("Calendar: Simulated");
    expect(summary.detail).toContain("Retrieval: Fallback");
    expect(summary.tone).toBe("warn");
  });

  it("does not claim Live when retrieval is on fallback", () => {
    const summary = summarizeProviderStatus([
      provider("Gmail", "email", "live"),
      provider("Google Calendar", "calendar", "live"),
      provider("Qdrant", "vector", "fallback"),
      provider("OpenAI LLM", "llm", "live"),
      provider("Postgres", "database", "live"),
    ]);
    expect(summary.label).not.toBe("Live providers");
    expect(summary.label).toBe("Fallback providers");
    expect(summary.detail).toContain("Retrieval: Fallback");
  });

  it("reports Live only when core integrations are live", () => {
    const summary = summarizeProviderStatus([
      provider("Gmail", "email", "live"),
      provider("Google Calendar", "calendar", "live"),
      provider("Qdrant", "vector", "live"),
      provider("OpenAI LLM", "llm", "live"),
      provider("Postgres", "database", "live"),
    ]);
    expect(summary.label).toBe("Live providers");
    expect(summary.tone).toBe("ok");
  });

  it("marks unavailable Gmail as degraded", () => {
    const summary = summarizeProviderStatus([
      provider("Gmail", "email", "missing", false),
      provider("Google Calendar", "calendar", "live"),
      provider("Qdrant", "vector", "live"),
      provider("OpenAI LLM", "llm", "live"),
      provider("Postgres", "database", "live"),
    ]);
    expect(summary.label).toBe("Providers degraded");
    expect(summary.detail).toContain("Gmail: Unavailable");
    expect(summary.tone).toBe("danger");
  });

  it("treats missing Qdrant with fallback_used as Fallback, not Unavailable", () => {
    const summary = summarizeProviderStatus([
      provider("Gmail", "email", "mock"),
      provider("Google Calendar", "calendar", "mock"),
      {
        ...provider("Qdrant", "vector", "missing", false),
        configured: false,
        active: false,
        fallback_used: true,
        details: { provider: "memory" },
      },
      {
        ...provider("OpenAI LLM", "llm", "missing", false),
        configured: false,
        active: false,
        fallback_used: true,
      },
      provider("Postgres", "database", "live"),
    ]);
    expect(summary.label).toBe("Simulated integrations");
    expect(summary.detail).toContain("Retrieval: Fallback");
    expect(summary.detail).not.toContain("Retrieval: Unavailable");
  });
});
