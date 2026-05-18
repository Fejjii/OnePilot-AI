"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  MessageSquare,
  Plus,
  Send,
  ShieldAlert,
  Sparkles,
  BookOpen,
  Wrench,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/loading-skeleton";
import { ChatMessage } from "@/components/domain/chat-message";
import { CitationCard } from "@/components/domain/citation-card";
import { ToolTracePanel } from "@/components/domain/tool-trace-panel";
import { ApprovalBanner } from "@/components/domain/approval-banner";
import { WeakEvidenceWarning } from "@/components/domain/weak-evidence-warning";
import { ConfidenceBadge } from "@/components/domain/confidence-badge";
import { IntentBadge } from "@/components/domain/intent-badge";
import { MicrophoneInput } from "@/components/domain/microphone-input";
import {
  useChatMutation,
  useConversation,
  useConversations,
} from "@/lib/queries";
import { ApiRequestError } from "@/lib/api-client";
import {
  cn,
  formatRelativeTime,
} from "@/lib/utils";
import type {
  ChatResponse,
  Citation,
  ConversationDetailResponse,
  MessageResponse,
  ToolCallTrace,
  TraceStep,
} from "@/types/api";

/** Ephemeral UI state for an in-flight POST /chat tied to one conversation target. */
interface InFlightSend {
  /** Conversation id being continued, or null when starting a new conversation. */
  conversationId: string | null;
  pendingUser: {
    content: string;
    createdAt: string;
  };
  response: ChatResponse | null;
}

export default function WorkspacePage() {
  return (
    <Suspense fallback={<WorkspaceSkeleton />}>
      <WorkspaceInner />
    </Suspense>
  );
}

function WorkspaceInner() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const urlConversationId = searchParams.get("conversation");
  const [navigationOverride, setNavigationOverride] =
    useState<string | null | undefined>(undefined);

  // Apply navigation immediately while URL (useSearchParams) lags behind router.replace.
  const activeConversationId =
    navigationOverride !== undefined &&
    navigationOverride !== urlConversationId
      ? navigationOverride
      : urlConversationId;

  const conversations = useConversations();
  const conversationDetail = useConversation(activeConversationId);
  const chat = useChatMutation();

  const [inFlight, setInFlight] = useState<InFlightSend | null>(null);
  const [viewEpoch, setViewEpoch] = useState(0);

  const activeConversation = useMemo<ConversationDetailResponse | null>(() => {
    if (!activeConversationId) return null;
    if (conversationDetail.data?.id !== activeConversationId) return null;
    return conversationDetail.data;
  }, [activeConversationId, conversationDetail.data]);

  const persistedMessages = useMemo<MessageResponse[]>(
    () => activeConversation?.messages ?? [],
    [activeConversation],
  );

  const inFlightAppliesToView = useMemo(() => {
    if (!inFlight) return false;
    if (inFlight.conversationId === activeConversationId) return true;
    if (
      activeConversationId &&
      inFlight.response?.conversation_id === activeConversationId
    ) {
      return true;
    }
    return false;
  }, [inFlight, activeConversationId]);

  const messages = useMemo<MessageResponse[]>(() => {
    const base = persistedMessages;
    if (!inFlight || !inFlightAppliesToView) return base;

    const additions: MessageResponse[] = [];

    const lastUser = [...base].reverse().find((m) => m.role === "user");
    if (!lastUser || lastUser.content !== inFlight.pendingUser.content) {
      additions.push({
        id: "pending-user",
        role: "user",
        content: inFlight.pendingUser.content,
        intent: null,
        confidence: 0,
        citations: [],
        tool_calls: [],
        created_at: inFlight.pendingUser.createdAt,
      });
    }

    const response = inFlight.response;
    if (
      response?.final_response &&
      !base.find((m) => m.id === response.message_id)
    ) {
      additions.push({
        id: response.message_id,
        role: "assistant",
        content: response.final_response,
        intent: response.intent,
        confidence: response.confidence,
        citations: response.citations,
        tool_calls: response.tool_calls,
        created_at: new Date().toISOString(),
        trace_mode: response.trace_mode,
        trace_id: response.trace_id,
        trace_url: response.trace_url,
        span_count: response.span_count,
      });
    }

    return [...base, ...additions];
  }, [persistedMessages, inFlight, inFlightAppliesToView]);

  const panelData = useMemo<PanelData | null>(() => {
    const lastAssistant = [...messages]
      .reverse()
      .find((m) => m.role === "assistant");
    if (!lastAssistant) return null;

    const liveResponse =
      inFlightAppliesToView &&
      inFlight?.response &&
      inFlight.response.message_id === lastAssistant.id &&
      inFlight.response.conversation_id === activeConversationId
        ? inFlight.response
        : null;

    if (liveResponse) {
      return panelDataFromChatResponse(liveResponse);
    }

    if (
      activeConversationId &&
      activeConversation?.id !== activeConversationId
    ) {
      return null;
    }

    return panelDataFromMessage(lastAssistant);
  }, [
    messages,
    inFlight,
    inFlightAppliesToView,
    activeConversationId,
    activeConversation?.id,
  ]);

  const panelSourceConversationId = useMemo(() => {
    if (inFlightAppliesToView && inFlight?.response) {
      return inFlight.response.conversation_id;
    }
    return activeConversationId;
  }, [inFlightAppliesToView, inFlight, activeConversationId]);

  const approvalRequired =
    inFlightAppliesToView && (inFlight?.response?.approval_required ?? false);
  const approvalId =
    inFlightAppliesToView && inFlight?.response
      ? (inFlight.response.approval_id ?? null)
      : null;

  useEffect(() => {
    if (!inFlight?.response || !activeConversationId) return;
    if (activeConversation?.id !== activeConversationId) return;
    const persisted = activeConversation.messages.some(
      (m) => m.id === inFlight.response?.message_id,
    );
    if (!persisted) return;
    const id = window.setTimeout(() => setInFlight(null), 0);
    return () => window.clearTimeout(id);
  }, [activeConversation, inFlight, activeConversationId]);

  useWorkspaceDevDiagnostics(
    urlConversationId,
    navigationOverride,
    activeConversationId,
    conversationDetail.data?.id ?? null,
    activeConversation?.id ?? null,
    panelSourceConversationId,
    inFlight?.conversationId ?? null,
    inFlight?.response?.conversation_id ?? null,
    inFlightAppliesToView,
    messages.length,
    viewEpoch,
  );

  function navigateToConversation(
    id: string | null,
    opts?: { keepInFlight?: boolean },
  ) {
    if (process.env.NODE_ENV === "development") {
      console.debug("[workspace] navigateToConversation", {
        id,
        keepInFlight: opts?.keepInFlight ?? false,
        from: activeConversationId,
      });
    }

    if (!opts?.keepInFlight) {
      setInFlight(null);
      chat.reset();
    }

    setNavigationOverride(id);
    setViewEpoch((e) => e + 1);

    void queryClient.cancelQueries({ queryKey: ["conversation"] });

    const params = new URLSearchParams(searchParams.toString());
    if (id) params.set("conversation", id);
    else params.delete("conversation");
    const qs = params.toString();
    const href = qs ? `${pathname}?${qs}` : pathname;
    router.replace(href, { scroll: false });
  }

  async function handleSend(message: string) {
    const trimmed = message.trim();
    if (!trimmed) return;

    const sendTargetId = activeConversationId;
    setInFlight({
      conversationId: sendTargetId,
      pendingUser: {
        content: trimmed,
        createdAt: new Date().toISOString(),
      },
      response: null,
    });

    try {
      const response = await chat.mutateAsync({
        message: trimmed,
        conversation_id: sendTargetId ?? undefined,
      });
      setInFlight((prev) => {
        if (!prev || prev.conversationId !== sendTargetId) return null;
        return { ...prev, response };
      });
      if (!sendTargetId) {
        navigateToConversation(response.conversation_id, {
          keepInFlight: true,
        });
      }
      if (response.approval_required) {
        toast.info("Approval requested", {
          description: "An admin must approve before this action executes.",
        });
      }
    } catch (err) {
      const msg =
        err instanceof ApiRequestError ? err.message : "Failed to send message";
      toast.error("Could not send message", { description: msg });
      setInFlight(null);
    }
  }

  const viewKey = activeConversationId ?? "new";

  return (
    <div className="flex flex-col gap-4 lg:h-[calc(100vh-7rem)]">
      <PageHeader
        title="AI Workspace"
        description="Grounded chat with intent routing, citations, tool traces, and human approval gates."
        actions={
          <Button
            variant="outline"
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={() => navigateToConversation(null)}
          >
            New conversation
          </Button>
        }
      />

      <div className="grid flex-1 gap-4 lg:grid-cols-[280px_1fr_320px] lg:overflow-hidden">
        <ConversationsSidebar
          activeId={activeConversationId}
          onSelect={navigateToConversation}
          conversations={conversations}
        />
        <ChatColumn
          key={`chat-${viewKey}-${viewEpoch}`}
          activeId={activeConversationId}
          messages={messages}
          isSending={chat.isPending}
          isLoading={
            !!activeConversationId &&
            conversationDetail.isFetching &&
            !activeConversation
          }
          isError={conversationDetail.isError}
          onRetry={() => conversationDetail.refetch()}
          onSend={handleSend}
          approvalRequired={approvalRequired}
          approvalId={approvalId}
        />
        <DetailsPanel
          key={`details-${viewKey}-${viewEpoch}`}
          data={panelData}
          sending={chat.isPending && !panelData}
        />
      </div>
    </div>
  );
}

function useWorkspaceDevDiagnostics(
  urlConversationId: string | null,
  navigationOverride: string | null | undefined,
  activeConversationId: string | null,
  detailId: string | null,
  activeConversationMatchId: string | null,
  panelSourceConversationId: string | null,
  inFlightConversationId: string | null,
  inFlightResponseConversationId: string | null,
  inFlightAppliesToView: boolean,
  messageCount: number,
  viewEpoch: number,
) {
  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;
    console.debug("[workspace] state", {
      urlConversationId,
      navigationOverride,
      activeConversationId,
      detailId,
      activeConversationMatchId,
      panelSourceConversationId,
      inFlightConversationId,
      inFlightResponseConversationId,
      inFlightAppliesToView,
      messageCount,
      viewEpoch,
    });
  }, [
    urlConversationId,
    navigationOverride,
    activeConversationId,
    detailId,
    activeConversationMatchId,
    panelSourceConversationId,
    inFlightConversationId,
    inFlightResponseConversationId,
    inFlightAppliesToView,
    messageCount,
    viewEpoch,
  ]);
}

function panelDataFromChatResponse(resp: ChatResponse): PanelData {
  return {
    citations: resp.citations,
    toolCalls: resp.tool_calls,
    traceSteps: resp.trace_steps,
    approvalRequired: resp.approval_required,
    approvalId: resp.approval_id ?? null,
    safetyFlags: resp.safety_flags,
    usage: resp.usage,
    confidence: resp.confidence,
    intent: resp.intent,
    weakEvidence: detectWeakEvidence(resp),
    traceMode: resp.trace_mode,
    traceUrl: resp.trace_url ?? null,
  };
}

function panelDataFromMessage(msg: MessageResponse): PanelData {
  return {
    citations: msg.citations,
    toolCalls: msg.tool_calls,
    traceSteps: [],
    approvalRequired: false,
    approvalId: null,
    safetyFlags: [],
    usage: {},
    confidence: msg.confidence,
    intent: msg.intent ?? null,
    weakEvidence:
      msg.intent === "knowledge_search" && msg.citations.length === 0,
    traceMode: msg.trace_mode ?? "local",
    traceUrl: msg.trace_url ?? null,
  };
}

function detectWeakEvidence(resp: ChatResponse): boolean {
  if (resp.safety_flags?.includes("weak_evidence")) return true;
  if (resp.intent === "out_of_scope") return true;
  if (resp.intent === "knowledge_search" && resp.citations.length === 0)
    return true;
  return false;
}

interface ConversationsSidebarProps {
  activeId: string | null;
  onSelect: (id: string | null) => void;
  conversations: ReturnType<typeof useConversations>;
}

function ConversationsSidebar({
  activeId,
  onSelect,
  conversations,
}: ConversationsSidebarProps) {
  const items = conversations.data?.items ?? [];
  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader>
        <CardTitle>Conversations</CardTitle>
        <span className="text-[11px] text-slate-500">
          {conversations.data?.total ?? 0} total
        </span>
      </CardHeader>
      <div className="flex-1 overflow-y-auto px-2 py-2 thin-scrollbar">
        {conversations.isError ? (
          <ErrorState onRetry={() => conversations.refetch()} />
        ) : conversations.isLoading ? (
          <div className="space-y-2 px-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            icon={MessageSquare}
            title="No conversations"
            description="Start a new conversation to see it appear here."
          />
        ) : (
          <ul className="space-y-1">
            {items.map((conv) => (
              <li key={conv.id}>
                <button
                  type="button"
                  aria-label={conv.title}
                  aria-current={activeId === conv.id ? "true" : undefined}
                  onClick={() => onSelect(conv.id)}
                  className={cn(
                    "block w-full rounded-md px-2 py-2 text-left transition-colors",
                    activeId === conv.id
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-slate-700 hover:bg-slate-100",
                  )}
                >
                  <div className="flex items-center gap-1.5">
                    <p className="line-clamp-1 flex-1 text-xs font-medium">
                      {conv.title}
                    </p>
                    <ChevronRight className="h-3 w-3 shrink-0 opacity-50" />
                  </div>
                  <p className="mt-0.5 text-[10px] text-slate-400">
                    {formatRelativeTime(conv.updated_at)}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}

interface ChatColumnProps {
  activeId: string | null;
  messages: MessageResponse[];
  isSending: boolean;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  onSend: (msg: string) => void;
  approvalRequired: boolean;
  approvalId: string | null;
}

function ChatColumn({
  activeId,
  messages,
  isSending,
  isLoading,
  isError,
  onRetry,
  onSend,
  approvalRequired,
  approvalId,
}: ChatColumnProps) {
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, isSending]);

  useEffect(() => {
    if (!activeId && messages.length === 0 && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [activeId, messages.length]);

  function submit() {
    if (!draft.trim() || isSending) return;
    onSend(draft);
    setDraft("");
  }

  return (
    <Card className="flex h-full min-h-[480px] flex-col overflow-hidden">
      <CardHeader>
        <CardTitle>
          {activeId ? "Conversation" : "New conversation"}
        </CardTitle>
        {isSending && (
          <span className="flex items-center gap-1 text-[11px] text-slate-500">
            <Loader2 className="h-3 w-3 animate-spin" /> Agent is thinking…
          </span>
        )}
      </CardHeader>
      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto bg-slate-50/40 px-5 py-4 thin-scrollbar"
      >
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : isError ? (
          <ErrorState onRetry={onRetry} />
        ) : messages.length === 0 ? (
          <EmptyState
            icon={Sparkles}
            title="Ready when you are"
            description="Ask a question grounded in your knowledge base, ask the agent to draft an email, or capture a lead."
          />
        ) : (
          messages.map((m) => <ChatMessage key={m.id} message={m} />)
        )}
        {isSending && <AssistantTypingBubble />}
        {approvalRequired && <ApprovalBanner approvalId={approvalId} />}
      </div>
      <div className="border-t border-slate-100 bg-white px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={2}
            placeholder="Ask the AI assistant… (Shift+Enter for newline)"
            className="block w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          />
          <MicrophoneInput
            onTranscript={(transcript) => {
              setDraft((prev) => {
                const combined = prev ? `${prev} ${transcript}` : transcript;
                return combined;
              });
            }}
            disabled={isSending}
          />
          <Button
            onClick={submit}
            loading={isSending}
            disabled={!draft.trim()}
            leftIcon={!isSending ? <Send className="h-4 w-4" /> : undefined}
          >
            Send
          </Button>
        </div>
      </div>
    </Card>
  );
}

function AssistantTypingBubble() {
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 text-white">
        <Sparkles className="h-4 w-4" />
      </div>
      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <div className="flex gap-1">
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" />
        </div>
      </div>
    </div>
  );
}

interface PanelData {
  citations: Citation[];
  toolCalls: ToolCallTrace[];
  traceSteps: TraceStep[];
  approvalRequired: boolean;
  approvalId: string | null;
  safetyFlags: string[];
  usage: Record<string, unknown>;
  confidence: number;
  intent: string | null;
  weakEvidence: boolean;
  traceMode?: string;
  traceUrl?: string | null;
}

interface DetailsPanelProps {
  data: PanelData | null;
  sending: boolean;
}

function DetailsPanel({ data, sending }: DetailsPanelProps) {
  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader>
        <CardTitle>Response details</CardTitle>
        <span className="text-[11px] text-slate-500">
          AI transparency
        </span>
      </CardHeader>
      <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4 thin-scrollbar">
        {sending && !data ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-3/4" />
          </div>
        ) : !data ? (
          <EmptyState
            icon={BookOpen}
            title="No response yet"
            description="Citations, traces, and confidence will appear here after the agent replies."
          />
        ) : (
          <>
            {(data.intent || data.confidence > 0) && (
              <div className="flex flex-wrap items-center gap-2">
                {data.intent && <IntentBadge intent={data.intent} />}
                {data.confidence > 0 && (
                  <ConfidenceBadge value={data.confidence} />
                )}
              </div>
            )}

            {data.approvalRequired && (
              <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                <p className="flex items-center gap-1 font-semibold">
                  <ShieldAlert className="h-3.5 w-3.5" /> Approval gated
                </p>
                <p className="mt-1">
                  This action will not execute until an admin approves it on the
                  Approvals page.
                </p>
              </div>
            )}

            {data.weakEvidence && <WeakEvidenceWarning />}

            <section>
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <BookOpen className="h-3.5 w-3.5" />
                Citations ({data.citations.length})
              </h4>
              {data.citations.length === 0 ? (
                <p className="text-xs text-slate-500">
                  No citations were grounded in the knowledge base for this response.
                </p>
              ) : (
                <div className="space-y-2">
                  {data.citations.map((c, i) => (
                    <CitationCard key={`${c.document_id}-${i}`} citation={c} index={i} />
                  ))}
                </div>
              )}
            </section>

            <section>
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <Wrench className="h-3.5 w-3.5" /> Trace & tools
              </h4>
              <ToolTracePanel
                toolCalls={data.toolCalls}
                traceSteps={data.traceSteps}
                traceMode={data.traceMode}
                traceUrl={data.traceUrl}
              />
            </section>

            {Object.keys(data.usage).length > 0 && (
              <section>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Usage
                </h4>
                <div className="rounded-md border border-slate-200 bg-slate-50/60 p-2 font-mono text-[11px] text-slate-700">
                  {Object.entries(data.usage).map(([k, v]) => (
                    <p key={k}>
                      <span className="text-slate-500">{k}:</span> {String(v)}
                    </p>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </Card>
  );
}

function WorkspaceSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <div className="grid gap-4 lg:grid-cols-[280px_1fr_320px]">
        <Skeleton className="h-[480px]" />
        <Skeleton className="h-[480px]" />
        <Skeleton className="h-[480px]" />
      </div>
    </div>
  );
}
