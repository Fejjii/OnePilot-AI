import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    css: false,
    include: ["src/**/*.test.{ts,tsx}"],
    // Single-thread mode for reliability on Windows and resource-constrained environments
    pool: "vmThreads",
    singleThread: true,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Next.js must not type-check Vitest-only options during production builds.
  } as any,
});
