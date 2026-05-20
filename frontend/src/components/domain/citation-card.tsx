import { BookOpen, Globe } from "lucide-react";
import type { Citation } from "@/types/api";

interface CitationCardProps {
  citation: Citation;
  index?: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const score = Math.round(citation.relevance_score * 100);
  const isExternal = citation.citation_type === "external";
  const Icon = isExternal ? Globe : BookOpen;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-indigo-50 text-indigo-600">
            <Icon className="h-3.5 w-3.5" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-slate-900">
              {index !== undefined && (
                <span className="mr-1 text-slate-400">[{index + 1}]</span>
              )}
              {isExternal && citation.url ? (
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-700 hover:underline"
                >
                  {citation.document_title}
                </a>
              ) : (
                citation.document_title
              )}
            </p>
            <p className="text-[11px] text-slate-500">
              {isExternal
                ? `External web · ${citation.source || citation.section || "web"}`
                : citation.section || "Knowledge base"}
            </p>
          </div>
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
          {score}%
        </span>
      </div>
      {citation.chunk_text && (
        <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-slate-600">
          {citation.chunk_text}
        </p>
      )}
    </div>
  );
}
