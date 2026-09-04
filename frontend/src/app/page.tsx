"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  FlaskConical,
  Landmark,
  Lock,
  Mail,
  MessageSquare,
  ScrollText,
  ShieldCheck,
  UserCheck,
  Users,
} from "lucide-react";
import { TryDemoButton } from "@/components/landing/try-demo-button";
import { LandingHeader } from "@/components/landing/landing-header";
import { LandingFooter } from "@/components/landing/landing-footer";

const CAPABILITIES = [
  {
    icon: MessageSquare,
    title: "AI workspace & chat",
    description:
      "One conversation that can answer questions, rank leads, draft follow-ups, and propose meetings — then show the sources and steps it used.",
  },
  {
    icon: BookOpen,
    title: "Knowledge & retrieval",
    description:
      "Ask about company documents and get cited answers. If the evidence is thin, the assistant says so instead of guessing.",
  },
  {
    icon: ShieldCheck,
    title: "Approvals & human control",
    description:
      "Emails and calendar changes wait for a teammate. Owners and admins decide what goes out; every decision is recorded.",
  },
  {
    icon: BarChart3,
    title: "Business insights",
    description:
      "See leads, conversations, and pending approvals in one place — including which prospects look most promising right now.",
  },
  {
    icon: Mail,
    title: "Gmail & Calendar workflows",
    description:
      "The assistant drafts emails and meeting proposals for real. In this public demo, sending mail and writing calendar events is simulated.",
  },
  {
    icon: FlaskConical,
    title: "Demo-safe by design",
    description:
      "No sign-up and no credentials. You can try the full workflow without sending a real email or creating a real calendar event.",
  },
] as const;

const SAFETY_STEPS = [
  {
    icon: MessageSquare,
    title: "The AI proposes",
    description:
      "The assistant drafts the email or meeting request and shows what it used — nothing leaves the workspace yet.",
  },
  {
    icon: UserCheck,
    title: "A human decides",
    description:
      "The action appears in the approvals queue. Only owners and admins can approve or reject it.",
  },
  {
    icon: ScrollText,
    title: "Execution is audited",
    description:
      "Approved actions are recorded. In this public demo, Gmail and Calendar side effects stay simulated.",
  },
] as const;

const SAFEGUARDS = [
  "Human approval required before any external action executes",
  "Strict tenant isolation — every query is scoped to one organization",
  "Prompt-injection checks and per-feature rate limiting",
  "Role-based access for sensitive operations",
  "Public demo locked to simulated Gmail and Calendar side effects",
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

const AUDIENCES = [
  {
    icon: Users,
    title: "Small teams with big operational load",
    description:
      "Founders and operators juggling customer email, scheduling, leads, and internal questions across too many tabs.",
  },
  {
    icon: Landmark,
    title: "Organizations that need answers, not guesses",
    description:
      "Teams whose policies, pricing, and processes live in documents — and who want AI answers grounded in those documents, with citations.",
  },
  {
    icon: Lock,
    title: "Anyone who won't hand AI the keys",
    description:
      "Businesses that want AI leverage without giving a model unilateral power to email customers or change records.",
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
        {/* Hero */}
        <section
          aria-labelledby="hero-heading"
          className="relative overflow-hidden"
        >
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_0%,rgba(99,102,241,0.12),transparent)]"
          />
          <div className="relative mx-auto grid max-w-6xl gap-12 px-4 pb-20 pt-16 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:pt-24">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
                Live public demo — no sign-up, no credentials
              </p>
              <h1
                id="hero-heading"
                className="mt-5 text-4xl font-semibold leading-tight tracking-tight text-slate-900 sm:text-5xl"
              >
                One workspace. One AI copilot for every business operation.
              </h1>
              <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
                OnePilot AI is an operations copilot for small businesses.
                A real AI assistant searches your documents, ranks leads, and
                drafts emails or meetings — then waits for a person before
                anything is sent.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-start">
                <TryDemoButton size="lg" label="Try the live demo" />
                <a
                  href="#capabilities"
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                >
                  View capabilities
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </a>
                <Link
                  href="/login"
                  className="inline-flex h-10 items-center justify-center rounded-lg px-4 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                >
                  Sign in
                </Link>
              </div>
              <p className="mt-4 text-xs text-slate-500">
                The demo opens a pre-loaded workspace. The assistant, document
                search, and approvals are real. Gmail and Calendar side effects
                are simulated — no real emails or events are created.
              </p>
            </div>

            <HeroPreview />
          </div>
        </section>

        {/* Who it's for */}
        <section
          aria-labelledby="audience-heading"
          className="border-t border-slate-200 bg-white"
        >
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <div className="max-w-2xl">
              <h2
                id="audience-heading"
                className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl"
              >
                Built for teams whose operations outgrew their inbox
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-600 sm:text-base">
                Small businesses run on scattered knowledge, repetitive email,
                and manual scheduling. OnePilot puts those operations behind
                one AI workspace — without giving up control over what
                actually goes out the door.
              </p>
            </div>
            <div className="mt-10 grid gap-6 md:grid-cols-3">
              {AUDIENCES.map((item) => (
                <div
                  key={item.title}
                  className="rounded-xl border border-slate-200 bg-slate-50/60 p-6"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600">
                    <item.icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-4 text-sm font-semibold text-slate-900">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">
                    {item.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Capabilities */}
        <section
          id="capabilities"
          aria-labelledby="capabilities-heading"
          className="scroll-mt-20 border-t border-slate-200"
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
                One assistant, several jobs — each one cited, reviewable, and
                gated before anything leaves the workspace.
              </p>
            </div>
            <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {CAPABILITIES.map((capability) => (
                <div
                  key={capability.title}
                  className="rounded-xl border border-slate-200 bg-white p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-shadow hover:shadow-md"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 text-white">
                    <capability.icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-4 text-sm font-semibold text-slate-900">
                    {capability.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">
                    {capability.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Safety */}
        <section
          id="safety"
          aria-labelledby="safety-heading"
          className="scroll-mt-20 border-t border-slate-200 bg-slate-950 text-white"
        >
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
                Human-in-the-loop by design
              </p>
              <h2
                id="safety-heading"
                className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl"
              >
                The AI proposes. Humans approve. Everything is audited.
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-300 sm:text-base">
                OnePilot treats external actions as privileged operations. No
                email is sent and no calendar event is created until a person
                with the right role approves it.
              </p>
            </div>

            <div className="mt-10 grid gap-6 md:grid-cols-3">
              {SAFETY_STEPS.map((step, index) => (
                <div
                  key={step.title}
                  className="rounded-xl border border-white/10 bg-white/5 p-6"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500/20 text-sm font-semibold text-indigo-300">
                      {index + 1}
                    </span>
                    <step.icon
                      className="h-5 w-5 text-indigo-300"
                      aria-hidden="true"
                    />
                  </div>
                  <h3 className="mt-4 text-sm font-semibold text-white">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-300">
                    {step.description}
                  </p>
                </div>
              ))}
            </div>

            <ul className="mt-10 grid gap-3 sm:grid-cols-2">
              {SAFEGUARDS.map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-sm text-slate-200">
                  <CheckCircle2
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400"
                    aria-hidden="true"
                  />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* What's real vs simulated */}
        <section
          id="whats-real"
          aria-labelledby="whats-real-heading"
          className="scroll-mt-20 border-t border-slate-200 bg-white"
        >
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <div className="max-w-2xl">
              <h2
                id="whats-real-heading"
                className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl"
              >
                What is real in this demo
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-600 sm:text-base">
                Recruiters should judge the assistant on real AI work, not on
                simulated inbox or calendar side effects. The public demo is
                honest about that split.
              </p>
            </div>
            <div className="mt-10 grid gap-6 md:grid-cols-2">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-6">
                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                  Working for real
                </p>
                <ul className="mt-4 space-y-2 text-sm text-slate-700">
                  {[
                    "OpenAI language model for answers and drafts",
                    "Document search with embeddings, Qdrant, and citations",
                    "Web search when configured",
                    "Assistant routing across knowledge, CRM, email, and calendar",
                    "CRM lead ranking and follow-up copy from stored facts",
                    "Human approval before any external send or event write",
                  ].map((item) => (
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
              <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-6">
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                  Simulated in the public demo
                </p>
                <ul className="mt-4 space-y-2 text-sm text-slate-700">
                  {[
                    "Gmail side effects — drafts and sends do not reach a real inbox",
                    "Calendar side effects — events are not written to a live calendar",
                    "No credentials or Google account are required to try the workflow",
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-2.5">
                      <FlaskConical
                        className="mt-0.5 h-4 w-4 shrink-0 text-amber-700"
                        aria-hidden="true"
                      />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <EngineeringStack />
          </div>
        </section>

        {/* Demo transparency + final CTA */}
        <section
          aria-labelledby="demo-heading"
          className="border-t border-slate-200"
        >
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <div className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 via-white to-purple-50 p-8 sm:p-12">
              <div className="max-w-2xl">
                <h2
                  id="demo-heading"
                  className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl"
                >
                  See it for yourself — one click, zero risk
                </h2>
                <p className="mt-3 text-sm leading-relaxed text-slate-600 sm:text-base">
                  The public demo opens a shared workspace with a knowledge
                  base, leads, and pending approvals. The assistant work is
                  real. Gmail and Calendar side effects stay simulated: no
                  real emails are sent, no real events are created, and no
                  credentials are required.
                </p>
                <ul className="mt-6 space-y-2.5">
                  {[
                    "Ask about company policies and get cited answers",
                    "Draft a follow-up to the most promising lead and stop at approval",
                    "Review this week's meetings and check open time slots",
                  ].map((item) => (
                    <li
                      key={item}
                      className="flex items-start gap-2.5 text-sm text-slate-700"
                    >
                      <CalendarClock
                        className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500"
                        aria-hidden="true"
                      />
                      {item}
                    </li>
                  ))}
                </ul>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-start">
                  <TryDemoButton size="lg" label="Try the demo" />
                  <Link
                    href="/register"
                    className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                  >
                    Create a workspace
                  </Link>
                </div>
              </div>
            </div>
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
      className="mt-10 rounded-xl border border-slate-200 bg-slate-50/60 p-5"
      onToggle={(event) =>
        setOpen((event.currentTarget as HTMLDetailsElement).open)
      }
    >
      <summary className="cursor-pointer select-none text-sm font-medium text-slate-800">
        Engineering details
      </summary>
      {open && (
        <div className="mt-4">
          <p className="text-sm leading-relaxed text-slate-600">
            The product workspace is a Next.js app talking to a FastAPI
            backend. The assistant routes each request to knowledge search,
            CRM, email, or calendar tools, then pauses for approval before
            any external write.
          </p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
            If a managed service is unavailable, the demo keeps working
            with safe fallbacks for search, embeddings, and rate limits.
          </p>
        </div>
      )}
    </details>
  );
}

/**
 * Static product vignette: a chat exchange stopping at the approval gate.
 * Pure markup — communicates the core interaction without screenshots.
 */
function HeroPreview() {
  return (
    <div aria-hidden="true" className="relative">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xl shadow-indigo-500/5 sm:p-5">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 text-xs font-bold text-white">
            O
          </span>
          <p className="text-xs font-semibold text-slate-900">AI Workspace</p>
          <span className="ml-auto rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
            Demo — Gmail simulated
          </span>
        </div>

        <div className="space-y-3 pt-4">
          <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-2.5 text-xs text-white">
            Draft a follow-up email to our most promising lead.
          </div>
          <div className="w-fit max-w-[90%] rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-2.5 text-xs text-slate-700">
            Draft for Sarah Chen at Brightline Analytics, based on the stored
            CRM next step. Ready when you approve it.
          </div>
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-amber-600" />
              <p className="text-xs font-semibold text-amber-800">
                Approval required
              </p>
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-amber-700">
              Email draft to Sarah Chen at Brightline Analytics — waiting for
              an owner or admin.
            </p>
            <div className="mt-2.5 flex gap-2">
              <span className="rounded-md bg-emerald-600 px-2.5 py-1 text-[10px] font-medium text-white">
                Approve
              </span>
              <span className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-medium text-slate-600">
                Reject
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-[10px] text-slate-500">
            <ScrollText className="h-3.5 w-3.5 shrink-0" />
            Recorded: draft prepared · approval pending · nothing sent
          </div>
        </div>
      </div>
    </div>
  );
}
