import {
  BrainCircuit,
  Cable,
  Lock,
  Send,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

type LayerItem = {
  label: string;
  privateWorkspace?: boolean;
  integrationReady?: boolean;
};

type OperatingLayer = {
  name: string;
  icon: LucideIcon;
  items: readonly LayerItem[];
};

const LAYERS: readonly OperatingLayer[] = [
  {
    name: "Understand",
    icon: BrainCircuit,
    items: [
      { label: "Knowledge" },
      { label: "RAG" },
      { label: "Memory", privateWorkspace: true },
      { label: "CRM" },
      { label: "Web" },
    ],
  },
  {
    name: "Reason",
    icon: Workflow,
    items: [
      { label: "Context" },
      { label: "Lead priority" },
      { label: "Agent workflows" },
      { label: "Tool calling" },
    ],
  },
  {
    name: "Execute",
    icon: Send,
    items: [
      { label: "Email" },
      { label: "Scheduling" },
      { label: "Follow-ups" },
      { label: "CRM actions" },
      { label: "Approvals" },
    ],
  },
  {
    name: "Connect",
    icon: Cable,
    items: [
      { label: "Google Workspace" },
      { label: "APIs" },
      { label: "CRM" },
      { label: "Payments", integrationReady: true },
      { label: "Communications", integrationReady: true },
    ],
  },
];

const PRIVATE_WORKSPACE_HINT = "Authenticated / private workspace";
const INTEGRATION_READY_HINT =
  "Integration-ready — not a live production connector";

function LayerItemList({ items }: { items: readonly LayerItem[] }) {
  return (
    <>
      {items.map((item, itemIndex) => (
        <span key={item.label}>
          {itemIndex > 0 ? (
            <span aria-hidden="true" className="px-1.5 text-slate-600">
              ·
            </span>
          ) : null}
          <span
            className={cn(item.integrationReady && "text-slate-500")}
            title={
              item.privateWorkspace
                ? PRIVATE_WORKSPACE_HINT
                : item.integrationReady
                  ? INTEGRATION_READY_HINT
                  : undefined
            }
            aria-label={
              item.integrationReady
                ? `${item.label}. ${INTEGRATION_READY_HINT}`
                : undefined
            }
          >
            {item.label}
            {item.privateWorkspace ? (
              <Lock
                className="ml-1 inline h-2.5 w-2.5 -translate-y-px text-slate-500"
                aria-label={PRIVATE_WORKSPACE_HINT}
              />
            ) : null}
          </span>
        </span>
      ))}
    </>
  );
}

function LayerCapabilities({ items }: { items: readonly LayerItem[] }) {
  const liveItems = items.filter((item) => !item.integrationReady);
  const readyItems = items.filter((item) => item.integrationReady);

  return (
    <div className="mt-1 space-y-0.5">
      <p className="text-[12px] leading-relaxed text-slate-400">
        <LayerItemList items={liveItems} />
      </p>
      {readyItems.length > 0 ? (
        <p className="text-[12px] leading-relaxed text-slate-500">
          <span className="mr-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Ready
          </span>
          <LayerItemList items={readyItems} />
        </p>
      ) : null}
    </div>
  );
}

/**
 * Compact operating-layer visual for the public landing hero.
 * Positions OnePilot as a grounded, human-controlled operations layer
 * without implying live HubSpot, payments, or communications connectors.
 */
export function HeroOperatingLayer() {
  return (
    <aside
      aria-labelledby="hero-operating-layer-heading"
      className="relative"
    >
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl shadow-indigo-950/30">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-400/60 to-transparent"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-16 -top-20 h-48 w-48 rounded-full bg-indigo-500/20 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-24 -left-10 h-40 w-40 rounded-full bg-violet-600/15 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:linear-gradient(to_right,rgba(255,255,255,0.35)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.35)_1px,transparent_1px)] [background-size:28px_28px]"
        />

        <div className="relative px-5 py-5 sm:px-6 sm:py-6">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-indigo-300/80">
            Operating layer
          </p>
          <p
            id="hero-operating-layer-heading"
            className="mt-2 text-[1.35rem] font-semibold leading-snug tracking-tight text-white sm:text-2xl"
          >
            From scattered business tools
            <span className="mt-1 block font-medium text-slate-300">
              to one intelligent operating layer.
            </span>
          </p>

          <p className="sr-only">
            Memory is available in authenticated private workspaces. Payments
            and communications connectors are integration-ready, not live
            production integrations.
          </p>

          <div className="relative mt-5">
            <div
              aria-hidden="true"
              className="absolute bottom-4 left-[15px] top-4 w-px bg-gradient-to-b from-indigo-400/70 via-violet-400/35 to-slate-600/50"
            />
            <ol className="m-0 list-none p-0">
              {LAYERS.map((layer, index) => (
                <li
                  key={layer.name}
                  className="relative grid grid-cols-[32px_1fr] items-start gap-3 py-2.5 first:pt-0 last:pb-0"
                >
                  <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full border border-indigo-400/35 bg-slate-950 text-indigo-200 shadow-[0_0_16px_rgba(99,102,241,0.28)]">
                    <layer.icon className="h-3.5 w-3.5" aria-hidden="true" />
                  </div>
                  <div className="min-w-0 pt-0.5">
                    <div className="flex items-baseline gap-2">
                      <span className="font-mono text-[10px] tabular-nums text-slate-500">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                        {layer.name}
                      </p>
                    </div>
                    <LayerCapabilities items={layer.items} />
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <p className="mt-5 border-t border-white/10 pt-4 text-[12px] leading-relaxed tracking-wide text-slate-400">
            Grounded in context. Connected to tools. Controlled by humans.
          </p>
        </div>
      </div>
    </aside>
  );
}
