"""Agent-facing memory helpers: explicit persist heuristics for durable facts.

Only stores preferences / confirmed facts when the user states them clearly.
Never stores secrets, temporary errors, or unconfirmed model assumptions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.errors import ValidationError
from onepilot.core.logging import get_logger
from onepilot.security.auth import Principal
from onepilot.services import memory_service

logger = get_logger(__name__)

# Explicit remember / preference patterns (user-authored durable facts only).
_REMEMBER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bremember\s+that\s+(.+)$",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bplease\s+remember\s+(.+)$",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bmy\s+preference\s+is\s+(.+)$",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bi\s+prefer\s+(.+)$",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\balways\s+use\s+(.+)$",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bfrom\s+now\s+on[, ]+(.+)$",
        re.IGNORECASE | re.DOTALL,
    ),
)


@dataclass(slots=True, frozen=True)
class MemoryCandidate:
    key: str
    value: str
    scope: str = "user"


def _slugify_key(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return (slug[:80] or "preference")[:80]


def extract_explicit_memory_candidates(message: str) -> list[MemoryCandidate]:
    """Extract durable memory candidates from an explicit user instruction."""
    text = (message or "").strip()
    if not text or len(text) > 2000:
        return []

    candidates: list[MemoryCandidate] = []
    for pattern in _REMEMBER_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = match.group(1).strip().strip("\"'")
        value = re.sub(r"\s+", " ", value)
        if len(value) < 3:
            continue
        # Prefer a short preference key when the value is long.
        key_seed = value if len(value) <= 40 else value[:40]
        key = f"pref_{_slugify_key(key_seed)}"
        candidates.append(MemoryCandidate(key=key, value=value, scope="user"))
        break  # one durable fact per turn is enough

    return candidates


def maybe_persist_from_user_message(
    session: Session,
    *,
    principal: Principal,
    settings: Settings,
    message: str,
) -> int:
    """Persist explicit durable facts from the user message. Returns write count."""
    enabled, reason = memory_service.agent_memory_enabled(
        session, principal=principal, settings=settings
    )
    if not enabled:
        logger.info(
            "memory_persist_skipped",
            organization_id=principal.organization_id,
            reason=reason,
        )
        return 0

    written = 0
    for candidate in extract_explicit_memory_candidates(message):
        try:
            memory_service.write_memory(
                session,
                principal=principal,
                scope=candidate.scope,
                key=candidate.key,
                value=candidate.value,
                settings=settings,
            )
            written += 1
            logger.info(
                "memory_persisted",
                organization_id=principal.organization_id,
                scope=candidate.scope,
                key=candidate.key,
            )
        except ValidationError:
            logger.info(
                "memory_persist_rejected",
                organization_id=principal.organization_id,
                key=candidate.key,
            )
        except Exception:
            logger.exception(
                "memory_persist_failed",
                organization_id=principal.organization_id,
            )
    return written
