import { describe, expect, it } from "vitest";
import {
  formatProviderDetailValue,
  getProviderDetailEntries,
  isProviderDiagnostic,
  normalizeProviderMode,
  resolveProviderMode,
} from "./provider-diagnostics";
import type { ProviderDiagnostic } from "@/types/api";

const liveProvider: ProviderDiagnostic = {
  name: "Serper Web Search",
  category: "search",
  configured: true,
  healthy: true,
  active: true,
  fallback_used: false,
  mode: "live",
  last_checked_at: "2024-01-01T00:00:00Z",
  details: { serper_mode: "live" },
};

const unhealthyProvider: ProviderDiagnostic = {
  name: "Google Calendar",
  category: "calendar",
  configured: true,
  healthy: false,
  active: false,
  fallback_used: false,
  mode: "unhealthy",
  reason: "Calendar provider issue: missing_calendar_scope",
  last_checked_at: "2024-01-01T00:00:00Z",
  details: {
    calendar_status_reason: "missing_calendar_scope",
    scope_check_ok: false,
  },
};

describe("provider-diagnostics helpers", () => {
  it("normalizes known provider modes", () => {
    expect(normalizeProviderMode("live")).toBe("live");
    expect(normalizeProviderMode("unhealthy")).toBe("unhealthy");
  });

  it("falls back to unhealthy for unknown modes", () => {
    expect(normalizeProviderMode("experimental")).toBe("unhealthy");
    expect(normalizeProviderMode(null)).toBe("unhealthy");
  });

  it("resolves missing providers with active fallbacks as fallback", () => {
    expect(
      resolveProviderMode({
        ...liveProvider,
        name: "Qdrant",
        category: "vector",
        configured: false,
        healthy: false,
        active: false,
        fallback_used: true,
        mode: "missing",
        details: { provider: "memory" },
      }),
    ).toBe("fallback");
    expect(resolveProviderMode(liveProvider)).toBe("live");
    expect(resolveProviderMode(unhealthyProvider)).toBe("unhealthy");
  });

  it("formats detail values safely", () => {
    expect(formatProviderDetailValue(null)).toBe("—");
    expect(formatProviderDetailValue(true)).toBe("yes");
    expect(formatProviderDetailValue({ nested: true })).toBe("configured");
    expect(formatProviderDetailValue(["a", "b"])).toBe("a, b");
  });

  it("handles unknown detail fields without crashing", () => {
    const entries = getProviderDetailEntries({
      calendar_status_reason: "missing_calendar_scope",
      future_flag: { enabled: true },
      null_field: null,
    });
    expect(entries).toEqual([
      ["calendar_status_reason", "missing_calendar_scope"],
      ["future_flag", "configured"],
      ["null_field", "—"],
    ]);
  });

  it("validates provider diagnostic shape", () => {
    expect(isProviderDiagnostic(liveProvider)).toBe(true);
    expect(isProviderDiagnostic(unhealthyProvider)).toBe(true);
    expect(isProviderDiagnostic({ name: "broken" })).toBe(false);
  });
});
