"use client";

import { useCallback, useState } from "react";
import { useAuth } from "@/lib/auth";
import { demoErrorMessage } from "@/lib/demo-errors";

interface DemoEntryState {
  /** Start a one-click demo session (POST /demo/start + navigate to /dashboard). */
  startDemo: () => Promise<void>;
  isStarting: boolean;
  error: string | null;
}

/**
 * One-click public-demo entry shared by every landing CTA.
 * On success `enterDemo` navigates to /dashboard, so the loading state is
 * intentionally kept active until this page unmounts.
 */
export function useDemoEntry(): DemoEntryState {
  const { enterDemo } = useAuth();
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startDemo = useCallback(async () => {
    setError(null);
    setIsStarting(true);
    try {
      await enterDemo();
    } catch (err) {
      setError(demoErrorMessage(err));
      setIsStarting(false);
    }
  }, [enterDemo]);

  return { startDemo, isStarting, error };
}
