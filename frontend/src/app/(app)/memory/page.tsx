"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { Database, Plus, Trash2, Loader2, Eraser } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";
import { Modal } from "@/components/ui/modal";
import { Input, Label, Select, Textarea, FieldError } from "@/components/ui/input";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import {
  useMemoryClearMutation,
  useMemoryDeleteMutation,
  useMemoryList,
  useMemoryPreferenceMutation,
  useMemoryStatus,
  useMemoryWriteMutation,
} from "@/lib/queries";
import { ApiRequestError } from "@/lib/api-client";
import { formatRelativeTime, titleize } from "@/lib/utils";

const SCOPE_OPTIONS = ["user", "organization", "agent"] as const;

const SCOPE_TONES: Record<(typeof SCOPE_OPTIONS)[number], BadgeTone> = {
  user: "primary",
  organization: "info",
  agent: "success",
};

const memorySchema = z.object({
  scope: z.enum(SCOPE_OPTIONS),
  key: z
    .string()
    .min(1, "Key is required")
    .max(255, "Max 255 chars"),
  value: z.string().min(1, "Value is required"),
  ttl_seconds: z
    .string()
    .optional()
    .refine(
      (v) => !v || (Number.isFinite(Number(v)) && Number(v) > 0),
      "Must be a positive number",
    ),
});

type MemoryForm = z.infer<typeof memorySchema>;

export default function MemoryPage() {
  const [scopeFilter, setScopeFilter] = useState<string>("");
  const [createOpen, setCreateOpen] = useState(false);
  const memory = useMemoryList(scopeFilter || undefined);
  const status = useMemoryStatus();
  const remove = useMemoryDeleteMutation();
  const clearAll = useMemoryClearMutation();
  const preference = useMemoryPreferenceMutation();
  const items = memory.data?.items ?? [];
  const agentEnabled = status.data?.agent_memory_enabled ?? true;
  const sharedDemo = status.data?.shared_demo_tenant ?? false;
  const userDisabled = status.data?.user_disabled ?? false;

  async function onDelete(scope: string, key: string) {
    if (!window.confirm(`Delete memory "${key}"?`)) return;
    try {
      await remove.mutateAsync({ scope, key });
      toast.success("Memory deleted");
    } catch (err) {
      const msg =
        err instanceof ApiRequestError ? err.message : "Delete failed";
      toast.error("Failed to delete", { description: msg });
    }
  }

  async function onClearAll() {
    if (
      !window.confirm(
        "Clear all of your user and agent memories? This cannot be undone.",
      )
    ) {
      return;
    }
    try {
      const result = await clearAll.mutateAsync();
      toast.success("Memory cleared", {
        description: `${result.deleted_count} item(s) removed`,
      });
    } catch (err) {
      const msg =
        err instanceof ApiRequestError ? err.message : "Clear failed";
      toast.error("Failed to clear memory", { description: msg });
    }
  }

  async function onToggleDisabled() {
    try {
      const next = !userDisabled;
      await preference.mutateAsync(next);
      toast.success(next ? "Agent memory disabled" : "Agent memory enabled");
    } catch (err) {
      const msg =
        err instanceof ApiRequestError ? err.message : "Update failed";
      toast.error("Could not update preference", { description: msg });
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Memory"
        description="Durable facts the agent may recall across conversations. Secrets are rejected. Clear or disable anytime."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              leftIcon={<Eraser className="h-4 w-4" />}
              onClick={() => void onClearAll()}
              loading={clearAll.isPending}
              disabled={items.length === 0}
            >
              Clear my memory
            </Button>
            <Button
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => setCreateOpen(true)}
            >
              Write memory
            </Button>
          </div>
        }
      />

      {status.data && (
        <div
          role="status"
          className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
        >
          {sharedDemo ? (
            <p>
              Public demo uses a shared workspace. Agent memory recall and
              auto-save are disabled so visitors cannot see each other&apos;s
              notes. Manual entries are cleared when a new demo session starts.
            </p>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p>
                Agent memory is{" "}
                <span className="font-semibold">
                  {agentEnabled ? "enabled" : "disabled"}
                </span>
                {userDisabled ? " by your preference" : ""}.
                {" "}
                {status.data.item_count} visible item
                {status.data.item_count === 1 ? "" : "s"}.
              </p>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => void onToggleDisabled()}
                loading={preference.isPending}
                aria-pressed={userDisabled}
              >
                {userDisabled ? "Enable agent memory" : "Disable agent memory"}
              </Button>
            </div>
          )}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Entries</CardTitle>
          <Select
            value={scopeFilter}
            onChange={(e) => setScopeFilter(e.target.value)}
            className="h-8 text-xs"
          >
            <option value="">All scopes</option>
            {SCOPE_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {titleize(s)}
              </option>
            ))}
          </Select>
        </CardHeader>
        <CardContent>
          {memory.isError ? (
            <ErrorState onRetry={() => memory.refetch()} />
          ) : memory.isLoading ? (
            <LoadingSkeleton lines={5} />
          ) : items.length === 0 ? (
            <EmptyState
              icon={Database}
              title="No memory yet"
              description="Persist context the agent should remember across conversations: preferences, confirmed facts, and recurring goals."
            />
          ) : (
            <ul className="divide-y divide-slate-100">
              {items.map((item) => {
                const tone =
                  SCOPE_TONES[item.scope as keyof typeof SCOPE_TONES] ??
                  "neutral";
                const isDeleting =
                  remove.isPending &&
                  remove.variables?.key === item.key &&
                  remove.variables?.scope === item.scope;
                return (
                  <li
                    key={item.id}
                    className="flex items-start justify-between gap-4 py-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={tone}>{titleize(item.scope)}</Badge>
                        <p className="font-mono text-xs font-semibold text-slate-900">
                          {item.key}
                        </p>
                        {item.expires_at && (
                          <span className="text-[10px] text-amber-700">
                            expires {formatRelativeTime(item.expires_at)}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 line-clamp-3 whitespace-pre-wrap text-xs text-slate-600">
                        {item.value}
                      </p>
                      <p className="mt-1 text-[10px] text-slate-400">
                        Updated {formatRelativeTime(item.updated_at)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => onDelete(item.scope, item.key)}
                      className="min-h-[44px] min-w-[44px] rounded-md p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                      aria-label={`Delete memory ${item.key}`}
                      disabled={isDeleting}
                    >
                      {isDeleting ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      <CreateMemoryModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}

interface CreateMemoryModalProps {
  open: boolean;
  onClose: () => void;
}

function CreateMemoryModal({ open, onClose }: CreateMemoryModalProps) {
  const create = useMemoryWriteMutation();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<MemoryForm>({
    resolver: zodResolver(memorySchema),
    defaultValues: {
      scope: "user",
      key: "",
      value: "",
      ttl_seconds: "",
    },
  });

  async function onSubmit(data: MemoryForm) {
    const ttl =
      data.ttl_seconds && data.ttl_seconds.trim() !== ""
        ? Number(data.ttl_seconds)
        : null;
    try {
      await create.mutateAsync({
        scope: data.scope,
        key: data.key,
        value: data.value,
        ttl_seconds: ttl,
      });
      toast.success("Memory saved");
      reset();
      onClose();
    } catch (err) {
      const msg =
        err instanceof ApiRequestError ? err.message : "Could not save memory";
      toast.error("Failed to save", { description: msg });
    }
  }

  return (
    <Modal
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title="Write memory"
      description="Stored under the current organization and user. Secrets are rejected. TTL is optional."
      footer={
        <>
          <Button
            variant="outline"
            onClick={() => {
              reset();
              onClose();
            }}
          >
            Cancel
          </Button>
          <Button type="submit" form="memory-form" loading={isSubmitting}>
            Save
          </Button>
        </>
      }
    >
      <form id="memory-form" className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
        <div>
          <Label htmlFor="scope">Scope</Label>
          <Select id="scope" {...register("scope")}>
            {SCOPE_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {titleize(s)}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="key">Key</Label>
          <Input
            id="key"
            placeholder="preferred_tone, timezone…"
            {...register("key")}
          />
          <FieldError message={errors.key?.message} />
        </div>
        <div>
          <Label htmlFor="value">Value</Label>
          <Textarea id="value" rows={4} {...register("value")} />
          <FieldError message={errors.value?.message} />
        </div>
        <div>
          <Label htmlFor="ttl_seconds">TTL (seconds, optional)</Label>
          <Input
            id="ttl_seconds"
            type="number"
            min={1}
            placeholder="e.g. 86400"
            {...register("ttl_seconds")}
          />
          <FieldError message={errors.ttl_seconds?.message} />
        </div>
      </form>
    </Modal>
  );
}
