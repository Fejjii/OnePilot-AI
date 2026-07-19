"use client";

import { useEffect } from "react";

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Root-level error boundary (replaces the root layout when it fails).
 * Uses self-contained markup because the root layout is not available.
 */
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    console.error("[onepilot] global UI error", error.digest ?? error.name);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#f8fafc",
          fontFamily:
            'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
          color: "#0f172a",
          padding: 24,
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: 420,
            borderRadius: 16,
            border: "1px solid #fecdd3",
            background: "#ffffff",
            padding: 32,
            textAlign: "center",
            boxShadow: "0 1px 2px rgba(15,23,42,0.04)",
          }}
        >
          <h1 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
            Something went wrong
          </h1>
          <p
            style={{
              margin: "12px 0 0",
              fontSize: 14,
              lineHeight: 1.5,
              color: "#475569",
            }}
          >
            OnePilot could not load this page. Please try again.
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              marginTop: 24,
              borderRadius: 8,
              border: "none",
              background: "#4f46e5",
              color: "#ffffff",
              fontSize: 14,
              fontWeight: 500,
              padding: "10px 16px",
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
