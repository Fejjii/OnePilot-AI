"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { ApiRequestError } from "@/lib/api-client";
import { Input, Label, FieldError } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

function demoErrorMessage(err: unknown): string {
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

export default function LoginPage() {
  const { login, enterDemo } = useAuth();
  const [apiError, setApiError] = useState<string | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  async function onSubmit(data: LoginForm) {
    setApiError(null);
    try {
      await login(data.email, data.password);
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setApiError(err.message);
      } else {
        setApiError("Something went wrong. Please try again.");
      }
    }
  }

  async function onTryDemo() {
    setDemoError(null);
    setDemoLoading(true);
    try {
      await enterDemo();
    } catch (err) {
      setDemoError(demoErrorMessage(err));
    } finally {
      setDemoLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">Sign in</h2>
      <p className="mt-1 text-sm text-slate-500">
        Welcome back. Enter your credentials to access your workspace.
      </p>

      {apiError && (
        <div className="mt-4 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {apiError}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            className="mt-1.5"
            {...register("email")}
          />
          <FieldError message={errors.email?.message} />
        </div>

        <div>
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            className="mt-1.5"
            {...register("password")}
          />
          <FieldError message={errors.password?.message} />
        </div>

        <Button type="submit" loading={isSubmitting} className="w-full">
          {isSubmitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Don&apos;t have an account?{" "}
        <Link
          href="/register"
          className="font-medium text-indigo-600 hover:text-indigo-700"
        >
          Create one
        </Link>
      </p>

      <div className="mt-6 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-4">
        <p className="text-xs font-semibold text-indigo-900">
          Just looking around?
        </p>
        <p className="mt-1 text-[11px] leading-relaxed text-indigo-700">
          Explore a pre-loaded workspace with a knowledge base, leads, and
          approvals — no account or credentials needed. Gmail and Calendar are
          simulated; nothing external is ever sent.
        </p>
        {demoError && (
          <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">
            {demoError}
          </div>
        )}
        <Button
          type="button"
          onClick={onTryDemo}
          loading={demoLoading}
          className="mt-3 w-full bg-indigo-600 hover:bg-indigo-700"
        >
          <Sparkles className="mr-2 h-4 w-4" />
          {demoLoading ? "Preparing your demo…" : "Try the demo"}
        </Button>
      </div>
    </div>
  );
}
