"use client";

import { FlaskConical } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { useDemoModeFlag } from "@/lib/auth";
import { normalizeProviderMode } from "@/lib/provider-diagnostics";
import { useProviderDiagnostics } from "@/lib/queries";
import type { ProviderDiagnostic, ProviderMode } from "@/types/api";

const INTEGRATION_LABELS: Record<ProviderMode, string> = {
  live: "Live",
  mock: "Simulated",
  fallback: "Fallback",
  local: "Local",
  missing: "Not configured",
  optional: "Optional",
  unhealthy: "Unavailable",
};

const INTEGRATION_TONES: Record<ProviderMode, BadgeTone> = {
  live: "success",
  mock: "warning",
  fallback: "warning",
  local: "info",
  missing: "muted",
  optional: "muted",
  unhealthy: "danger",
};

function retrievalLabel(provider: ProviderDiagnostic): {
  label: string;
  tone: BadgeTone;
} {
  const mode = normalizeProviderMode(provider.mode);
  if (!provider.healthy || mode === "unhealthy") {
    return { label: "Unavailable", tone: "danger" };
  }
  if (mode === "live") {
    return { label: "Vector search", tone: "success" };
  }
  // local / fallback = documented in-memory or deterministic fallback retrieval
  return { label: "Fallback ready", tone: "info" };
}

function IntegrationBadge({
  label,
  provider,
}: {
  label: string;
  provider: ProviderDiagnostic;
}) {
  const mode = normalizeProviderMode(provider.mode);
  return (
    <Badge tone={INTEGRATION_TONES[mode]}>
      {label}: {INTEGRATION_LABELS[mode]}
    </Badge>
  );
}

/**
 * Provider-transparency strip for the AI workspace. Shows whether the session
 * is a demo, whether Gmail/Calendar are simulated or live, and whether
 * knowledge retrieval is available — sourced from the same `/providers`
 * diagnostics used on the dashboard and settings pages. Renders nothing while
 * diagnostics are unavailable so the workspace never blocks on it.
 */
export function WorkspaceStatusBadges() {
  const isDemo = useDemoModeFlag();
  const diagnostics = useProviderDiagnostics();
  const providers = diagnostics.data?.providers ?? [];
  const gmail = providers.find((p) => p.name === "Gmail");
  const calendar = providers.find((p) => p.name === "Google Calendar");
  const retrieval = providers.find((p) => p.category === "vector");

  if (!isDemo && providers.length === 0) return null;

  const retrievalStatus = retrieval ? retrievalLabel(retrieval) : null;

  return (
    <div
      role="status"
      aria-label="Workspace integration status"
      className="flex flex-wrap items-center gap-2"
    >
      {isDemo && (
        <Badge
          tone="warning"
          icon={<FlaskConical className="h-3 w-3" aria-hidden="true" />}
        >
          Demo mode — actions simulated
        </Badge>
      )}
      {gmail && <IntegrationBadge label="Gmail" provider={gmail} />}
      {calendar && <IntegrationBadge label="Calendar" provider={calendar} />}
      {retrievalStatus && (
        <Badge tone={retrievalStatus.tone}>
          Knowledge retrieval: {retrievalStatus.label}
        </Badge>
      )}
    </div>
  );
}
