"""会话业务逻辑。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository


async def create_conversation(db: AsyncSession, user_id: int, title: str = "新对话") -> Conversation:
    conv = await ConversationRepository(db).create(user_id, title)
    await db.commit()
    await db.refresh(conv)
    return conv


async def list_conversations(db: AsyncSession, user_id: int) -> list[Conversation]:
    return await ConversationRepository(db).list_by_user(user_id)


async def rename_conversation(
    db: AsyncSession, user_id: int, conversation_id: int, title: str
) -> Conversation:
    conv = await ConversationRepository(db).rename(user_id, conversation_id, title)
    if conv is None:
        raise NotFoundError("会话不存在")
    await db.commit()
    await db.refresh(conv)
    return conv


async def delete_conversation(db: AsyncSession, user_id: int, conversation_id: int) -> None:
    ok = await ConversationRepository(db).soft_delete(user_id, conversation_id)
    if not ok:
        raise NotFoundError("会话不存在")
    await db.commit()


async def get_messages(
    db: AsyncSession, user_id: int, conversation_id: int
) -> list[Message]:
    conv = await ConversationRepository(db).get_by_id(user_id, conversation_id)
    if conv is None:
        raise NotFoundError("会话不存在")
    return await MessageRepository(db).list_by_conversation(user_id, conversation_id)
