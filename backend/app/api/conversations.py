"""会话管理接口：新建 / 列表 / 重命名 / 删除 / 历史消息。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.response import ok
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
)
from app.services import conversation as conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convs = await conversation_service.list_conversations(db, current_user.id)
    data = [ConversationResponse.model_validate(c).model_dump(mode="json") for c in convs]
    return ok(data)


@router.post("")
async def create_conversation(
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await conversation_service.create_conversation(db, current_user.id, body.title)
    return ok(ConversationResponse.model_validate(conv).model_dump(mode="json"))


@router.patch("/{conversation_id}")
async def rename_conversation(
    conversation_id: int,
    body: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await conversation_service.rename_conversation(
        db, current_user.id, conversation_id, body.title
    )
    return ok(ConversationResponse.model_validate(conv).model_dump(mode="json"))


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await conversation_service.delete_conversation(db, current_user.id, conversation_id)
    return ok(None)


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    messages = await conversation_service.get_messages(db, current_user.id, conversation_id)
    data = [MessageResponse.model_validate(m).model_dump(mode="json") for m in messages]
    return ok(data)
