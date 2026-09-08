import { Lock } from "lucide-react";
import { cn } from "@/lib/utils";

type CapabilityItem = {
  label: string;
  privateWorkspace?: boolean;
  emphasis?: boolean;
};

type CapabilityLayer = {
  name: string;
  items: readonly CapabilityItem[];
};

const LAYERS: readonly CapabilityLayer[] = [
  {
    name: "Interaction",
    items: [
      { label: "Chat" },
      { label: "Voice", privateWorkspace: true },
      { label: "Multilingual" },
    ],
  },
  {
    name: "Context & Intelligence",
    items: [
      { label: "RAG / company knowledge" },
      { label: "Memory & personalization", privateWorkspace: true },
      { label: "CRM context" },
      { label: "Web research" },
    ],
  },
  {
    name: "Agent Orchestration",
    items: [
      { label: "Intent routing" },
      { label: "LangGraph" },
      { label: "Tool calling" },
      { label: "Connectors / adapters" },
    ],
  },
  {
    name: "Business Actions",
    items: [
      { label: "Email" },
      { label: "Calendar" },
      { label: "Leads" },
      { label: "Human approvals", emphasis: true },
    ],
  },
];

const TRUST_MARKS = [
  "Tenant-isolated",
  "Traced",
  "Evaluated",
  "Human-controlled",
] as const;

const PRIVATE_WORKSPACE_HINT = "Authenticated / private workspace";

/**
 * Compact production-style capability stack for the public landing hero.
 * Voice and persistent memory are marked as authenticated-workspace capabilities.
 */
export function HeroCapabilityArchitecture() {
  return (
    <aside aria-labelledby="hero-architecture-label" className="relative">
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-indigo-500/5">
        <div
          aria-hidden="true"
          className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-indigo-500 to-purple-500"
        />
        <div className="p-5 pl-6 sm:p-6 sm:pl-7">
          <p
            id="hero-architecture-label"
            className="text-[11px] font-semibold uppercase tracking-wide text-slate-500"
          >
            Capability architecture
          </p>
          <p className="sr-only">
            Voice and persistent memory are available in authenticated private
            workspaces. The public shared demo may restrict them.
          </p>

          <ul className="mt-4 divide-y divide-slate-100">
            {LAYERS.map((layer) => (
              <li
                key={layer.name}
                className="grid gap-2 py-3 first:pt-0 last:pb-0 sm:grid-cols-[9.75rem_1fr] sm:items-start sm:gap-3"
              >
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  {layer.name}
                </p>
                <ul className="flex flex-wrap gap-1.5">
                  {layer.items.map((item) => (
                    <li key={item.label}>
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-medium leading-none",
                          item.emphasis
                            ? "border-indigo-200 bg-indigo-50 text-indigo-800"
                            : "border-slate-200 bg-slate-50 text-slate-700",
                        )}
                        title={
                          item.privateWorkspace
                            ? PRIVATE_WORKSPACE_HINT
                            : undefined
                        }
                      >
                        {item.label}
                        {item.privateWorkspace ? (
                          <Lock
                            className="h-2.5 w-2.5 text-slate-400"
                            aria-label={PRIVATE_WORKSPACE_HINT}
                          />
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>

          <p className="mt-4 border-t border-slate-100 pt-3 text-[10px] font-medium uppercase tracking-wide text-slate-400">
            {TRUST_MARKS.join(" · ")}
          </p>
        </div>
      </div>
    </aside>
  );
}
