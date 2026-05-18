"""Repositories for conversations and messages."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import Conversation, Message


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Conversation)

    def list_for_user(
        self,
        organization_id: str,
        user_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(
                Conversation.organization_id == organization_id,
                Conversation.user_id == user_id,
            )
            .order_by(Conversation.last_message_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Message)

    def list_for_conversation(
        self,
        conversation_id: str,
        *,
        organization_id: str,
        limit: int | None = None,
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.organization_id == organization_id,
            )
            .order_by(Message.created_at.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def last_n_turns(
        self,
        conversation_id: str,
        *,
        organization_id: str,
        n: int,
    ) -> list[Message]:
        """Return the most recent ``n`` messages in chronological order."""
        if n <= 0:
            return []
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.organization_id == organization_id,
            )
            .order_by(Message.created_at.desc())
            .limit(n)
        )
        rows = list(self._session.execute(stmt).scalars().all())
        rows.reverse()
        return rows

    def count_for_conversation(
        self, conversation_id: str, *, organization_id: str
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.organization_id == organization_id,
            )
        )
        return self._session.execute(stmt).scalar() or 0
