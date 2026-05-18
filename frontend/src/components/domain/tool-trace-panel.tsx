import { Wrench, Workflow, ExternalLink } from "lucide-react";
import type { ToolCallTrace, TraceStep } from "@/types/api";
import { titleize } from "@/lib/utils";

interface ToolTracePanelProps {
  toolCalls: ToolCallTrace[];
  traceSteps?: TraceStep[];
  traceMode?: string;
  traceUrl?: string | null;
}

export function ToolTracePanel({
  toolCalls,
  traceSteps,
  traceMode = "local",
  traceUrl,
}: ToolTracePanelProps) {
  const hasTools = toolCalls.length > 0;
  const hasSteps = (traceSteps?.length ?? 0) > 0;

  if (!hasTools && !hasSteps) {
    return (
      <p className="text-xs text-slate-500">
        No tool calls or trace steps for this response.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Trace Mode Badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">
            Trace mode:
          </span>
          <span
            className={
              "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide " +
              (traceMode === "langsmith"
                ? "bg-indigo-100 text-indigo-700"
                : "bg-slate-100 text-slate-700")
            }
          >
            {traceMode === "langsmith" ? "LangSmith" : "Local"}
          </span>
        </div>
        {traceMode === "langsmith" && traceUrl && (
          <a
            href={traceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100"
          >
            <ExternalLink className="h-3 w-3" />
            Open LangSmith trace
          </a>
        )}
      </div>

      {hasSteps && (
        <div>
          <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <Workflow className="h-3.5 w-3.5" />
            Agent trace
          </h4>
          <ol className="space-y-1.5">
            {traceSteps!.map((step, i) => (
              <li
                key={`${step.step}-${i}`}
                className="flex items-start gap-2 rounded-md border border-slate-200 bg-slate-50/60 px-3 py-2"
              >
                <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-200 text-[10px] font-semibold text-slate-700">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-slate-900">
                    {titleize(step.step)}
                  </p>
                  {step.detail && (
                    <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">
                      {step.detail}
                    </p>
                  )}
                </div>
                {step.duration_ms > 0 && (
                  <span className="text-[10px] text-slate-400">
                    {step.duration_ms}ms
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      {hasTools && (
        <div>
          <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <Wrench className="h-3.5 w-3.5" />
            Tool calls
          </h4>
          <ul className="space-y-1.5">
            {toolCalls.map((tool, i) => (
              <li
                key={`${tool.tool_name}-${i}`}
                className="rounded-md border border-slate-200 bg-white px-3 py-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="font-mono text-xs font-semibold text-slate-900">
                    {tool.tool_name}
                  </p>
                  <span className="text-[10px] text-slate-400">
                    {tool.duration_ms}ms
                  </span>
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                  <span className="text-slate-400">in:</span> {tool.input_summary}
                </p>
                <p className="text-[11px] leading-relaxed text-slate-500">
                  <span className="text-slate-400">out:</span> {tool.output_summary}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
