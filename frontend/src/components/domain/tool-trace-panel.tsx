import { Wrench, Workflow, ExternalLink } from "lucide-react";
import type { ExecutionTraceStep, ToolCallTrace, TraceStep } from "@/types/api";
import { ToolBadge } from "./tool-badge";
import {
  mapInternalTraceSteps,
  sanitizeExecutionTrace,
} from "@/lib/execution-trace";

interface ToolTracePanelProps {
  toolCalls: ToolCallTrace[];
  executionTrace?: ExecutionTraceStep[];
  traceSteps?: TraceStep[];
  traceMode?: string;
  traceUrl?: string | null;
}

export function ToolTracePanel({
  toolCalls,
  executionTrace,
  traceSteps,
  traceMode = "local",
  traceUrl,
}: ToolTracePanelProps) {
  const persisted = sanitizeExecutionTrace(executionTrace);
  const steps =
    persisted.length > 0 ? persisted : mapInternalTraceSteps(traceSteps);
  const hasTools = toolCalls.length > 0;
  const hasSteps = steps.length > 0;

  if (!hasTools && !hasSteps) {
    return (
      <p className="text-xs text-slate-500" data-testid="execution-trace-empty">
        No recorded steps for this reply.
      </p>
    );
  }

  return (
    <div className="space-y-4" data-testid="execution-trace">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Trace mode:</span>
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
            Steps
          </h4>
          <ol className="space-y-1.5">
            {steps.map((step, i) => (
              <li
                key={`${step.key}-${i}`}
                className="flex items-start gap-2 rounded-md border border-slate-200 bg-slate-50/60 px-3 py-2"
              >
                <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-200 text-[10px] font-semibold text-slate-700">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-slate-900">{step.label}</p>
                  {step.detail && (
                    <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">
                      {step.detail}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {hasTools && (
        <div>
          <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <Wrench className="h-3.5 w-3.5" />
            Tools used
          </h4>
          <ul className="flex flex-wrap gap-1.5">
            {toolCalls.map((tool, i) => (
              <li key={`${tool.tool_name}-${i}`}>
                <ToolBadge toolName={tool.tool_name} label={tool.label} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
