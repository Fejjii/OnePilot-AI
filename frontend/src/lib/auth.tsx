"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiRequestError, TOKEN_KEY } from "@/lib/api-client";
import type { DemoStartResponse, MeResponse, TokenResponse } from "@/types/api";

// TODO: Move token storage to httpOnly cookies set by the backend
// for improved security against XSS attacks.

const DEMO_MODE_KEY = "onepilot_demo_mode";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export function getDemoModeFlag(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(DEMO_MODE_KEY) === "1";
}

function setDemoModeFlag(): void {
  window.localStorage.setItem(DEMO_MODE_KEY, "1");
}

function clearDemoModeFlag(): void {
  window.localStorage.removeItem(DEMO_MODE_KEY);
}

interface RegisterInput {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
}

interface AuthState {
  user: MeResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  /** True while an authenticated one-click demo session is active. */
  isDemo: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterInput) => Promise<void>;
  enterDemo: () => Promise<void>;
  logout: () => void;
  refresh: () => Promise<MeResponse | null>;
}

const AuthContext = createContext<AuthState | null>(null);

async function fetchMe(): Promise<MeResponse | null> {
  const token = getToken();
  if (!token) return null;
  try {
    return await api.get<MeResponse>("/me");
  } catch (err) {
    if (err instanceof ApiRequestError && err.status === 401) {
      // Expired or invalid session (including expired demo sessions):
      // drop the token and the demo flag so the UI degrades gracefully.
      clearToken();
      clearDemoModeFlag();
    }
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [user, setUser] = useState<MeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchMe().then((me) => {
      if (cancelled) return;
      setUser(me);
      setIsDemo(!!me && getDemoModeFlag());
      setIsLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const refresh = useCallback(async () => {
    const me = await fetchMe();
    setUser(me);
    setIsDemo(!!me && getDemoModeFlag());
    return me;
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await api.post<TokenResponse>(
        "/auth/login",
        { email, password },
      );
      setToken(data.access_token);
      clearDemoModeFlag();
      const me = await fetchMe();
      setUser(me);
      setIsDemo(false);
      queryClient.clear();
      router.push("/dashboard");
    },
    [queryClient, router],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      const data = await api.post<TokenResponse>("/auth/register", input);
      setToken(data.access_token);
      clearDemoModeFlag();
      const me = await fetchMe();
      setUser(me);
      setIsDemo(false);
      queryClient.clear();
      router.push("/dashboard");
    },
    [queryClient, router],
  );

  const enterDemo = useCallback(async () => {
    const data = await api.post<DemoStartResponse>("/demo/start");
    setToken(data.access_token);
    setDemoModeFlag();
    const me = await fetchMe();
    setUser(me);
    setIsDemo(!!me);
    queryClient.clear();
    router.push("/dashboard");
  }, [queryClient, router]);

  const logout = useCallback(() => {
    clearToken();
    clearDemoModeFlag();
    setUser(null);
    setIsDemo(false);
    queryClient.clear();
    router.push("/login");
  }, [queryClient, router]);

  const value = useMemo<AuthState>(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      isDemo,
      login,
      register,
      enterDemo,
      logout,
      refresh,
    }),
    [user, isLoading, isDemo, login, register, enterDemo, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

export function isAdminRole(role: string | undefined): boolean {
  return role === "owner" || role === "admin";
}
