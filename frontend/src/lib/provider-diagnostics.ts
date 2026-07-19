import type { ProviderDiagnostic, ProviderMode } from "@/types/api";

const PROVIDER_MODES: readonly ProviderMode[] = [
  "live",
  "fallback",
  "mock",
  "local",
  "missing",
  "optional",
  "unhealthy",
];

export function normalizeProviderMode(mode: unknown): ProviderMode {
  if (typeof mode === "string" && PROVIDER_MODES.includes(mode as ProviderMode)) {
    return mode as ProviderMode;
  }
  return "unhealthy";
}

/**
 * Resolve the mode recruiters/operators should see.
 *
 * Backend diagnostics often report optional infra as `mode=missing` with
 * `fallback_used=true` (e.g. Qdrant unset → in-memory vectors). That is a
 * working fallback, not an outage — surface it as `fallback`.
 */
export function resolveProviderMode(provider: ProviderDiagnostic): ProviderMode {
  const mode = normalizeProviderMode(provider.mode);
  if (provider.fallback_used && (mode === "missing" || mode === "unhealthy")) {
    return "fallback";
  }
  return mode;
}

export function formatProviderDetailValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "boolean") {
    return value ? "yes" : "no";
  }
  if (typeof value === "number" || typeof value === "string") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => formatProviderDetailValue(item)).join(", ");
  }
  if (typeof value === "object") {
    return "configured";
  }
  return String(value);
}

export function getProviderDetailEntries(
  details: Record<string, unknown> | null | undefined
): Array<[string, string]> {
  if (!details) {
    return [];
  }
  return Object.entries(details).map(([key, value]) => [
    key,
    formatProviderDetailValue(value),
  ]);
}

export function isProviderDiagnostic(value: unknown): value is ProviderDiagnostic {
  if (!value || typeof value !== "object") {
    return false;
  }
  const p = value as ProviderDiagnostic;
  return (
    typeof p.name === "string" &&
    typeof p.configured === "boolean" &&
    typeof p.healthy === "boolean" &&
    typeof p.active === "boolean" &&
    typeof p.fallback_used === "boolean" &&
    typeof p.last_checked_at === "string"
  );
}
