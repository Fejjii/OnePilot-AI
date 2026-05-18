import { vi } from "vitest";
import type { AnchorHTMLAttributes } from "react";

let pathname = "/dashboard";
let searchParams = new URLSearchParams();

export function setMockNextLocation(opts: {
  pathname?: string;
  search?: string;
}) {
  if (opts.pathname !== undefined) pathname = opts.pathname;
  if (opts.search !== undefined) searchParams = new URLSearchParams(opts.search);
}

export const navigationMocks = {
  push: vi.fn(),
  replace: vi.fn(),
  prefetch: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
};

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
