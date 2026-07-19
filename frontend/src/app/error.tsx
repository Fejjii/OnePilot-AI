"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Segment-level Next.js error boundary. Shows a friendly recovery UI without
 * exposing stack traces or internal error details to the user.
 */
export default function Error({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // Keep diagnostics in the console for developers; never surface them in UI.
    console.error("[onepilot] unhandled UI error", error.digest ?? error.name);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-16">
      <div className="w-full max-w-md rounded-2xl border border-rose-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600">
          <AlertTriangle className="h-6 w-6" aria-hidden="true" />
        </div>
        <h1 className="mt-4 text-lg font-semibold text-slate-900">
          Something went wrong
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          OnePilot hit an unexpected problem loading this page. Your data is
          safe — try again, or return to the dashboard.
        </p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
          <Button type="button" onClick={reset}>
            Try again
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              window.location.href = "/dashboard";
            }}
          >
            Go to dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}
