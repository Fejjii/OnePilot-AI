import { vi } from "vitest";
import type { AnchorHTMLAttributes } from "react";

let pathname = "/workspace";
let searchParams = new URLSearchParams();

export function setMockNextLocation(opts: {
  pathname?: string;
  search?: string;
}) {
  if (opts.pathname !== undefined) pathname = opts.pathname;
  if (opts.search !== undefined) searchParams = new URLSearchParams(opts.search);
}

function syncLocationFromHref(url: string) {
  try {
    const parsed = new URL(url, "http://localhost");
    setMockNextLocation({
      pathname: parsed.pathname,
      search: parsed.search,
    });
  } catch {
    // ignore malformed URLs in tests
  }
}

export const navigationMocks = {
  push: vi.fn(),
  replace: vi.fn((url: string) => {
    syncLocationFromHref(url);
  }),
  prefetch: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
};

/** Restore router.replace to sync URL immediately (default). */
export function enableRouterUrlSync() {
  navigationMocks.replace.mockImplementation((url: string) => {
    syncLocationFromHref(url);
  });
}

/** Simulate Next.js App Router lag: replace is called but searchParams do not update yet. */
export function blockRouterUrlSync() {
  navigationMocks.replace.mockImplementation(() => {});
}

vi.mock("next/navigation", () => ({
  useRouter: () => navigationMocks,
  usePathname: () => pathname,
  useSearchParams: () => searchParams,
  redirect: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
