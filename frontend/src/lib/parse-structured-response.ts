export type StructuredSectionId =
  | "summary"
  | "key-points"
  | "evidence"
  | "next-action"
  | "external-research"
  | "email-preview"
  | "meeting-proposal"
  | "other";

export interface StructuredSection {
  id: StructuredSectionId;
  title: string;
  content: string;
  items: string[];
}

export interface SourceItem {
  title: string;
  url?: string;
  snippet?: string;
  published?: string;
  raw: string;
}

export interface MeetingProposalDetails {
  title: string;
  startTime: string;
  endTime: string;
  timezone: string;
  approvalStatus: string;
  nextAction: string;
  attendees: string;
}

export interface CalendarListItem {
  title: string;
  when: string;
  detail: string;
}

export interface CalendarListDetails {
  heading: string;
  notice: string;
  items: CalendarListItem[];
  footer: string;
}

export type ParsedAssistantResponse =
  | { kind: "structured"; sections: StructuredSection[] }
  | { kind: "compound"; sections: StructuredSection[] }
  | { kind: "email"; subject: string; body: string }
  | { kind: "meeting-proposal"; proposal: MeetingProposalDetails }
  | { kind: "meetings-list"; list: CalendarListDetails }
  | { kind: "availability-slots"; list: CalendarListDetails }
  | { kind: "plain"; content: string };

const STANDARD_SECTION_TITLES: Record<string, StructuredSectionId> = {
  summary: "summary",
  "key points": "key-points",
  "evidence or sources": "evidence",
  "suggested next action": "next-action",
};

const COMPOUND_SECTION_TITLES: Record<string, StructuredSectionId> = {
  "external market research": "external-research",
  "draft email preview": "email-preview",
  "meeting proposal": "meeting-proposal",
};

function normalizeTitle(title: string): string {
  return title.trim().toLowerCase();
}

function sectionIdForTitle(title: string): StructuredSectionId {
  const normalized = normalizeTitle(title);
  return (
    STANDARD_SECTION_TITLES[normalized] ??
    COMPOUND_SECTION_TITLES[normalized] ??
    "other"
  );
}

function extractListItems(content: string): string[] {
  const items: string[] = [];
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const bullet = trimmed.match(/^[-*•]\s+(.+)$/);
    if (bullet) {
      items.push(bullet[1].trim());
      continue;
    }
    const numbered = trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (numbered) {
      items.push(numbered[1].trim());
    }
  }
  return items;
}

function splitByMarkdownHeaders(
  content: string,
  allowedTitles?: Record<string, StructuredSectionId>,
): StructuredSection[] {
  const lines = content.split("\n");
  const sections: StructuredSection[] = [];
  let currentTitle: string | null = null;
  let buffer: string[] = [];

  const flush = () => {
    if (!currentTitle) return;
    const body = buffer.join("\n").trim();
    sections.push({
      id: allowedTitles
        ? (allowedTitles[normalizeTitle(currentTitle)] ?? sectionIdForTitle(currentTitle))
        : sectionIdForTitle(currentTitle),
      title: currentTitle,
      content: body,
      items: extractListItems(body),
    });
    buffer = [];
  };

  for (const line of lines) {
    const headerMatch = line.match(/^##\s+(.+?)\s*$/);
    if (headerMatch) {
      const title = headerMatch[1].trim();
      const isBoundary =
        !allowedTitles || normalizeTitle(title) in allowedTitles;
      if (!isBoundary) {
        if (currentTitle) {
          buffer.push(line);
        }
        continue;
      }
      flush();
      currentTitle = title;
      continue;
    }
    if (currentTitle) {
      buffer.push(line);
    }
  }
  flush();
  return sections;
}

function contentHasCompoundHeaders(content: string): boolean {
  return Object.keys(COMPOUND_SECTION_TITLES).some((title) =>
    new RegExp(`^##\\s+${title}\\s*$`, "im").test(content),
  );
}

function parseEmailDraft(content: string): { subject: string; body: string } | null {
  const match = content.match(/^Subject:\s*(.+?)(?:\n\n|\n$)([\s\S]*)$/);
  if (!match) return null;
  return {
    subject: match[1].trim(),
    body: match[2].trim(),
  };
}

function parseMeetingProposal(content: string): MeetingProposalDetails | null {
  const titleMatch = content.match(/^(?:Title|Meeting proposal):\s*(.+)$/m);
  const timeMatch = content.match(/^(?:Date and time|Proposed time):\s*(.+)$/m);
  const timezoneMatch = content.match(/^Timezone:\s*(.+)$/m);
  const approvalMatch = content.match(/^Approval status:\s*(.+)$/m);
  const nextActionMatch = content.match(/^Next action:\s*(.+)$/m);
  const attendeesMatch = content.match(/^Attendees:\s*(.+)$/m);

  if (!titleMatch || !timeMatch) {
    return null;
  }

  const when = timeMatch[1].trim();
  const split = when.split(/\s+[–—]\s+/);
  return {
    title: titleMatch[1].trim(),
    startTime: split[0]?.trim() ?? when,
    endTime: split[1]?.trim() ?? "",
    timezone: timezoneMatch?.[1]?.trim() ?? "",
    approvalStatus: approvalMatch?.[1]?.trim() ?? "pending",
    nextAction:
      nextActionMatch?.[1]?.trim() ??
      "Review and approve to create this meeting.",
    attendees: attendeesMatch?.[1]?.trim() ?? "",
  };
}

function parseNumberedCalendarItems(content: string): CalendarListItem[] {
  const items: CalendarListItem[] = [];
  const lines = content.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const numbered = lines[i].trim().match(/^\d+[.)]\s+(.+)$/);
    if (!numbered) continue;
    const rest = numbered[1].trim();
    const [titlePart, whenPart] = rest.split(/\s+—\s+/, 2);
    let detail = "";
    const next = lines[i + 1];
    if (next && /^\s{2,}\S/.test(next) && !/^\d+[.)]\s+/.test(next.trim())) {
      detail = next.trim();
    }
    items.push({
      title: (titlePart || rest).trim(),
      when: (whenPart || "").trim(),
      detail,
    });
  }
  return items;
}

function parseCalendarListBlock(
  content: string,
  headingPattern: RegExp,
): CalendarListDetails | null {
  const trimmed = content.trim();
  if (!headingPattern.test(trimmed.split("\n", 1)[0] ?? "")) {
    return null;
  }
  const lines = trimmed.split("\n");
  const heading = (lines[0] ?? "").replace(/:$/, "").trim();
  const noticeLines: string[] = [];
  const footerLines: string[] = [];
  const bodyLines: string[] = [];
  let seenItem = false;
  for (const line of lines.slice(1)) {
    const trimmedLine = line.trim();
    if (!trimmedLine) continue;
    if (/^times shown in /i.test(trimmedLine)) {
      footerLines.push(trimmedLine);
      continue;
    }
    if (/^\d+[.)]\s+/.test(trimmedLine) || (seenItem && /^\s{2,}\S/.test(line))) {
      seenItem = true;
      bodyLines.push(line);
      continue;
    }
    if (!seenItem) {
      noticeLines.push(trimmedLine);
    }
  }
  return {
    heading,
    notice: noticeLines.join(" "),
    items: parseNumberedCalendarItems(bodyLines.join("\n")),
    footer: footerLines.join(" "),
  };
}

function hasStandardKnowledgeSections(sections: StructuredSection[]): boolean {
  const ids = new Set(sections.map((section) => section.id));
  return (
    ids.has("summary") &&
    (ids.has("key-points") || ids.has("evidence") || ids.has("next-action"))
  );
}

export function parseStructuredResponse(content: string): ParsedAssistantResponse {
  const trimmed = content.trim();
  if (!trimmed) {
    return { kind: "plain", content: "" };
  }

  const emailDraft = parseEmailDraft(trimmed);
  if (emailDraft && !trimmed.startsWith("##")) {
    return { kind: "email", ...emailDraft };
  }

  const meetingProposal = parseMeetingProposal(trimmed);
  if (meetingProposal && !trimmed.startsWith("##")) {
    return { kind: "meeting-proposal", proposal: meetingProposal };
  }

  const meetingsList = parseCalendarListBlock(
    trimmed,
    /^(upcoming meetings|no meetings are on the calendar)/i,
  );
  if (meetingsList && !trimmed.startsWith("##")) {
    return { kind: "meetings-list", list: meetingsList };
  }

  const availabilityList = parseCalendarListBlock(
    trimmed,
    /^(available time slots|available meeting times|you are available)/i,
  );
  if (availabilityList && !trimmed.startsWith("##")) {
    return { kind: "availability-slots", list: availabilityList };
  }

  if (contentHasCompoundHeaders(trimmed)) {
    const compoundSections = splitByMarkdownHeaders(trimmed, COMPOUND_SECTION_TITLES);
    if (compoundSections.length > 0) {
      return { kind: "compound", sections: compoundSections };
    }
  }

  const sections = splitByMarkdownHeaders(trimmed, STANDARD_SECTION_TITLES);
  if (sections.length === 0) {
    return { kind: "plain", content: trimmed };
  }

  if (hasStandardKnowledgeSections(sections)) {
    return { kind: "structured", sections };
  }

  if (sections.length >= 2) {
    return { kind: "structured", sections };
  }

  return { kind: "plain", content: trimmed };
}

export function parseSourceLine(line: string): SourceItem {
  const raw = line.trim();
  const text = raw.replace(/^[-*•]\s*/, "").trim();

  const boldMatch = text.match(
    /^\*\*(.+?)\*\*(?:\s*\(([^)]+)\))?(?::\s*(.+?))?(?:\s*\[published:\s*(.+?)\])?$/i,
  );
  if (boldMatch) {
    const [, title, url, snippet, published] = boldMatch;
    return {
      title: title.trim(),
      url: url?.startsWith("http") ? url.trim() : undefined,
      snippet: snippet?.trim(),
      published: published?.trim(),
      raw,
    };
  }

  const bracketTitle = text.match(/^\[(.+?)\](?::\s*(.+))?$/);
  if (bracketTitle) {
    return {
      title: bracketTitle[1].trim(),
      snippet: bracketTitle[2]?.trim(),
      raw,
    };
  }

  const urlInParens = text.match(/^(.+?)\s*\((https?:\/\/[^)]+)\)(?::\s*(.+))?$/);
  if (urlInParens) {
    return {
      title: urlInParens[1].replace(/^\*\*|\*\*$/g, "").trim(),
      url: urlInParens[2].trim(),
      snippet: urlInParens[3]?.trim(),
      raw,
    };
  }

  return { title: text, raw };
}

export function parseEvidenceContent(content: string): {
  subsections: { label: string; items: SourceItem[] }[];
  items: SourceItem[];
} {
  const lines = content.split("\n");
  const subsections: { label: string; items: SourceItem[] }[] = [];
  const topLevelItems: SourceItem[] = [];
  let currentLabel: string | null = null;
  let currentItems: SourceItem[] = [];

  const flushSubsection = () => {
    if (currentLabel) {
      subsections.push({ label: currentLabel, items: currentItems });
    }
    currentLabel = null;
    currentItems = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    const subheader = trimmed.match(/^\*\*(.+?)\*\*$/);
    if (subheader) {
      flushSubsection();
      currentLabel = subheader[1].trim();
      continue;
    }

    const isListItem =
      trimmed.startsWith("- ") ||
      trimmed.startsWith("* ") ||
      trimmed.startsWith("• ");

    if (isListItem) {
      const item = parseSourceLine(trimmed);
      if (currentLabel) {
        currentItems.push(item);
      } else {
        topLevelItems.push(item);
      }
      continue;
    }

    if (!currentLabel) {
      topLevelItems.push({ title: trimmed, raw: trimmed });
    } else {
      currentItems.push({ title: trimmed, raw: trimmed });
    }
  }

  flushSubsection();
  return { subsections, items: topLevelItems };
}
