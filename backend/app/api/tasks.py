"""任务管理接口。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.response import ok
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services import task as task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tasks = await task_service.list_tasks(db, current_user.id, status, priority)
    data = [TaskResponse.model_validate(t).model_dump(mode="json") for t in tasks]
    return ok(data)


@router.post("")
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.create_task(
        db,
        current_user.id,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        due_date=body.due_date,
    )
    return ok(TaskResponse.model_validate(task).model_dump(mode="json"))


@router.patch("/{task_id}")
async def update_task(
    task_id: int,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fields = body.model_dump(exclude_none=True)
    task = await task_service.update_task(db, current_user.id, task_id, **fields)
    return ok(TaskResponse.model_validate(task).model_dump(mode="json"))


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await task_service.delete_task(db, current_user.id, task_id)
    return ok(None)
