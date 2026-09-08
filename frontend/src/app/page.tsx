"use client";

import { useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  FlaskConical,
  Mail,
  ShieldCheck,
  Users,
} from "lucide-react";
import { TryDemoButton } from "@/components/landing/try-demo-button";
import { LandingHeader } from "@/components/landing/landing-header";
import { LandingFooter } from "@/components/landing/landing-footer";
import { HeroOperatingLayer } from "@/components/landing/hero-operating-layer";
import { PRODUCT_GITHUB_URL } from "@/lib/product";

const NOVAEDGE_NOTE =
  "NovaEdge Solutions is the preloaded sample company used to demonstrate RAG, leads and workflows.";

const CAPABILITY_GROUPS = [
  {
    icon: BookOpen,
    title: "Knowledge & Research",
    items: [
      "RAG over company documents",
      "Web research when configured",
      "Citations on grounded answers",
    ],
  },
  {
    icon: Users,
    title: "CRM & Leads",
    items: [
      "Lead intelligence from stored facts",
      "Ranking and context",
      "Grounded follow-ups",
    ],
  },
  {
    icon: Mail,
    title: "Email & Calendar",
    items: [
      "Drafts prepared in the workspace",
      "Availability and meeting proposals",
      "API-connected private implementation",
    ],
  },
  {
    icon: ShieldCheck,
    title: "Safe Agentic Execution",
    items: [
      "Human-in-the-loop approvals",
      "Traces and auditability",
      "Evaluation and safety guards",
    ],
  },
] as const;

const PUBLIC_TRACK = [
  "Real AI, RAG, web, and CRM logic",
  "Gmail simulated",
  "Calendar simulated",
  "HITL approvals remain real",
] as const;

const PRIVATE_TRACK = [
  "Same core agent",
  "Org-restricted live Gmail",
  "Org-restricted live Google Calendar",
  "Approval-gated external actions",
] as const;

const TECH_STACK = [
  {
    name: "FastAPI",
    role: "Typed Python backend with layered routers, services, and repositories",
  },
  {
    name: "Next.js",
    role: "App Router frontend with TanStack Query and Tailwind CSS",
  },
  {
    name: "LangGraph",
    role: "Agent orchestration: intent routing, tool calls, and approval hand-offs",
  },
  {
    name: "PostgreSQL",
    role: "Multi-tenant data model with Alembic-managed migrations",
  },
  {
    name: "Redis",
    role: "Rate limiting and caching, with a safe in-memory fallback",
  },
  {
    name: "Qdrant",
    role: "Vector search for retrieval, with deterministic fallback retrieval",
  },
  {
    name: "Railway",
    role: "Backend, PostgreSQL, and Redis hosting for the public demo",
  },
  {
    name: "Vercel",
    role: "Frontend hosting and deployments for the public demo",
  },
] as const;

export default function LandingPage() {
  return (
    <div className="min-h-full bg-slate-50">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-slate-900 focus:shadow-lg"
      >
        Skip to content
      </a>

      <LandingHeader />

      <main id="main-content">
        <section aria-labelledby="hero-heading" className="relative overflow-hidden">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_0%,rgba(99,102,241,0.12),transparent)]"
          />
          <div className="relative mx-auto grid max-w-6xl gap-12 px-4 pb-20 pt-16 sm:px-6 lg:grid-cols-[1.15fr_0.85fr] lg:items-center lg:pt-24">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
                Live public demo — no sign-up, no credentials
              </p>
              <h1
                id="hero-heading"
                className="mt-5 text-4xl font-semibold leading-tight tracking-tight text-slate-900 sm:text-5xl"
              >
                One AI workspace for business knowledge and operations.
              </h1>
              <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
                OnePilot can search company knowledge, research the web, work
                with leads, draft emails and schedule meetings, while keeping a
                human approval gate before external actions execute.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-start">
                <TryDemoButton size="lg" label="Try the live demo" />
                <a
                  href={PRODUCT_GITHUB_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                >
                  View GitHub
                </a>
              </div>
              <p className="mt-4 text-xs text-slate-500">{NOVAEDGE_NOTE}</p>
            </div>

            <HeroOperatingLayer />
          </div>
        </section>

        <section
          id="capabilities"
          aria-labelledby="capabilities-heading"
          className="scroll-mt-20 border-t border-slate-200 bg-white"
        >
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <div className="max-w-2xl">
              <h2
                id="capabilities-heading"
                className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl"
              >
                What OnePilot can do
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-600 sm:text-base">
                Four capability groups. Each one is reviewable, and external
                writes wait for a person.
              </p>
            </div>
            <div className="mt-10 grid gap-6 sm:grid-cols-2">
              {CAPABILITY_GROUPS.map((group) => (
                <div
                  key={group.title}
                  className="rounded-xl border border-slate-200 bg-slate-50/40 p-6"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 text-white">
                    <group.icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-4 text-sm font-semibold text-slate-900">
                    {group.title}
                  </h3>
                  <ul className="mt-3 space-y-1.5">
                    {group.items.map((item) => (
                      <li
                        key={item}
                        className="flex items-start gap-2 text-sm leading-relaxed text-slate-600"
                      >
                        <CheckCircle2
                          className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500"
                          aria-hidden="true"
                        />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section
          id="public-vs-live"
          aria-labelledby="public-vs-live-heading"
          className="scroll-mt-20 border-t border-slate-200"
        >
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <div className="max-w-2xl">
              <h2
                id="public-vs-live-heading"
                className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl"
              >
                Public demo vs live integrations
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-600 sm:text-base">
                The public demo is the same agent with simulated Gmail and
                Calendar side effects. A private, org-restricted track can
                connect live Google APIs. HubSpot is a mock adapter today, not
                a live production connector.
              </p>
            </div>
            <div className="mt-10 grid gap-6 md:grid-cols-2">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-6">
                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                  Public
                </p>
                <ul className="mt-4 space-y-2 text-sm text-slate-700">
                  {PUBLIC_TRACK.map((item) => (
                    <li key={item} className="flex items-start gap-2.5">
                      <CheckCircle2
                        className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                        aria-hidden="true"
                      />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-6">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                  Private validated track
                </p>
                <ul className="mt-4 space-y-2 text-sm text-slate-700">
                  {PRIVATE_TRACK.map((item) => (
                    <li key={item} className="flex items-start gap-2.5">
                      <ShieldCheck
                        className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600"
                        aria-hidden="true"
                      />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section
          id="architecture"
          aria-labelledby="architecture-heading"
          className="scroll-mt-20 border-t border-slate-200 bg-white"
        >
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <div className="max-w-2xl">
              <h2
                id="architecture-heading"
                className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl"
              >
                Architecture
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-600 sm:text-base">
                Next.js talks to a FastAPI backend. The assistant routes each
                request to knowledge, CRM, email, or calendar tools, then pauses
                for approval before any external write.
              </p>
            </div>
            <EngineeringStack />
          </div>
        </section>
      </main>

      <LandingFooter />
    </div>
  );
}

function EngineeringStack() {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="mt-8 rounded-xl border border-slate-200 bg-slate-50/60 p-5"
      onToggle={(event) =>
        setOpen((event.currentTarget as HTMLDetailsElement).open)
      }
    >
      <summary className="cursor-pointer select-none text-sm font-medium text-slate-800">
        Engineering details
      </summary>
      {open && (
        <div className="mt-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {TECH_STACK.map((tech) => (
              <div
                key={tech.name}
                className="rounded-xl border border-slate-200 bg-white p-5"
              >
                <p className="text-sm font-semibold text-slate-900">
                  {tech.name}
                </p>
                <p className="mt-2 text-xs leading-relaxed text-slate-600">
                  {tech.role}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-6 text-xs text-slate-500">
            If a managed service is unavailable, the demo keeps working with
            safe fallbacks for search, embeddings, and rate limits.
          </p>
        </div>
      )}
    </details>
  );
}
