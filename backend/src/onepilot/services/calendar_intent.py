"""Shared calendar routing signals for Stage-1, Stage-2, and tool inference.

Patterns are semantic (availability vs meetings vs scheduling) rather than
single-phrase exact matches. Conversation continuation only inherits fields
from bounded recent same-conversation user turns.
"""

from __future__ import annotations

import re

_AVAILABILITY = re.compile(
    r"\b("
    r"when am i (available|free)"
    r"|what times? am i (available|free)"
    r"|what times? are we (available|free)"
    r"|am i (available|free)"
    r"|are we (available|free)"
    r"|do i have (any )?(availability|free time|open (time )?slots?)"
    r"|do we have (any )?(availability|free time|open (time )?slots?)"
    r"|check (my )?(calendar )?availability"
    r"|availability (tomorrow|today|next|this|between)"
    r"|(available|free) (tomorrow|today|next week|this week|between)"
    r"|free (tomorrow|next|this)"
    r"|busy tomorrow"
    r"|open (time )?slots?"
    r"|find (an? )?(open|available|free)"
    r"|available between"
    r"|free between"
    r")\b",
    re.IGNORECASE,
)

_LIST_EVENTS = re.compile(
    r"\b("
    r"show (me )?(my )?(upcoming )?meetings"
    r"|list (my )?(upcoming )?meetings"
    r"|what meetings"
    r"|meetings (are |on )"
    r"|on the calendar"
    r"|calendar this week"
    r"|check my calendar"
    r"|what'?s on (my |the )?calendar"
    r"|upcoming meetings"
    r"|my (upcoming )?meetings"
    r")\b",
    re.IGNORECASE,
)

_SCHEDULING = re.compile(
    r"\b("
    r"(schedule|book a|book (the|an?)|set up a|create a).{0,60}"
    r"\b(meeting|call|appointment|slot|demo)\b"
    r"|\b(suggest|propose|offer|recommend).{0,30}\b(slot|time|times|meeting)\b"
    r"|\bbook.{0,20}\b\d{1,3}[- ]?(?:minute|min).{0,20}\bslot\b"
    r")",
    re.IGNORECASE,
)

_SUGGEST_SLOTS = re.compile(
    r"\b(suggest|propose|offer|recommend).{0,40}\b(slots?|times?)\b",
    re.IGNORECASE,
)

_CONTINUATION = re.compile(
    r"^\s*("
    r"just schedule( (it|this|that|the meeting|that meeting|this meeting|a meeting))?"
    r"|yes,?\s*(please,?\s*)?(schedule|book)( it| the meeting| that)?"
    r"|go ahead( and schedule( it| the meeting)?)?"
    r"|please (schedule|book)( it| the meeting)?"
    r"|confirm( (the|that|this) meeting)?"
    r"|schedule it"
    r"|book it"
    r"|proceed"
    r")\s*[.!]?\s*$",
    re.IGNORECASE,
)

_TITLE_MARKER = re.compile(
    r"(?:^|[\s,;])(?:titled|called|named|title\s*[:=])\s+",
    re.IGNORECASE,
)

# Opening/closing quotation marks used in natural title syntax.
_QUOTE_CHARS = "\"'“”„‟«»‘’‚‛‹›＂＇"

# Preferred closer(s) for a given opener so inner apostrophes are not cut off.
_QUOTE_CLOSERS = {
    '"': '"”‟',
    "'": "'’‛",
    "“": "”\"",
    "”": "”\"",
    "„": "“”\"",
    "«": "»",
    "‘": "’'",
    "’": "’'",
    "‚": "‘’'",
    "‹": "›",
    "＂": "＂\"",
    "＇": "＇'",
}

# Unquoted titles must not swallow date/time clauses that belong to scheduling.
_TITLE_STOP = re.compile(
    r"\s+(?:"
    r"tomorrow|today|tonight|yesterday|"
    r"next\s+week|this\s+week|next\s+month|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"at\s+\d{1,2}(?::\d{2})?\s*(?:a\.?\s*m\.?|p\.?\s*m\.?)?|"
    r"on\s+\d{1,2}(?:[/-]\d{1,2})?|"
    r"for\s+\d{1,3}\s*-?\s*(?:minutes?|mins?|hours?)"
    r")\b",
    re.IGNORECASE,
)

_DURATION = re.compile(
    r"\b(\d{1,3})\s*-?\s*(?:minutes?|mins?)\b",
    re.IGNORECASE,
)

_DATE_OR_TIME = re.compile(
    r"\b("
    r"tomorrow|today|next week|this week|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"\d{1,2}(:\d{2})?\s*(a\.?\s*m\.?|p\.?\s*m\.?)"
    r")\b",
    re.IGNORECASE,
)

_MAX_CONTINUATION_USER_TURNS = 6


def looks_like_availability(message: str) -> bool:
    """True when the user is asking about free/busy time rather than listing meetings."""
    return bool(_AVAILABILITY.search(message or ""))


def looks_like_list_events(message: str) -> bool:
    """True when the user wants existing meetings listed."""
    return bool(_LIST_EVENTS.search(message or ""))


def looks_like_scheduling(message: str) -> bool:
    """True when the user wants to book/create a meeting or get slot suggestions.

    Continuation-only phrases such as "Just schedule the meeting" are not a
    standalone scheduling spec; they must recover a prior request or clarify.
    """
    if is_scheduling_continuation(message):
        return False
    return bool(_SCHEDULING.search(message or ""))


def looks_like_suggest_slots(message: str) -> bool:
    return bool(_SUGGEST_SLOTS.search(message or ""))


def is_scheduling_continuation(message: str) -> bool:
    """True for short confirmations that should reuse a prior scheduling request."""
    return bool(_CONTINUATION.match((message or "").strip()))


def missing_prior_scheduling_request(
    message: str,
    history: list[dict] | None,
    *,
    max_user_turns: int = _MAX_CONTINUATION_USER_TURNS,
) -> bool:
    """True when the user confirmed scheduling but no prior request can be recovered."""
    if not is_scheduling_continuation(message):
        return False
    return (
        recover_prior_scheduling_request(history, max_user_turns=max_user_turns)
        is None
    )


def extract_meeting_title(message: str) -> str | None:
    """Return an explicit meeting title from the message, or None if not stated.

    Accepts quoted, curly-quoted, unquoted, and accidentally unmatched opening
    quotes after titled/called/named/title. Unquoted remainder is clipped so
    date/time clauses are not consumed as part of the title.
    """
    cleaned = message or ""
    marker = _TITLE_MARKER.search(cleaned)
    if not marker:
        return None
    rest = cleaned[marker.end() :].strip()
    if not rest:
        return None

    quoted, closed = _split_quoted_title(rest)
    candidate = quoted if closed else _clip_unquoted_title(quoted)
    title = " ".join(candidate.split()).strip(" \t.,;:!?-")
    if len(title) < 3:
        return None
    if _TITLE_STOP.match(f" {title}"):
        return None
    return title[:200]


def _split_quoted_title(rest: str) -> tuple[str, bool]:
    """Return (body, closed) when ``rest`` starts with a quotation mark."""
    if not rest or rest[0] not in _QUOTE_CHARS:
        return rest, False
    body = rest[1:]
    closers = _QUOTE_CLOSERS.get(rest[0], _QUOTE_CHARS)
    for index, char in enumerate(body):
        if char in closers:
            return body[:index], True
    return body, False


def _clip_unquoted_title(text: str) -> str:
    """Take title text until an unrelated date/time clause or end of message."""
    match = _TITLE_STOP.search(text)
    clipped = text[: match.start()] if match else text
    return clipped.strip()


def parse_duration_minutes(message: str, default: int) -> int:
    match = _DURATION.search(message or "")
    if match:
        return max(15, min(480, int(match.group(1))))
    return int(default)


def _has_recoverable_scheduling_details(message: str) -> bool:
    if not looks_like_scheduling(message):
        return False
    return bool(
        extract_meeting_title(message)
        or _DATE_OR_TIME.search(message)
        or _DURATION.search(message)
    )


def recover_prior_scheduling_request(
    history: list[dict] | None,
    *,
    max_user_turns: int = _MAX_CONTINUATION_USER_TURNS,
) -> str | None:
    """Return the most recent same-conversation user scheduling request, if any.

    Only user turns are considered. Assistant text is ignored so the model cannot
    invent fields. Returns None when no recoverable prior request exists.
    """
    if not history:
        return None
    user_turns: list[str] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("role") or "").lower() != "user":
            continue
        content = str(entry.get("content") or "").strip()
        if content:
            user_turns.append(content)
    bound = max(1, min(max_user_turns, _MAX_CONTINUATION_USER_TURNS))
    for content in reversed(user_turns[-bound:]):
        if is_scheduling_continuation(content):
            continue
        if _has_recoverable_scheduling_details(content):
            return content
    return None


def resolve_calendar_source_message(
    message: str,
    history: list[dict] | None = None,
    *,
    max_user_turns: int = _MAX_CONTINUATION_USER_TURNS,
) -> str:
    """Use the current message, or a prior scheduling request for a clear continuation."""
    current = (message or "").strip()
    if not is_scheduling_continuation(current):
        return current
    recovered = recover_prior_scheduling_request(
        history, max_user_turns=max_user_turns
    )
    return recovered or current


__all__ = [
    "extract_meeting_title",
    "is_scheduling_continuation",
    "looks_like_availability",
    "looks_like_list_events",
    "looks_like_scheduling",
    "looks_like_suggest_slots",
    "missing_prior_scheduling_request",
    "parse_duration_minutes",
    "recover_prior_scheduling_request",
    "resolve_calendar_source_message",
]
