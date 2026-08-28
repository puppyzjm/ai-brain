"""任务业务逻辑（AI 工具与 REST API 共用同一入口）。"""
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.task import Task
from app.repositories.task import TaskRepository


async def create_task(
    db: AsyncSession,
    user_id: int,
    title: str,
    description: str | None = None,
    status: str = "todo",
    priority: str = "medium",
    due_date: date | None = None,
) -> Task:
    task = await TaskRepository(db).create(
        user_id, title, description, status, priority, due_date
    )
    await db.commit()
    await db.refresh(task)
    return task


async def list_tasks(
    db: AsyncSession,
    user_id: int,
    status: str | None = None,
    priority: str | None = None,
) -> list[Task]:
    return await TaskRepository(db).list_by_user(user_id, status, priority)


async def update_task(db: AsyncSession, user_id: int, task_id: int, **fields) -> Task:
    task = await TaskRepository(db).update(user_id, task_id, **fields)
    if task is None:
        raise NotFoundError("任务不存在")
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, user_id: int, task_id: int) -> None:
    ok = await TaskRepository(db).soft_delete(user_id, task_id)
    if not ok:
        raise NotFoundError("任务不存在")
    await db.commit()
