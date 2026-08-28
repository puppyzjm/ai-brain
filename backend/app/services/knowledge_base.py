"""知识库业务逻辑。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.knowledge_base import KnowledgeBase
from app.repositories.knowledge_base import KnowledgeBaseRepository


async def create_kb(
    db: AsyncSession, user_id: int, name: str, description: str | None
) -> KnowledgeBase:
    kb = await KnowledgeBaseRepository(db).create(user_id, name, description)
    await db.commit()
    await db.refresh(kb)
    return kb


async def list_kbs(db: AsyncSession, user_id: int) -> list[KnowledgeBase]:
    return await KnowledgeBaseRepository(db).list_by_user(user_id)


async def update_kb(
    db: AsyncSession, user_id: int, kb_id: int, name: str, description: str | None
) -> KnowledgeBase:
    kb = await KnowledgeBaseRepository(db).update(user_id, kb_id, name, description)
    if kb is None:
        raise NotFoundError("知识库不存在")
    await db.commit()
    await db.refresh(kb)
    return kb


async def delete_kb(db: AsyncSession, user_id: int, kb_id: int) -> None:
    ok = await KnowledgeBaseRepository(db).soft_delete(user_id, kb_id)
    if not ok:
        raise NotFoundError("知识库不存在")
    await db.commit()
