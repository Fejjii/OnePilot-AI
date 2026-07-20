import { resolveProviderMode } from "@/lib/provider-diagnostics";
import type { ProviderDiagnostic, ProviderMode } from "@/types/api";

export type ProviderStatusTone = "ok" | "warn" | "danger" | "muted";

export interface ProviderStatusSummary {
  /** Primary label shown in the app header. */
  label: string;
  tone: ProviderStatusTone;
  /** Compact secondary line (integration modes). */
  detail: string;
}

const MODE_LABEL: Record<ProviderMode, string> = {
  live: "Live",
  mock: "Simulated",
  fallback: "Fallback",
  local: "Fallback",
  missing: "Unavailable",
  optional: "Optional",
  unhealthy: "Unavailable",
};

function findByName(
  providers: ProviderDiagnostic[],
  name: string,
): ProviderDiagnostic | undefined {
  return providers.find((p) => p.name === name);
}

function findByCategory(
  providers: ProviderDiagnostic[],
  category: string,
): ProviderDiagnostic | undefined {
  return providers.find((p) => p.category === category);
}

function modeOf(provider: ProviderDiagnostic | undefined): ProviderMode {
  if (!provider) return "missing";
  return resolveProviderMode(provider);
}

function isLive(mode: ProviderMode): boolean {
  return mode === "live";
}

function isSimulated(mode: ProviderMode): boolean {
  return mode === "mock";
}

function isUnavailable(mode: ProviderMode): boolean {
  return mode === "missing" || mode === "unhealthy";
}

function isFallbackish(mode: ProviderMode): boolean {
  return mode === "fallback" || mode === "local";
}

/**
 * Derive a concise, truthful header label from `/providers` diagnostics.
 * Never claims "Live" when Gmail/Calendar/retrieval are simulated or on fallback.
 */
export function summarizeProviderStatus(
  providers: ProviderDiagnostic[] | null | undefined,
): ProviderStatusSummary {
  if (!providers || providers.length === 0) {
    return {
      label: "Provider status unavailable",
      tone: "muted",
      detail: "Could not load diagnostics",
    };
  }

  const gmail = modeOf(findByName(providers, "Gmail"));
  const calendar = modeOf(findByName(providers, "Google Calendar"));
  const retrieval = modeOf(findByCategory(providers, "vector"));
  const llm = modeOf(findByName(providers, "OpenAI LLM"));
  const database = modeOf(findByName(providers, "Postgres"));

  const detailParts = [
    `Gmail: ${MODE_LABEL[gmail]}`,
    `Calendar: ${MODE_LABEL[calendar]}`,
    `Retrieval: ${MODE_LABEL[retrieval]}`,
  ];
  const detail = detailParts.join(" · ");

  if (isUnavailable(database)) {
    return {
      label: "Database unavailable",
      tone: "danger",
      detail,
    };
  }

  // Public-demo / mock-safe posture: both mail and calendar simulated.
  if (isSimulated(gmail) && isSimulated(calendar)) {
    return {
      label: "Simulated integrations",
      tone: "warn",
      detail,
    };
  }

  if (
    isUnavailable(gmail) ||
    isUnavailable(calendar) ||
    isUnavailable(retrieval) ||
    isUnavailable(llm)
  ) {
    return {
      label: "Providers degraded",
      tone: "danger",
      detail,
    };
  }

  const coreLive =
    isLive(llm) &&
    isLive(retrieval) &&
    isLive(gmail) &&
    isLive(calendar);

  if (coreLive) {
    return {
      label: "Live providers",
      tone: "ok",
      detail,
    };
  }

  if (isFallbackish(retrieval) || isFallbackish(llm)) {
    return {
      label: "Fallback providers",
      tone: "warn",
      detail,
    };
  }

  return {
    label: "Mixed providers",
    tone: "warn",
    detail,
  };
}
