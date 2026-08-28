"""Message 数据访问层。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
        model: str | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            model=model,
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def list_by_conversation(self, user_id: int, conversation_id: int) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.user_id == user_id,
            )
            .order_by(Message.id.asc())
        )
        return list(result.scalars().all())
