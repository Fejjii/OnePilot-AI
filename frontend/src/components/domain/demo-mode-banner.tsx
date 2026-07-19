"use client";

import { FlaskConical } from "lucide-react";
import { useAuth } from "@/lib/auth";

/**
 * Visible whenever an authenticated one-click demo session is active.
 * Makes clear that external actions (Gmail, Calendar) are simulated.
 */
export function DemoModeBanner() {
  const { isDemo, isAuthenticated } = useAuth();
  if (!isDemo || !isAuthenticated) return null;
  return (
    <div
      role="status"
      className="flex items-center justify-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-1.5 text-xs text-amber-800"
    >
      <FlaskConical className="h-3.5 w-3.5 shrink-0" />
      <span>
        <span className="font-semibold">Demo mode</span> — shared sample
        workspace. Gmail and Calendar are simulated; no real emails or events
        are ever sent.
      </span>
    </div>
  );
}
