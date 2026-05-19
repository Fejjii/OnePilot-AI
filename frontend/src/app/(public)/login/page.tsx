"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuth } from "@/lib/auth";
import { ApiRequestError } from "@/lib/api-client";
import { Input, Label, FieldError } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login } = useAuth();
  const [apiError, setApiError] = useState<string | null>(null);

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

      <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <p className="text-xs font-medium text-slate-700">Demo credentials</p>
        <p className="mt-1 font-mono text-[11px] text-slate-600">
          admin@onepilot.ai / Demo1234!
        </p>
        <p className="mt-1.5 text-[10px] text-slate-500">
          Run <span className="font-mono">python scripts/seed_demo.py</span> after
          starting the backend to load 19 NovaEdge docs, leads, approvals, and usage
          sample data.
        </p>
      </div>
    </div>
  );
}
