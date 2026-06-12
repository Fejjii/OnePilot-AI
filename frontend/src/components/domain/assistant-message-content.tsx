import type { ReactNode } from "react";
import {
  ArrowRight,
  BookOpen,
  ExternalLink,
  Globe,
  Lightbulb,
  ListChecks,
  Mail,
  Sparkles,
} from "lucide-react";
import {
  parseEvidenceContent,
  parseSourceLine,
  parseStructuredResponse,
  type ParsedAssistantResponse,
  type SourceItem,
  type StructuredSection,
} from "@/lib/parse-structured-response";
import { cn } from "@/lib/utils";

interface AssistantMessageContentProps {
  content: string;
}

function SectionLabel({
  children,
  icon: Icon,
}: {
  children: ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex items-center gap-1.5">
      {Icon && <Icon className="h-3.5 w-3.5 text-indigo-500" />}
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {children}
      </p>
    </div>
  );
}

function PlainTextBlock({ content }: { content: string }) {
  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
      {content}
    </p>
  );
}

function SourceRow({ source, external = false }: { source: SourceItem; external?: boolean }) {
  const Icon = external ? Globe : BookOpen;

  return (
    <div className="rounded-md border border-slate-200 bg-slate-50/70 px-2.5 py-2">
      <div className="flex items-start gap-2">
        <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-white text-indigo-600 ring-1 ring-slate-200">
          <Icon className="h-3 w-3" />
        </div>
        <div className="min-w-0 flex-1">
          {source.url ? (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-700 hover:underline"
            >
              {source.title}
              <ExternalLink className="h-3 w-3 shrink-0 opacity-70" />
            </a>
          ) : (
            <p className="text-xs font-semibold text-slate-900">{source.title}</p>
          )}
          {source.snippet && (
            <p className="mt-1 text-xs leading-relaxed text-slate-600">
              {source.snippet}
            </p>
          )}
          {source.published && (
            <p className="mt-1 text-[10px] text-slate-400">
              Published {source.published}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function KeyPointsList({ items }: { items: string[] }) {
  if (items.length === 0) return null;

  return (
    <ul className="mt-2 space-y-2">
      {items.map((item, index) => (
        <li key={`${index}-${item.slice(0, 24)}`} className="flex gap-2.5">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500" />
          <span className="text-sm leading-relaxed text-slate-700">{item}</span>
        </li>
      ))}
    </ul>
  );
}

function EvidenceSection({ section }: { section: StructuredSection }) {
  const { subsections, items } = parseEvidenceContent(section.content);
  const listItems =
    items.length > 0 ? items : section.items.map((item) => parseSourceLine(item));

  return (
    <div className="space-y-2">
      <SectionLabel icon={BookOpen}>Evidence & sources</SectionLabel>
      {subsections.length > 0 ? (
        <div className="mt-2 space-y-3">
          {subsections.map((subsection) => (
            <div key={subsection.label}>
              <p className="text-[11px] font-medium text-slate-600">
                {subsection.label}
              </p>
              <div className="mt-1.5 space-y-2">
                {subsection.items.map((item, index) => (
                  <SourceRow
                    key={`${subsection.label}-${index}`}
                    source={item}
                    external={subsection.label.toLowerCase().includes("web")}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-2 space-y-2">
          {listItems.map((item, index) => (
            <SourceRow key={`${index}-${item.title}`} source={item} external />
          ))}
        </div>
      )}
    </div>
  );
}

function NextActionCallout({ content }: { content: string }) {
  const text = content.trim();
  if (!text) return null;

  return (
    <div className="rounded-lg border border-indigo-200/80 bg-indigo-50/60 px-3 py-2.5">
      <SectionLabel icon={Lightbulb}>Suggested next action</SectionLabel>
      <div className="mt-2 flex items-start gap-2">
        <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" />
        <p className="text-sm leading-relaxed text-indigo-950">{text}</p>
      </div>
    </div>
  );
}

function StructuredSectionBlock({ section }: { section: StructuredSection }) {
  switch (section.id) {
    case "summary":
      return (
        <div>
          <SectionLabel icon={Sparkles}>Summary</SectionLabel>
          <p className="mt-1.5 text-sm leading-relaxed text-slate-800">
            {section.content}
          </p>
        </div>
      );
    case "key-points":
      return (
        <div>
          <SectionLabel icon={ListChecks}>Key points</SectionLabel>
          <KeyPointsList items={section.items} />
        </div>
      );
    case "evidence":
      return <EvidenceSection section={section} />;
    case "next-action":
      return <NextActionCallout content={section.content} />;
    default:
      return (
        <div>
          <SectionLabel>{section.title}</SectionLabel>
          {section.items.length > 0 ? (
            <KeyPointsList items={section.items} />
          ) : (
            <p className="mt-1.5 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
              {section.content}
            </p>
          )}
        </div>
      );
  }
}

function StructuredKnowledgeResponse({ sections }: { sections: StructuredSection[] }) {
  const orderedIds = ["summary", "key-points", "evidence", "next-action"] as const;
  const ordered = orderedIds
    .map((id) => sections.find((section) => section.id === id))
    .filter((section): section is StructuredSection => Boolean(section));
  const remainder = sections.filter(
    (section) => !orderedIds.includes(section.id as (typeof orderedIds)[number]),
  );

  return (
    <div className="space-y-4">
      {[...ordered, ...remainder].map((section) => (
        <StructuredSectionBlock key={`${section.id}-${section.title}`} section={section} />
      ))}
    </div>
  );
}

function EmailDraftContent({ subject, body }: { subject: string; body: string }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5">
        <Mail className="h-3.5 w-3.5 text-indigo-500" />
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Email draft
        </p>
      </div>
      <div className="rounded-md border border-slate-200 bg-slate-50/50 px-3 py-2">
        <p className="text-[11px] font-medium text-slate-500">Subject</p>
        <p className="mt-0.5 text-sm font-medium text-slate-900">{subject}</p>
      </div>
      <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
        {body}
      </div>
    </div>
  );
}

function CompoundWorkflowResponse({ sections }: { sections: StructuredSection[] }) {
  return (
    <div className="space-y-5">
      {sections.map((section) => {
        if (section.id === "email-preview") {
          const email = parseStructuredResponse(section.content);
          if (email.kind === "email") {
            return (
              <div key={section.id}>
                <EmailDraftContent subject={email.subject} body={email.body} />
              </div>
            );
          }
        }

        if (section.id === "external-research") {
          const nested = parseStructuredResponse(section.content);
          if (nested.kind === "structured") {
            return (
              <div key={section.id} className="space-y-3">
                <SectionLabel icon={Globe}>External market research</SectionLabel>
                <StructuredKnowledgeResponse sections={nested.sections} />
              </div>
            );
          }
        }

        return (
          <div key={`${section.id}-${section.title}`}>
            <SectionLabel>
              {section.title}
            </SectionLabel>
            <div className="mt-2">
              {section.items.length > 0 ? (
                <KeyPointsList items={section.items} />
              ) : (
                <PlainTextBlock content={section.content} />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function renderParsedResponse(parsed: ParsedAssistantResponse) {
  switch (parsed.kind) {
    case "structured":
      return <StructuredKnowledgeResponse sections={parsed.sections} />;
    case "compound":
      return <CompoundWorkflowResponse sections={parsed.sections} />;
    case "email":
      return <EmailDraftContent subject={parsed.subject} body={parsed.body} />;
    case "plain":
      return <PlainTextBlock content={parsed.content} />;
  }
}

export function AssistantMessageContent({ content }: AssistantMessageContentProps) {
  const parsed = parseStructuredResponse(content);
  const isRich =
    parsed.kind === "structured" ||
    parsed.kind === "compound" ||
    parsed.kind === "email";

  return (
    <div
      className={cn(
        "text-sm leading-relaxed",
        isRich && "space-y-1",
      )}
      data-testid="assistant-message-content"
      data-response-kind={parsed.kind}
    >
      {renderParsedResponse(parsed)}
    </div>
  );
}
