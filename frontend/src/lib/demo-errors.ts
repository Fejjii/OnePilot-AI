import { ApiRequestError } from "@/lib/api-client";

/**
 * Map failures from `POST /demo/start` to friendly, actionable copy.
 * Shared by every "Try the demo" entry point (landing page, login page).
 */
export function demoErrorMessage(err: unknown): string {
  if (err instanceof ApiRequestError) {
    if (err.status === 403) {
      return "The public demo is not enabled on this server.";
    }
    if (err.status === 429) {
      return "Too many demo sessions were started recently. Please try again in a few minutes.";
    }
    if (err.status === 503) {
      return "The demo workspace could not be prepared. Please try again shortly.";
    }
    return err.message;
  }
  return "Could not start the demo. Please try again.";
}
