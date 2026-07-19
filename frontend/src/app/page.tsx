"use client";

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
      "A conversational workspace where a multi-intent agent answers questions, drafts emails, and proposes actions — with structured responses and full tool traces for every step.",
  },
  {
    icon: BookOpen,
    title: "Knowledge & retrieval",
    description:
      "Upload company documents and get grounded answers with citations. Retrieval-augmented generation with confidence scoring, reranking, and honest fallbacks when evidence is weak.",
  },
  {
    icon: ShieldCheck,
    title: "Approvals & human control",
    description:
      "Every external action — sending email, creating events, updating records — is held for explicit human approval. Owners and admins decide; everything is audited.",
  },
  {
    icon: BarChart3,
    title: "Business insights",
    description:
      "A live dashboard for leads, conversations, usage, and estimated cost, so teams see what the AI is doing and what it costs — per organization, in real time.",
  },
  {
    icon: Mail,
    title: "Gmail & Calendar workflows",
    description:
      "Draft customer emails, check availability, and propose meeting slots. Integrations run live or fully simulated, and always behind the approval gate.",
  },
  {
    icon: FlaskConical,
    title: "Demo-safe by design",
    description:
      "The public demo runs entirely on mock providers: no real emails, no real calendar events, no credentials required — the safeguards are enforced by server configuration.",
  },
] as const;

const SAFETY_STEPS = [
  {
    icon: MessageSquare,
    title: "The AI proposes",
    description:
      "The agent drafts the email or meeting request and explains its reasoning — nothing leaves the workspace yet.",
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
      "Approved actions run through the configured provider and land in a per-organization audit log.",
  },
] as const;

const SAFEGUARDS = [
  "Human approval required before any external action executes",
  "Strict tenant isolation — every query is scoped to one organization",
  "Prompt-injection detection and per-feature rate limiting",
  "Role-based access control for sensitive operations",
  "Public demo locked to simulated Gmail and Calendar providers",
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
                OnePilot AI is an AI operations platform for small businesses.
                It answers questions from your own knowledge base with
                citations, drafts emails, schedules meetings, and tracks leads
                — and it never takes an external action without a human saying
                yes.
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
                The demo opens a pre-loaded workspace. Gmail and Calendar are
                simulated — no real emails or events are ever created.
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
                A single agent, many skills — each one explainable, traceable,
                and gated where it matters.
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

        {/* Architecture */}
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
                Under the hood
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-600 sm:text-base">
                A layered, production-style architecture: the Next.js frontend
                calls a FastAPI backend, which routes each message through a
                LangGraph agent to tools for retrieval, email, calendar, and
                lead management. External actions pause for human approval
                before any provider executes them, and every step is logged.
              </p>
            </div>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {TECH_STACK.map((tech) => (
                <div
                  key={tech.name}
                  className="rounded-xl border border-slate-200 bg-slate-50/60 p-5"
                >
                  <p className="font-mono text-sm font-semibold text-slate-900">
                    {tech.name}
                  </p>
                  <p className="mt-2 text-xs leading-relaxed text-slate-600">
                    {tech.role}
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-6 text-xs text-slate-500">
              When managed services are unavailable, the platform degrades
              gracefully to deterministic fallbacks — retrieval, embeddings,
              rate limiting, and the demo keep working end to end.
            </p>
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
                  The public demo opens a shared workspace pre-loaded with a
                  knowledge base, leads, and pending approvals. Everything you
                  trigger is simulated: no real emails are sent, no real
                  calendar events are created, and no credentials are
                  required.
                </p>
                <ul className="mt-6 space-y-2.5">
                  {[
                    "Ask the agent about company policies and get cited answers",
                    "Draft a customer email and watch it stop at the approval gate",
                    "Check calendar availability with the simulated provider",
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

/**
 * Static product vignette: a chat exchange stopping at the approval gate.
 * Pure markup — communicates the core interaction without screenshots.
 */
function HeroPreview() {
  return (
    <div aria-hidden="true" className="relative hidden lg:block">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xl shadow-indigo-500/5">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 text-xs font-bold text-white">
            O
          </span>
          <p className="text-xs font-semibold text-slate-900">AI Workspace</p>
          <span className="ml-auto rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
            Demo mode — simulated
          </span>
        </div>

        <div className="space-y-3 pt-4">
          <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-2.5 text-xs text-white">
            Draft a follow-up email to Northwind about the renewal quote.
          </div>
          <div className="w-fit max-w-[90%] rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-2.5 text-xs text-slate-700">
            Here&apos;s a draft based on your pricing docs and the last
            conversation. Ready to send when you are.
          </div>
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-amber-600" />
              <p className="text-xs font-semibold text-amber-800">
                Approval required
              </p>
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-amber-700">
              send_email · to: sales@northwind.example — waiting for an owner
              or admin to approve.
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
            <ScrollText className="h-3.5 w-3.5" />
            Audit log: email.draft created · approval pending · nothing sent
          </div>
        </div>
      </div>
    </div>
  );
}
