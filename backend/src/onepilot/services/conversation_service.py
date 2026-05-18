"""Conversation persistence service.

Stores user/assistant turns in Postgres scoped by ``organization_id`` and
``user_id``. The agent uses ``recent_history`` to fetch the last N messages for
contextual continuity.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from onepilot.core.errors import NotFoundError
from onepilot.core.ids import new_id
from onepilot.core.logging import get_logger
from onepilot.repositories.conversations import ConversationRepository, MessageRepository
from onepilot.repositories.models import Conversation, Message

logger = get_logger(__name__)

DEFAULT_HISTORY_TURNS = 10
MAX_HISTORY_TURNS = 50


def get_or_create_conversation(
    session: Session,
    *,
    organization_id: str,
    user_id: str,
    conversation_id: str | None,
    title_hint: str | None = None,
) -> Conversation:
    repo = ConversationRepository(session)
    if conversation_id:
        existing = repo.get(conversation_id, organization_id=organization_id)
        if existing is None:
            raise NotFoundError(f"Conversation '{conversation_id}' not found")
        if existing.user_id != user_id:
            raise NotFoundError(f"Conversation '{conversation_id}' not found")
        return existing

    title = (title_hint or "New conversation").strip()[:255] or "New conversation"
    conversation = Conversation(
        id=new_id("conv"),
        organization_id=organization_id,
        user_id=user_id,
        title=title,
        last_message_at=datetime.now(UTC),
    )
    repo.create(conversation)
    return conversation


def append_message(
    session: Session,
    *,
    conversation: Conversation,
    role: str,
    content: str,
    user_id: str | None,
    intent: str | None = None,
    confidence: float = 0.0,
    citations: Iterable[dict] | None = None,
    tool_calls: Iterable[dict] | None = None,
    metadata: dict | None = None,
) -> Message:
    msg = Message(
        id=new_id("msg"),
        organization_id=conversation.organization_id,
        conversation_id=conversation.id,
        user_id=user_id,
        role=role,
        content=content,
        intent=intent,
        confidence=confidence,
        citations=list(citations or []),
        tool_calls=list(tool_calls or []),
        msg_metadata=metadata or {},
    )
    repo = MessageRepository(session)
    repo.create(msg)

    conversation.last_message_at = datetime.now(UTC)
    if intent:
        conversation.last_intent = intent
    session.flush()
    return msg


def recent_history(
    session: Session,
    *,
    organization_id: str,
    conversation_id: str,
    limit: int = DEFAULT_HISTORY_TURNS,
) -> list[dict]:
    """Return last ``limit`` messages as plain dicts for prompt construction."""
    limit = max(0, min(limit, MAX_HISTORY_TURNS))
    repo = MessageRepository(session)
    rows = repo.last_n_turns(
        conversation_id,
        organization_id=organization_id,
        n=limit,
    )
    return [
        {
            "role": row.role,
            "content": row.content,
            "intent": row.intent,
        }
        for row in rows
    ]


def list_conversations(
    session: Session,
    *,
    organization_id: str,
    user_id: str,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Conversation], int]:
    repo = ConversationRepository(session)
    items = repo.list_for_user(
        organization_id, user_id, offset=offset, limit=min(limit, 100)
    )
    total = repo.count(organization_id=organization_id)
    return items, total


def get_conversation_with_messages(
    session: Session,
    *,
    organization_id: str,
    user_id: str,
    conversation_id: str,
) -> tuple[Conversation, list[Message]]:
    conv_repo = ConversationRepository(session)
    conv = conv_repo.get(conversation_id, organization_id=organization_id)
    if conv is None or conv.user_id != user_id:
        raise NotFoundError(f"Conversation '{conversation_id}' not found")
    msg_repo = MessageRepository(session)
    msgs = msg_repo.list_for_conversation(
        conversation_id, organization_id=organization_id
    )
    return conv, msgs
