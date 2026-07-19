"use client";

import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDemoEntry } from "@/lib/use-demo-entry";
import { cn } from "@/lib/utils";

interface TryDemoButtonProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

/**
 * One-click entry into the public demo. Errors (demo disabled, rate limit,
 * seeding failure) render inline below the button so every CTA placement
 * degrades gracefully.
 */
export function TryDemoButton({
  size = "md",
  className,
  label = "Try the demo",
}: TryDemoButtonProps) {
  const { startDemo, isStarting, error } = useDemoEntry();

  return (
    <div className={cn("flex flex-col", className)}>
      <Button
        type="button"
        size={size}
        loading={isStarting}
        onClick={startDemo}
        leftIcon={<Sparkles className="h-4 w-4" aria-hidden="true" />}
      >
        {isStarting ? "Preparing your demo…" : label}
      </Button>
      {error && (
        <p
          role="alert"
          className="mt-2 rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700"
        >
          {error}
        </p>
      )}
    </div>
  );
}
