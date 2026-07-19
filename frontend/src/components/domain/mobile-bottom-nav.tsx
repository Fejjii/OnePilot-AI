"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Menu,
  MessageSquare,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useApprovals } from "@/lib/queries";
import { cn } from "@/lib/utils";

export type MobileNavPrimaryHref =
  | "/workspace"
  | "/approvals"
  | "/knowledge"
  | "/leads";

interface MobileBottomNavProps {
  /** Opens the full app drawer (remaining destinations + sign out). */
  onOpenMenu: () => void;
}

const PRIMARY_TABS: ReadonlyArray<{
  href: MobileNavPrimaryHref;
  label: string;
  icon: typeof MessageSquare;
  badge?: "pending";
}> = [
  { href: "/workspace", label: "Chat", icon: MessageSquare },
  { href: "/approvals", label: "Approvals", icon: ShieldCheck, badge: "pending" },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/leads", label: "Leads", icon: Users },
];

/**
 * App-level mobile navigation. Primary destinations stay one tap away; the
 * More control opens the existing full sidebar for secondary routes.
 * Hidden from `lg` and up where the desktop sidebar is always visible.
 */
export function MobileBottomNav({ onOpenMenu }: MobileBottomNavProps) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/90 lg:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      <ul className="grid h-16 grid-cols-5">
        {PRIMARY_TABS.map((tab) => {
          const active =
            pathname === tab.href || pathname.startsWith(`${tab.href}/`);
          return (
            <li key={tab.href} className="min-w-0">
              <Link
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-full min-h-[44px] flex-col items-center justify-center gap-0.5 px-1 text-[10px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-inset",
                  active ? "text-indigo-600" : "text-slate-500 hover:text-slate-800",
                )}
              >
                <span className="relative">
                  <tab.icon className="h-5 w-5" aria-hidden="true" />
                  {tab.badge === "pending" && <PendingApprovalsBadge />}
                </span>
                <span className="truncate">{tab.label}</span>
              </Link>
            </li>
          );
        })}
        <li className="min-w-0">
          <button
            type="button"
            onClick={onOpenMenu}
            className="flex h-full min-h-[44px] w-full flex-col items-center justify-center gap-0.5 px-1 text-[10px] font-medium text-slate-500 hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-inset"
            aria-label="Open navigation menu"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
            <span>More</span>
          </button>
        </li>
      </ul>
    </nav>
  );
}

function PendingApprovalsBadge() {
  const { data } = useApprovals({ status: "pending", limit: 1 });
  const pending = data?.pending_count ?? 0;
  if (pending === 0) return null;
  return (
    <span
      aria-label={`${pending} pending approvals`}
      className="absolute -right-2 -top-1 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-rose-500 px-1 text-[9px] font-semibold text-white"
    >
      {pending > 9 ? "9+" : pending}
    </span>
  );
}
