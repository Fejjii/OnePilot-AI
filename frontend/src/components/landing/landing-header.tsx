"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { TryDemoButton } from "@/components/landing/try-demo-button";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { label: "Capabilities", href: "#capabilities" },
  { label: "Safety", href: "#safety" },
  { label: "Architecture", href: "#architecture" },
];

/**
 * Sticky public navigation. Shows "Sign in" for visitors and
 * "Open dashboard" once an authenticated session exists.
 */
export function LandingHeader() {
  const { isAuthenticated, isLoading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const accountAction = isLoading ? null : isAuthenticated ? (
    <Link
      href="/dashboard"
      className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900"
    >
      Open dashboard
    </Link>
  ) : (
    <Link
      href="/login"
      className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900"
    >
      Sign in
    </Link>
  );

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 text-base font-bold text-white">
            O
          </span>
          <span className="text-sm font-semibold tracking-tight text-slate-900">
            OnePilot AI
          </span>
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          {accountAction}
          <TryDemoButton size="md" />
        </div>

        <button
          type="button"
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900 md:hidden"
          aria-expanded={menuOpen}
          aria-controls="landing-mobile-menu"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? (
            <X className="h-5 w-5" aria-hidden="true" />
          ) : (
            <Menu className="h-5 w-5" aria-hidden="true" />
          )}
        </button>
      </div>

      <div
        id="landing-mobile-menu"
        className={cn(
          "border-t border-slate-200 bg-white px-4 pb-4 pt-2 md:hidden",
          menuOpen ? "block" : "hidden",
        )}
      >
        <nav aria-label="Primary mobile" className="flex flex-col gap-1">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              {link.label}
            </a>
          ))}
          {isAuthenticated ? (
            <Link
              href="/dashboard"
              onClick={() => setMenuOpen(false)}
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Open dashboard
            </Link>
          ) : (
            <Link
              href="/login"
              onClick={() => setMenuOpen(false)}
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Sign in
            </Link>
          )}
        </nav>
        <TryDemoButton size="md" className="mt-3 [&>button]:w-full" />
      </div>
    </header>
  );
}
