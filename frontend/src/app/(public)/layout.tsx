import Link from "next/link";
import {
  BookOpen,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="grid min-h-full lg:grid-cols-2">
      {/* Marketing pane */}
      <div className="relative hidden flex-col justify-between bg-slate-950 px-12 py-12 text-white lg:flex">
        <Link href="/" className="flex w-fit items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 text-lg font-bold">
            O
          </div>
          <div>
            <p className="text-sm font-semibold">OnePilot AI</p>
            <p className="text-[11px] text-slate-400">
              AI operations for small businesses
            </p>
          </div>
        </Link>

        <div className="max-w-md">
          <h2 className="text-3xl font-semibold leading-tight">
            One workspace.
            <br />
            One co-pilot for every operation.
          </h2>
          <p className="mt-4 text-sm text-slate-300">
            Ground answers in your knowledge base, capture leads, draft emails,
            and gate risky actions through human approval. With full traceability.
          </p>

          <ul className="mt-8 space-y-3 text-sm text-slate-200">
            <li className="flex items-start gap-2">
              <BookOpen className="mt-0.5 h-4 w-4 text-indigo-300" />
              Grounded answers with citations
            </li>
            <li className="flex items-start gap-2">
              <ShieldCheck className="mt-0.5 h-4 w-4 text-indigo-300" />
              Human-in-the-loop approvals for risky actions
            </li>
            <li className="flex items-start gap-2">
              <Sparkles className="mt-0.5 h-4 w-4 text-indigo-300" />
              Multi-intent agent with deterministic fallbacks
            </li>
          </ul>
        </div>

        <p className="text-[11px] text-slate-500">
          © {new Date().getFullYear()} OnePilot AI. Public demo actions are
          simulated.
        </p>
      </div>

      {/* Form pane */}
      <div className="flex items-center justify-center bg-slate-50 px-4 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center lg:hidden">
            <Link href="/" className="inline-block">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 text-white font-bold text-xl">
                O
              </div>
              <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
                OnePilot AI
              </h1>
            </Link>
            <p className="mt-1 text-sm text-slate-500">
              AI operations for small businesses
            </p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
