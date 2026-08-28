"""KnowledgeBase 数据访问层（user_id 强制隔离 + 软删）。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase


class KnowledgeBaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, name: str, description: str | None) -> KnowledgeBase:
        kb = KnowledgeBase(user_id=user_id, name=name, description=description)
        self.db.add(kb)
        await self.db.flush()
        return kb

    async def get_by_id(self, user_id: int, kb_id: int) -> KnowledgeBase | None:
        result = await self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.user_id == user_id,
                KnowledgeBase.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> list[KnowledgeBase]:
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.user_id == user_id, KnowledgeBase.deleted_at.is_(None))
            .order_by(KnowledgeBase.updated_at.desc())
        )
        return list(result.scalars().all())

    async def update(
        self, user_id: int, kb_id: int, name: str, description: str | None
    ) -> KnowledgeBase | None:
        kb = await self.get_by_id(user_id, kb_id)
        if kb is None:
            return None
        kb.name = name
        kb.description = description
        kb.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return kb

    async def soft_delete(self, user_id: int, kb_id: int) -> bool:
        kb = await self.get_by_id(user_id, kb_id)
        if kb is None:
            return False
        kb.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
