import { vi } from "vitest";

interface MockResponse {
  status?: number;
  body?: unknown;
}

interface RouteMatch {
  method?: string;
  url: string | RegExp;
  response: MockResponse | ((req: { method: string; body: unknown }) => MockResponse);
}

/**
 * Install a fetch mock that matches requests by method + URL substring/regex.
 * Returns a cleanup function.
 */
export function installFetchMock(routes: RouteMatch[]): () => void {
  const original = globalThis.fetch;
  globalThis.fetch = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
    const urlStr =
      typeof url === "string"
        ? url
        : url instanceof URL
          ? url.toString()
          : url.url;
    const method = (init?.method ?? "GET").toUpperCase();
    const match = routes.find((r) => {
      if (r.method && r.method.toUpperCase() !== method) return false;
      if (r.url instanceof RegExp) return r.url.test(urlStr);
      return urlStr.includes(r.url);
    });

    if (!match) {
      return new Response(
        JSON.stringify({ error: "not_found", message: `No mock for ${method} ${urlStr}` }),
        { status: 404, headers: { "Content-Type": "application/json" } },
      );
    }

    let body: unknown = undefined;
    try {
      body = init?.body ? JSON.parse(init.body as string) : undefined;
    } catch {
      body = init?.body;
    }

    const resolved =
      typeof match.response === "function"
        ? match.response({ method, body })
        : match.response;

    const status = resolved.status ?? 200;
    const payload =
      resolved.body === undefined
        ? null
        : typeof resolved.body === "string"
          ? resolved.body
          : JSON.stringify(resolved.body);

    return new Response(payload, {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }) as typeof fetch;

  return () => {
    globalThis.fetch = original;
  };
}
