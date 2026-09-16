"""Persistent conversation memory with deterministic keyword recall."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jarvis.database.session import StoredMessage
from jarvis.models.contracts import ChatMessage


class MemoryManager:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, conversation_id: UUID, message: ChatMessage, importance: int = 1) -> None:
        async with self._sessions() as session:
            session.add(
                StoredMessage(
                    conversation_id=str(conversation_id),
                    role=message.role,
                    content=message.content,
                    importance=importance,
                )
            )
            await session.commit()

    async def recall(self, conversation_id: UUID, limit: int = 20) -> list[ChatMessage]:
        async with self._sessions() as session:
            query = (
                select(StoredMessage)
                .where(StoredMessage.conversation_id == str(conversation_id))
                .order_by(StoredMessage.created_at.desc())
                .limit(limit)
            )
            rows = list((await session.scalars(query)).all())
        return [
            ChatMessage(role=row.role, content=row.content, created_at=row.created_at)
            for row in reversed(rows)
        ]

    async def search(self, conversation_id: UUID, query: str, limit: int = 10) -> list[ChatMessage]:
        async with self._sessions() as session:
            statement = (
                select(StoredMessage)
                .where(
                    StoredMessage.conversation_id == str(conversation_id),
                    StoredMessage.content.ilike(f"%{query}%"),
                )
                .limit(limit)
            )
            rows = list((await session.scalars(statement)).all())
        return [
            ChatMessage(role=row.role, content=row.content, created_at=row.created_at)
            for row in rows
        ]

    async def forget(self, conversation_id: UUID) -> None:
        async with self._sessions() as session:
            await session.execute(
                delete(StoredMessage).where(StoredMessage.conversation_id == str(conversation_id))
            )
            await session.commit()
