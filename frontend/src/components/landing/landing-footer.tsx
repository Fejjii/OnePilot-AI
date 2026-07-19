import Link from "next/link";

export function LandingFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-sm">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 text-sm font-bold text-white">
              O
            </span>
            <span className="text-sm font-semibold text-slate-900">
              OnePilot AI
            </span>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-slate-500">
            An AI operations platform with human-in-the-loop safety. Public
            demo actions are simulated — no real emails are sent and no real
            calendar events are created.
          </p>
        </div>

        <nav aria-label="Footer" className="flex gap-12 text-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Product
            </p>
            <ul className="mt-3 space-y-2">
              <li>
                <a href="#capabilities" className="text-slate-600 hover:text-slate-900">
                  Capabilities
                </a>
              </li>
              <li>
                <a href="#safety" className="text-slate-600 hover:text-slate-900">
                  Safety model
                </a>
              </li>
              <li>
                <a href="#architecture" className="text-slate-600 hover:text-slate-900">
                  Architecture
                </a>
              </li>
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Account
            </p>
            <ul className="mt-3 space-y-2">
              <li>
                <Link href="/login" className="text-slate-600 hover:text-slate-900">
                  Sign in
                </Link>
              </li>
              <li>
                <Link href="/register" className="text-slate-600 hover:text-slate-900">
                  Create a workspace
                </Link>
              </li>
            </ul>
          </div>
        </nav>
      </div>
      <div className="border-t border-slate-100">
        <p className="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-400 sm:px-6">
          © {new Date().getFullYear()} OnePilot AI. All demo activity runs
          against simulated integrations.
        </p>
      </div>
    </footer>
  );
}
