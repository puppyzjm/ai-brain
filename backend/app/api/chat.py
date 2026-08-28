"""AI Chat SSE 接口（普通对话 / RAG 问答）。"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services import chat as chat_service
from app.services import rag as rag_service

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """多轮对话 / RAG 问答 + SSE 流式输出。

    knowledge_base_ids 为空 → 普通对话；非空 → RAG（检索 → Context → DeepSeek）。
    """
    # RAG 模式：预校验知识库归属（SSE 生成器内无法返回常规 HTTP 错误码）
    if body.knowledge_base_ids:
        await rag_service.validate_kb_access(db, current_user.id, body.knowledge_base_ids)

    async def event_stream():
        async for event in chat_service.stream_chat(
            db, current_user.id, body.conversation_id, body.content, body.knowledge_base_ids
        ):
            yield _sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
