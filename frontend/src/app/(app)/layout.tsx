"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  Users,
  ShieldCheck,
  Database,
  BarChart3,
  ClipboardCheck,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  CircleDashed,
} from "lucide-react";
import { useAuth, isAdminRole } from "@/lib/auth";
import { useHealth, useApprovals } from "@/lib/queries";
import { PlanBadge } from "@/components/domain/plan-badge";
import { DemoModeBanner } from "@/components/domain/demo-mode-banner";
import { cn, initialsFromName } from "@/lib/utils";

type NavItem = {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  badge?: "pending";
};

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "AI Workspace", href: "/workspace", icon: MessageSquare },
  { label: "Knowledge Base", href: "/knowledge", icon: BookOpen },
  { label: "Leads", href: "/leads", icon: Users },
  { label: "Approvals", href: "/approvals", icon: ShieldCheck, badge: "pending" },
  { label: "Memory", href: "/memory", icon: Database },
  { label: "Usage & Admin", href: "/usage", icon: BarChart3 },
  { label: "Evaluation", href: "/evaluation", icon: ClipboardCheck },
  { label: "Settings", href: "/settings", icon: Settings },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated || !user) return null;

  const initials = initialsFromName(user.user.full_name);

  return (
    <div className="flex h-full">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-slate-950 transition-transform duration-200 lg:static lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center gap-3 border-b border-white/5 px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 text-sm font-bold text-white">
            O
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">
              {user.organization.name}
            </p>
            <p className="truncate text-[11px] text-slate-400">OnePilot AI</p>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="ml-auto text-slate-400 hover:text-white lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-4 pt-3">
          <PlanBadge plan={user.plan} />
        </div>

        <nav className="mt-2 flex-1 space-y-0.5 overflow-y-auto px-3 py-2 thin-scrollbar">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-white/10 text-white"
                    : "text-slate-400 hover:bg-white/5 hover:text-white",
                )}
              >
                <item.icon className="h-[18px] w-[18px] shrink-0" />
                <span className="flex-1">{item.label}</span>
                {item.badge === "pending" && <PendingApprovalsDot />}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-white/5 p-3">
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            <LogOut className="h-[18px] w-[18px]" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <DemoModeBanner />
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-slate-500 hover:text-slate-900 lg:hidden"
              aria-label="Open sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>
            <ProviderStatusIndicator />
          </div>

          <div className="relative flex items-center gap-3">
            <button
              type="button"
              onClick={() => setUserMenuOpen((v) => !v)}
              className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-2 py-1 text-left hover:bg-slate-50"
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 text-[11px] font-semibold text-white">
                {initials}
              </div>
              <div className="hidden text-right sm:block">
                <p className="text-xs font-medium text-slate-900 leading-tight">
                  {user.user.full_name}
                </p>
                <p className="text-[10px] capitalize text-slate-500">
                  {user.role}
                </p>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            </button>
            {userMenuOpen && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setUserMenuOpen(false)}
                />
                <div className="absolute right-0 top-full z-20 mt-2 w-56 rounded-lg border border-slate-200 bg-white p-1 shadow-lg">
                  <div className="border-b border-slate-100 px-3 py-2">
                    <p className="truncate text-xs font-medium text-slate-900">
                      {user.user.full_name}
                    </p>
                    <p className="truncate text-[11px] text-slate-500">
                      {user.user.email}
                    </p>
                  </div>
                  <Link
                    href="/settings"
                    className="block rounded-md px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    Settings
                  </Link>
                  {isAdminRole(user.role) && (
                    <Link
                      href="/usage"
                      className="block rounded-md px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      Admin audit
                    </Link>
                  )}
                  <button
                    onClick={logout}
                    className="mt-1 block w-full rounded-md border-t border-slate-100 px-3 py-1.5 text-left text-xs text-rose-600 hover:bg-rose-50"
                  >
                    Sign out
                  </button>
                </div>
              </>
            )}
          </div>
        </header>

        <main className="flex-1 overflow-y-auto bg-slate-50 px-4 py-6 lg:px-8 lg:py-8 thin-scrollbar">
          {children}
        </main>
      </div>
    </div>
  );
}

function PendingApprovalsDot() {
  const { data } = useApprovals({ status: "pending", limit: 1 });
  const pending = data?.pending_count ?? 0;
  if (pending === 0) return null;
  return (
    <span className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold text-white">
      {pending}
    </span>
  );
}

function ProviderStatusIndicator() {
  const { data, isLoading } = useHealth();
  if (isLoading) {
    return (
      <div className="hidden items-center gap-1.5 text-xs text-slate-500 sm:flex">
        <CircleDashed className="h-3.5 w-3.5 animate-spin" />
        Checking providers…
      </div>
    );
  }
  if (!data) return null;
  const providers = data.providers;
  const allOk = providers.database;
  const hasOpenAI = providers.openai;
  const Icon = allOk ? CheckCircle2 : AlertTriangle;
  const color = allOk ? "text-emerald-600" : "text-amber-600";
  const mode = hasOpenAI ? "Live providers" : "Deterministic fallback";
  return (
    <div className="hidden items-center gap-2 sm:flex">
      <Icon className={cn("h-4 w-4", color)} />
      <div className="text-xs">
        <p className="font-medium text-slate-900">{mode}</p>
        <p className="text-[10px] text-slate-500">
          env: {data.env} · v{data.version}
        </p>
      </div>
    </div>
  );
}
