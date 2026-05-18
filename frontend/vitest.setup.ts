import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});

// Default API URL for tests; individual tests can override fetch behaviour.
if (typeof process !== "undefined") {
  process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";
}
