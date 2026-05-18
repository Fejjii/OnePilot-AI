import type { ApiError } from "@/types/api";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_STORAGE_KEY = "onepilot_token";

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly error: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

type Json = unknown;

interface FetchOptions extends Omit<RequestInit, "body"> {
  body?: Json;
  auth?: boolean;
  query?: Record<string, string | number | boolean | undefined | null>;
}

function buildUrl(
  path: string,
  query?: FetchOptions["query"],
): string {
  if (!query) return `${BASE_URL}${path}`;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    params.append(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${BASE_URL}${path}?${qs}` : `${BASE_URL}${path}`;
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

async function parseErrorPayload(res: Response): Promise<ApiError> {
  try {
    return (await res.json()) as ApiError;
  } catch {
    return {
      error: "unknown_error",
      message: res.statusText || "An unexpected error occurred",
    };
  }
}

async function rawFetch<T>(
  path: string,
  init: RequestInit & { auth?: boolean; query?: FetchOptions["query"] },
): Promise<T> {
  const { auth = true, query, headers: extraHeaders, ...rest } = init;
  const headers = new Headers(extraHeaders);

  if (auth) {
    const token = getStoredToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const url = buildUrl(path, query);
  const res = await fetch(url, { ...rest, headers });

  if (!res.ok) {
    const payload = await parseErrorPayload(res);
    throw new ApiRequestError(res.status, payload.error, payload.message);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}

export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const { body, auth, query, headers, ...rest } = options;
  const finalHeaders = new Headers(headers as HeadersInit | undefined);

  if (body !== undefined && !finalHeaders.has("Content-Type")) {
    finalHeaders.set("Content-Type", "application/json");
  }

  return rawFetch<T>(path, {
    ...rest,
    auth,
    query,
    headers: finalHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export interface RequestOptions {
  query?: FetchOptions["query"];
  signal?: AbortSignal;
}

export const api = {
  get<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    return apiFetch<T>(path, { method: "GET", ...opts });
  },
  post<T>(
    path: string,
    body?: Json,
    opts: RequestOptions = {},
  ): Promise<T> {
    return apiFetch<T>(path, { method: "POST", body, ...opts });
  },
  patch<T>(
    path: string,
    body?: Json,
    opts: RequestOptions = {},
  ): Promise<T> {
    return apiFetch<T>(path, { method: "PATCH", body, ...opts });
  },
  delete<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    return apiFetch<T>(path, { method: "DELETE", ...opts });
  },
  upload<T>(
    path: string,
    form: FormData,
    opts: RequestOptions = {},
  ): Promise<T> {
    // FormData manages its own Content-Type with boundary; do not set headers.
    return rawFetch<T>(path, {
      method: "POST",
      body: form,
      auth: true,
      query: opts.query,
      signal: opts.signal,
    });
  },
};

export function getApiBaseUrl(): string {
  return BASE_URL;
}

export const TOKEN_KEY = TOKEN_STORAGE_KEY;
