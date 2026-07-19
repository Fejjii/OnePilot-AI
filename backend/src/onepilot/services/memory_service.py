"""Persistent memory service for agent state.

Stores tenant-scoped key/value pairs that the agent (or user) can read across
conversations. Memory is always scoped by ``organization_id``; ``user_id`` is
optional for org-wide scopes. Each item supports a TTL.

Agent recall uses only ``user`` / ``agent`` scopes for the calling principal so
memories never cross users. Organization-scoped rows remain available via the
HTTP API for explicit admin/product facts but are not auto-injected into chat.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.errors import NotFoundError, ValidationError
from onepilot.core.ids import new_id
from onepilot.core.logging import get_logger
from onepilot.repositories.memory import MemoryItemRepository
from onepilot.repositories.models import MemoryItem
from onepilot.security.auth import Principal

logger = get_logger(__name__)

VALID_SCOPES: frozenset[str] = frozenset({"user", "organization", "agent"})
AGENT_CONTEXT_SCOPES: tuple[str, ...] = ("user", "agent")
MEMORY_DISABLED_KEY = "__memory_disabled"
RESERVED_KEYS: frozenset[str] = frozenset({MEMORY_DISABLED_KEY})

_SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|credential|private[_-]?key)",
    re.IGNORECASE,
)
_SENSITIVE_VALUE_RE = re.compile(
    r"("
    r"Bearer\s+[A-Za-z0-9\-._~+/]+=*"
    r"|sk-[A-Za-z0-9]{20,}"
    r"|pk_[A-Za-z0-9]{20,}"
    r"|-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"
    r"|\bpassword\s*[:=]\s*\S+"
    r"|\bapi[_-]?key\s*[:=]\s*\S+"
    r")",
    re.IGNORECASE,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _resolve_user_id(principal: Principal, scope: str) -> str | None:
    if scope == "organization":
        return None
    return principal.user_id


def is_shared_demo_principal(principal: Principal, settings: Settings) -> bool:
    """True when the principal is the shared public-demo tenant identity."""
    return (
        principal.organization_id == settings.DEV_ORG_ID
        and principal.user_id == settings.DEV_USER_ID
    )


def contains_sensitive_content(*, key: str, value: str) -> bool:
    """Return True when key/value look like credentials or secrets."""
    if _SENSITIVE_KEY_RE.search(key or ""):
        return True
    if _SENSITIVE_VALUE_RE.search(value or ""):
        return True
    return False


def write_memory(
    session: Session,
    *,
    principal: Principal,
    scope: str,
    key: str,
    value: str,
    ttl_seconds: int | None = None,
    settings: Settings | None = None,
    allow_reserved: bool = False,
) -> MemoryItem:
    if scope not in VALID_SCOPES:
        raise ValidationError(f"Invalid memory scope '{scope}'")
    if not key or not key.strip():
        raise ValidationError("Memory key is required")

    cleaned_key = key.strip()[:255]
    if not allow_reserved and cleaned_key in RESERVED_KEYS:
        raise ValidationError(f"Memory key '{cleaned_key}' is reserved")
    if not value or not str(value).strip():
        raise ValidationError("Memory value is required")

    cleaned_value = str(value).strip()
    max_chars = 500
    if settings is not None:
        max_chars = max(1, settings.AGENT_MEMORY_VALUE_MAX_CHARS)
    if len(cleaned_value) > max_chars:
        raise ValidationError(f"Memory value exceeds {max_chars} characters")

    if contains_sensitive_content(key=cleaned_key, value=cleaned_value):
        raise ValidationError(
            "Memory cannot store passwords, tokens, API keys, or other secrets"
        )

    user_id = _resolve_user_id(principal, scope)
    repo = MemoryItemRepository(session)
    existing = repo.get_by_key(
        principal.organization_id, scope=scope, key=cleaned_key, user_id=user_id
    )

    expires_at = (
        _now() + timedelta(seconds=ttl_seconds) if ttl_seconds and ttl_seconds > 0 else None
    )

    if existing is not None:
        existing.value = cleaned_value
        existing.ttl_seconds = ttl_seconds
        existing.expires_at = expires_at
        session.flush()
        return existing

    item = MemoryItem(
        id=new_id("mem"),
        organization_id=principal.organization_id,
        user_id=user_id,
        scope=scope,
        key=cleaned_key,
        value=cleaned_value,
        ttl_seconds=ttl_seconds,
        expires_at=expires_at,
    )
    repo.create(item)
    logger.info(
        "memory_written",
        organization_id=principal.organization_id,
        scope=scope,
        key=item.key,
    )
    return item


def read_memory(
    session: Session,
    *,
    principal: Principal,
    scope: str,
    key: str,
) -> MemoryItem | None:
    if scope not in VALID_SCOPES:
        raise ValidationError(f"Invalid memory scope '{scope}'")
    user_id = _resolve_user_id(principal, scope)
    repo = MemoryItemRepository(session)
    item = repo.get_by_key(
        principal.organization_id, scope=scope, key=key, user_id=user_id
    )
    if item is None:
        return None
    if item.expires_at and item.expires_at <= _now():
        repo.delete(item)
        return None
    return item


def delete_memory(
    session: Session,
    *,
    principal: Principal,
    scope: str,
    key: str,
) -> None:
    if scope not in VALID_SCOPES:
        raise ValidationError(f"Invalid memory scope '{scope}'")
    user_id = _resolve_user_id(principal, scope)
    repo = MemoryItemRepository(session)
    item = repo.get_by_key(
        principal.organization_id, scope=scope, key=key, user_id=user_id
    )
    if item is None:
        raise NotFoundError(f"Memory item '{key}' not found")
    repo.delete(item)
    logger.info(
        "memory_deleted",
        organization_id=principal.organization_id,
        scope=scope,
        key=key,
    )


def clear_user_memory(
    session: Session,
    *,
    principal: Principal,
    scopes: list[str] | None = None,
) -> int:
    """Delete all user-owned memories (default: user + agent scopes)."""
    repo = MemoryItemRepository(session)
    deleted = repo.delete_for_user(
        principal.organization_id,
        user_id=principal.user_id,
        scopes=scopes or list(AGENT_CONTEXT_SCOPES),
    )
    logger.info(
        "memory_cleared",
        organization_id=principal.organization_id,
        deleted_count=deleted,
    )
    return deleted


def list_memory(
    session: Session,
    *,
    principal: Principal,
    scope: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[MemoryItem], int]:
    repo = MemoryItemRepository(session)
    repo.delete_expired(principal.organization_id)
    user_id = _resolve_user_id(principal, scope or "user") if scope else principal.user_id
    items = repo.list_for_scope(
        principal.organization_id,
        scope=scope,
        user_id=user_id,
        offset=offset,
        limit=min(limit, 200),
    )
    # Hide reserved control keys from the default list UI.
    visible = [i for i in items if i.key not in RESERVED_KEYS]
    return visible, len(visible)


def set_memory_disabled(
    session: Session,
    *,
    principal: Principal,
    disabled: bool,
    settings: Settings | None = None,
) -> MemoryItem:
    return write_memory(
        session,
        principal=principal,
        scope="user",
        key=MEMORY_DISABLED_KEY,
        value="true" if disabled else "false",
        settings=settings,
        allow_reserved=True,
    )


def is_memory_disabled(session: Session, *, principal: Principal) -> bool:
    item = read_memory(
        session, principal=principal, scope="user", key=MEMORY_DISABLED_KEY
    )
    if item is None:
        return False
    return item.value.strip().lower() in {"1", "true", "yes", "on"}


def agent_memory_enabled(
    session: Session,
    *,
    principal: Principal,
    settings: Settings,
) -> tuple[bool, str]:
    """Whether the agent may recall/persist memory for this principal.

    Returns ``(enabled, reason)`` where reason is for safe observability only.
    """
    if not settings.AGENT_MEMORY_ENABLED:
        return False, "globally_disabled"
    if is_shared_demo_principal(principal, settings):
        return False, "shared_demo_tenant"
    try:
        if is_memory_disabled(session, principal=principal):
            return False, "user_disabled"
    except Exception:
        logger.exception(
            "memory_preference_check_failed",
            organization_id=principal.organization_id,
        )
        return False, "preference_check_failed"
    return True, "enabled"


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]{3,}", text.lower()) if t}


def score_memory_relevance(query: str, *, key: str, value: str) -> float:
    """Simple token-overlap score in [0, 1]. Unrelated items score 0."""
    q = _tokenize(query)
    if not q:
        return 0.0
    doc = _tokenize(f"{key} {value}")
    if not doc:
        return 0.0
    overlap = q & doc
    if not overlap:
        return 0.0
    return len(overlap) / max(len(q), 1)


def retrieve_relevant_memory(
    session: Session,
    *,
    principal: Principal,
    query: str,
    settings: Settings,
    max_items: int | None = None,
    max_chars: int | None = None,
) -> list[MemoryItem]:
    """Return bounded, relevant user/agent memories. Fail-safe → empty list."""
    try:
        enabled, reason = agent_memory_enabled(
            session, principal=principal, settings=settings
        )
        if not enabled:
            logger.info(
                "memory_recall_skipped",
                organization_id=principal.organization_id,
                reason=reason,
            )
            return []

        repo = MemoryItemRepository(session)
        repo.delete_expired(principal.organization_id)
        candidates = repo.list_for_agent_context(
            principal.organization_id,
            user_id=principal.user_id,
            scopes=list(AGENT_CONTEXT_SCOPES),
            limit=50,
        )
        # Exclude control keys from prompt injection.
        candidates = [c for c in candidates if c.key not in RESERVED_KEYS]

        scored: list[tuple[float, MemoryItem]] = []
        for item in candidates:
            score = score_memory_relevance(query, key=item.key, value=item.value)
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1].updated_at))

        limit = max_items if max_items is not None else settings.AGENT_MEMORY_MAX_ITEMS
        char_budget = (
            max_chars if max_chars is not None else settings.AGENT_MEMORY_MAX_CHARS
        )
        selected: list[MemoryItem] = []
        used = 0
        for _score, item in scored:
            piece = len(item.key) + len(item.value) + 8
            if selected and used + piece > char_budget:
                break
            selected.append(item)
            used += piece
            if len(selected) >= max(1, limit):
                break

        logger.info(
            "memory_recalled",
            organization_id=principal.organization_id,
            candidate_count=len(candidates),
            selected_count=len(selected),
            char_count=used,
        )
        return selected
    except Exception:
        logger.exception(
            "memory_recall_failed",
            organization_id=principal.organization_id,
        )
        return []


def format_memory_block(items: list[MemoryItem]) -> str:
    """Format memories for the LLM, clearly separated from the user message."""
    if not items:
        return ""
    lines = [
        "Stored memory (prior durable facts about this user/organization — "
        "not part of the current user message):",
    ]
    for item in items:
        lines.append(f"- [{item.scope}] {item.key}: {item.value}")
    lines.append(
        "Use these only when relevant. Prefer the current user message if it conflicts."
    )
    return "\n".join(lines)


def memory_status(
    session: Session,
    *,
    principal: Principal,
    settings: Settings,
) -> dict[str, object]:
    enabled, reason = agent_memory_enabled(
        session, principal=principal, settings=settings
    )
    try:
        items, total = list_memory(session, principal=principal, limit=200)
    except Exception:
        items, total = [], 0
    return {
        "agent_memory_enabled": enabled,
        "reason": reason,
        "user_disabled": reason == "user_disabled",
        "shared_demo_tenant": reason == "shared_demo_tenant",
        "item_count": total,
        "max_items": settings.AGENT_MEMORY_MAX_ITEMS,
        "max_chars": settings.AGENT_MEMORY_MAX_CHARS,
    }
