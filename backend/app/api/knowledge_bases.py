"""知识库管理接口。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.response import ok
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from app.services import knowledge_base as kb_service

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.get("")
async def list_kbs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kbs = await kb_service.list_kbs(db, current_user.id)
    data = [KnowledgeBaseResponse.model_validate(k).model_dump(mode="json") for k in kbs]
    return ok(data)


@router.post("")
async def create_kb(
    body: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await kb_service.create_kb(db, current_user.id, body.name, body.description)
    return ok(KnowledgeBaseResponse.model_validate(kb).model_dump(mode="json"))


@router.patch("/{kb_id}")
async def update_kb(
    kb_id: int,
    body: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb = await kb_service.update_kb(db, current_user.id, kb_id, body.name, body.description)
    return ok(KnowledgeBaseResponse.model_validate(kb).model_dump(mode="json"))


@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await kb_service.delete_kb(db, current_user.id, kb_id)
    return ok(None)
