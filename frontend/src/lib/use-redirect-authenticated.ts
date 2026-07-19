"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

/**
 * Bounce already-authenticated users away from public auth pages
 * (`/login`, `/register`) to the dashboard. Returns true while auth is
 * still resolving or a redirect is in flight so callers can avoid flashing
 * the sign-in form.
 */
export function useRedirectAuthenticated(
  destination = "/dashboard",
): { pending: boolean } {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace(destination);
    }
  }, [isLoading, isAuthenticated, router, destination]);

  return { pending: isLoading || isAuthenticated };
}
