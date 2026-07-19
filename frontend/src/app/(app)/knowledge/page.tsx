"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import {
  BookOpen,
  Upload,
  FileText,
  Trash2,
  Loader2,
  Send,
  X,
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";
import { Modal } from "@/components/ui/modal";
import { StatusBadge } from "@/components/domain/status-badge";
import { ConfidenceBadge } from "@/components/domain/confidence-badge";
import { WeakEvidenceWarning } from "@/components/domain/weak-evidence-warning";
import { ApiRequestError } from "@/lib/api-client";
import {
  useAnswerMutation,
  useDocument,
  useDocumentDeleteMutation,
  useDocumentUploadMutation,
  useDocuments,
} from "@/lib/queries";
import {
  cn,
  formatDateTime,
  formatNumber,
  formatRelativeTime,
} from "@/lib/utils";

export default function KnowledgePage() {
  const documents = useDocuments();
  const upload = useDocumentUploadMutation();
  const del = useDocumentDeleteMutation();
  const answer = useAnswerMutation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const items = documents.data?.items ?? [];

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      await upload.mutateAsync(file);
      toast.success("Document indexed", {
        description: `${file.name} is now searchable.`,
      });
    } catch (err) {
      const msg =
        err instanceof ApiRequestError ? err.message : "Upload failed";
      toast.error("Upload failed", { description: msg });
    }
  }

  async function onAsk(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    try {
      await answer.mutateAsync({ query: trimmed, top_k: 5 });
    } catch (err) {
      console.error("knowledge.answer_failed", err);
      const msg =
        err instanceof ApiRequestError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Search failed";
      toast.error("Could not get answer", { description: msg });
    }
  }

  async function onDelete(id: string, title: string) {
    if (!window.confirm(`Delete "${title}"? This removes its index.`)) return;
    try {
      await del.mutateAsync(id);
      toast.success("Document deleted");
      if (detailId === id) setDetailId(null);
    } catch (err) {
      const msg =
        err instanceof ApiRequestError ? err.message : "Delete failed";
      toast.error("Delete failed", { description: msg });
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Knowledge Base"
        description="Index documents and ask grounded questions. The agent cites every source."
        actions={
          <>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".txt,.md,.pdf,.html"
              onChange={onFileChange}
            />
            <Button
              loading={upload.isPending}
              leftIcon={<Upload className="h-4 w-4" />}
              onClick={() => fileInputRef.current?.click()}
            >
              Upload document
            </Button>
          </>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Ask a grounded question</CardTitle>
          <span className="text-[11px] text-slate-500">
            Answers include citations from your indexed documents
          </span>
        </CardHeader>
        <CardContent>
          <form onSubmit={onAsk} className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. What is NovaEdge's escalation policy?"
              className="block flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            />
            <Button
              type="submit"
              loading={answer.isPending}
              disabled={!query.trim()}
              leftIcon={!answer.isPending ? <Send className="h-4 w-4" /> : undefined}
            >
              Ask
            </Button>
          </form>

          {answer.data && (
            <div className="mt-4 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <ConfidenceBadge
                  value={answer.data.confidence}
                  weakEvidence={answer.data.weak_evidence}
                />
                {answer.data.fallback_used && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                    Fallback model
                  </span>
                )}
                <span className="text-[11px] text-slate-500">
                  Model: <span className="font-mono">{answer.data.model}</span>
                </span>
              </div>
              {answer.data.weak_evidence && <WeakEvidenceWarning />}
              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                  {answer.data.answer}
                </p>
              </div>
              {answer.data.citations.length > 0 && (
                <div>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Sources ({answer.data.citations.length})
                  </h4>
                  <ul className="space-y-1.5">
                    {answer.data.citations.map((c, i) => (
                      <li
                        key={c.chunk_id}
                        className="flex items-center justify-between gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs"
                      >
                        <div className="flex items-start gap-2">
                          <span className="text-slate-400">[{i + 1}]</span>
                          <div>
                            <p className="font-semibold text-slate-900">
                              {c.document_title}
                            </p>
                            {c.section && (
                              <p className="text-[11px] text-slate-500">
                                {c.section}
                              </p>
                            )}
                          </div>
                        </div>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                          {Math.round(c.score * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Indexed documents</CardTitle>
          <span className="text-[11px] text-slate-500">
            {documents.data?.total ?? 0} total
          </span>
        </CardHeader>
        <CardContent>
          {documents.isError ? (
            <ErrorState onRetry={() => documents.refetch()} />
          ) : documents.isLoading ? (
            <LoadingSkeleton lines={5} />
          ) : items.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title="No documents indexed yet"
              description="Upload markdown, text, or PDF files. Each document is chunked and embedded for grounded answers."
              action={
                <Button
                  size="sm"
                  leftIcon={<Upload className="h-3.5 w-3.5" />}
                  onClick={() => fileInputRef.current?.click()}
                >
                  Upload document
                </Button>
              }
            />
          ) : (
            <ul className="divide-y divide-slate-100">
              {items.map((doc) => (
                <li
                  key={doc.id}
                  className={cn(
                    "flex items-center justify-between gap-4 py-3 hover:bg-slate-50/60 -mx-5 px-5 cursor-pointer",
                    detailId === doc.id && "bg-indigo-50/30",
                  )}
                  onClick={() => setDetailId(doc.id)}
                >
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-md bg-emerald-50 text-emerald-600">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-900">
                        {doc.title}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {doc.filename} · {formatNumber(doc.chunk_count)} chunks ·{" "}
                        {formatRelativeTime(doc.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={doc.status} />
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete(doc.id, doc.title);
                      }}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                      disabled={del.isPending}
                      aria-label="Delete document"
                    >
                      {del.isPending && del.variables === doc.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <DocumentDetailModal
        documentId={detailId}
        onClose={() => setDetailId(null)}
      />
    </div>
  );
}

interface DocumentDetailModalProps {
  documentId: string | null;
  onClose: () => void;
}

function DocumentDetailModal({ documentId, onClose }: DocumentDetailModalProps) {
  const detail = useDocument(documentId);
  if (!documentId) return null;
  return (
    <Modal
      open={!!documentId}
      onClose={onClose}
      title={detail.data?.title ?? "Document details"}
      description={detail.data?.filename ?? "Loading…"}
      size="lg"
      footer={
        <Button variant="outline" onClick={onClose} leftIcon={<X className="h-3.5 w-3.5" />}>
          Close
        </Button>
      }
    >
      {detail.isLoading ? (
        <LoadingSkeleton lines={6} />
      ) : detail.isError || !detail.data ? (
        <ErrorState onRetry={() => detail.refetch()} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <Stat label="Status" value={<StatusBadge status={detail.data.status} />} />
            <Stat label="Source" value={detail.data.source} />
            <Stat label="Chunks" value={formatNumber(detail.data.chunk_count)} />
            <Stat
              label="Size"
              value={`${formatNumber(detail.data.size_bytes)} bytes`}
            />
            <Stat
              label="Uploaded"
              value={formatDateTime(detail.data.created_at)}
            />
            <Stat label="Type" value={detail.data.content_type} />
          </div>

          {detail.data.chunks.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Indexed chunks ({detail.data.chunks.length})
              </h4>
              <ul className="max-h-80 space-y-2 overflow-y-auto pr-1 thin-scrollbar">
                {detail.data.chunks.map((chunk) => (
                  <li
                    key={chunk.id}
                    className="rounded-md border border-slate-200 bg-slate-50/40 p-3"
                  >
                    <div className="flex items-center justify-between text-[11px] text-slate-500">
                      <span>
                        Chunk #{chunk.ordinal}
                        {chunk.section ? ` · ${chunk.section}` : ""}
                      </span>
                      <span>{chunk.token_count} tokens</span>
                    </div>
                    <p className="mt-1 line-clamp-4 text-xs text-slate-700">
                      {chunk.content}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
      <p className="text-[10px] uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <div className="mt-0.5 text-xs font-medium text-slate-900">{value}</div>
    </div>
  );
}
