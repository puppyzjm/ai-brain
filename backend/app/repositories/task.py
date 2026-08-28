"""Task 数据访问层（user_id 强制隔离 + 软删）。"""
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        title: str,
        description: str | None,
        status: str,
        priority: str,
        due_date: date | None,
    ) -> Task:
        task = Task(
            user_id=user_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            due_date=due_date,
        )
        self.db.add(task)
        await self.db.flush()
        return task

    async def get_by_id(self, user_id: int, task_id: int) -> Task | None:
        result = await self.db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: int,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[Task]:
        stmt = select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        stmt = stmt.order_by(Task.id.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, user_id: int, task_id: int, **fields) -> Task | None:
        task = await self.get_by_id(user_id, task_id)
        if task is None:
            return None
        for key, value in fields.items():
            if hasattr(task, key):
                setattr(task, key, value)
        task.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return task

    async def soft_delete(self, user_id: int, task_id: int) -> bool:
        task = await self.get_by_id(user_id, task_id)
        if task is None:
            return False
        task.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
