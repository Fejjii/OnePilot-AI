import { ShieldAlert } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface ApprovalBannerProps {
  approvalId?: string | null;
}

export function ApprovalBanner({ approvalId }: ApprovalBannerProps) {
  return (
    <div className="flex flex-wrap items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2.5">
      <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-amber-900">
          Approval required
        </p>
        <p className="text-[11px] text-amber-800">
          The agent proposed a sensitive action that needs admin review before it
          can execute.
        </p>
      </div>
      {approvalId && (
        <Link href={`/approvals?focus=${approvalId}`}>
          <Button size="sm" variant="outline" className="border-amber-300">
            Review →
          </Button>
        </Link>
      )}
    </div>
  );
}
