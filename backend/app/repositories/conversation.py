"""Conversation 数据访问层（铁律：所有查询强制 user_id 过滤 + 软删过滤）。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, title: str) -> Conversation:
        conv = Conversation(user_id=user_id, title=title)
        self.db.add(conv)
        await self.db.flush()
        return conv

    async def get_by_id(self, user_id: int, conversation_id: int) -> Conversation | None:
        """铁律：WHERE id = ? AND user_id = ? 且未软删。"""
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def rename(self, user_id: int, conversation_id: int, title: str) -> Conversation | None:
        conv = await self.get_by_id(user_id, conversation_id)
        if conv is None:
            return None
        conv.title = title
        conv.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return conv

    async def soft_delete(self, user_id: int, conversation_id: int) -> bool:
        conv = await self.get_by_id(user_id, conversation_id)
        if conv is None:
            return False
        conv.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def touch(self, user_id: int, conversation_id: int) -> None:
        """有新消息时刷新 updated_at。"""
        conv = await self.get_by_id(user_id, conversation_id)
        if conv is not None:
            conv.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
