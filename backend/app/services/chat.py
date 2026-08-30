"""对话核心逻辑：Agent 多轮工具调用 / RAG 问答 / 多模态视觉问答 / 普通多轮对话 → SSE 流式。"""
import asyncio
import base64
import json
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.base import AgentContext
from app.agent.registry import registry
from app.ai.factory import get_llm_provider, get_vision_provider
from app.core.exceptions import AppException, NotFoundError
from app.infrastructure.storage import EXT_TO_IMAGE_MIME, resolve_chat_image_path
from app.models.conversation import Conversation
from app.models.message import Message
from app.rag.context import build_context
from app.rag.prompts import NO_RELEVANT_CONTENT_REPLY, build_rag_messages
from app.repositories.agent_tool_call import AgentToolCallRepository
from app.repositories.ai_usage_log import AiUsageLogRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services import rag as rag_service

# 组装给 LLM 的最近消息条数（普通对话模式）
HISTORY_LIMIT = 20
# Agent 循环控制（TDD：最大轮数硬限制，工具失败修正限次）
MAX_AGENT_ROUNDS = 5
MAX_TOOL_FAILURES = 3


def _build_llm_messages(history: list[Message], content: str) -> list[dict]:
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": content})
    return messages


async def _prepare_conversation(
    db: AsyncSession, user_id: int, conversation_id: int | None
) -> tuple[Conversation, list[Message]]:
    """获取（或新建）会话，返回会话与历史消息。"""
    repo = ConversationRepository(db)
    if conversation_id is not None:
        conv = await repo.get_by_id(user_id, conversation_id)
        if conv is None:
            raise NotFoundError("会话不存在")
    else:
        conv = await repo.create(user_id, "新对话")

    history = await MessageRepository(db).list_by_conversation(user_id, conv.id)
    return conv, history[-HISTORY_LIMIT:]


async def stream_chat(
    db: AsyncSession,
    user_id: int,
    conversation_id: int | None,
    content: str,
    knowledge_base_ids: list[int] | None = None,
    images: list[str] | None = None,
) -> AsyncIterator[dict]:
    """对话主流程，逐事件 yield SSE 事件字典。

    事件：{"type":"delta","content":...} / {"type":"sources","sources":[...]}
         / {"type":"tool","name":...,"status":...} / {"type":"done",...} / {"type":"error",...}

    - 图片模式（images 非空，仅普通对话）：视觉模型直答（不带工具，不检索）。
    - RAG 模式（knowledge_base_ids 非空）：检索 → Context → DeepSeek（不带工具，Phase 5 行为）。
    - 普通模式：Agent 循环，自动携带 5 个工具定义，模型自主决定是否调用。
    """
    try:
        provider = get_llm_provider()
    except AppException as exc:
        yield {"type": "error", "message": exc.message}
        yield {"type": "done", "conversation_id": None, "message_id": None, "usage": None}
        return

    msg_repo = MessageRepository(db)
    conv_repo = ConversationRepository(db)
    usage_repo = AiUsageLogRepository(db)

    conv, history = await _prepare_conversation(db, user_id, conversation_id)

    # 保存用户消息；新会话以首条消息作为标题
    title_content = content.strip() or ("[图片]" if images else "新对话")
    await msg_repo.create(conv.id, user_id, "user", content, images=images)
    if conv.title == "新对话":
        conv.title = title_content[:30] or "新对话"
    conv.updated_at = datetime.now(timezone.utc)
    await db.commit()

    is_rag = bool(knowledge_base_ids)

    if images:
        if is_rag:
            yield {"type": "error", "message": "RAG 知识库问答暂不支持图片，请使用普通对话"}
            yield {
                "type": "done",
                "conversation_id": conv.id,
                "message_id": None,
                "usage": None,
            }
            return
        async for event in _vision_chat(db, provider, user_id, conv, content, images):
            yield event
    elif is_rag:
        async for event in _rag_chat(db, provider, user_id, conv, content, knowledge_base_ids):
            yield event
    else:
        async for event in _agent_chat(db, provider, user_id, conv, history, content):
            yield event


# ==================== 多模态视觉分支（图片直答，不带工具/检索） ====================


async def _vision_chat(
    db: AsyncSession,
    provider,
    user_id: int,
    conv: Conversation,
    content: str,
    images: list[str],
) -> AsyncIterator[dict]:
    """视觉模型直答：本轮图片 + 历史文本上下文，流式输出。

    第一版取舍：历史消息中的图片不重发（省 token），仅携带文本上下文。
    """
    msg_repo = MessageRepository(db)
    usage_repo = AiUsageLogRepository(db)

    try:
        vision_provider = get_vision_provider()
    except AppException as exc:
        yield {"type": "error", "message": exc.message}
        yield {
            "type": "done",
            "conversation_id": conv.id,
            "message_id": None,
            "usage": None,
            "error": exc.message,
        }
        return

    # 读取图片 → base64（校验归属与存在性）
    image_parts: list[dict] = []
    try:
        for name in images:
            path = resolve_chat_image_path(user_id, name)
            if path is None:
                raise NotFoundError("图片不存在或已失效，请重新上传")
            ext = Path(name).suffix.lower()
            mime = EXT_TO_IMAGE_MIME.get(ext, "application/octet-stream")
            b64 = base64.b64encode(path.read_bytes()).decode()
            image_parts.append(
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
            )
    except AppException as exc:
        await usage_repo.create(
            user_id, conv.id, "vision", vision_provider.model, 0, 0, 0, "failed", exc.message
        )
        await db.commit()
        yield {"type": "error", "message": exc.message}
        yield {
            "type": "done",
            "conversation_id": conv.id,
            "message_id": None,
            "usage": None,
            "error": exc.message,
        }
        return

    # 历史文本上下文（排除刚保存的本轮消息）+ 本轮 vision 消息
    history = await msg_repo.list_by_conversation(user_id, conv.id)
    messages: list[dict] = [
        {"role": m.role, "content": m.content}
        for m in history[:-1]
        if m.role in ("user", "assistant") and m.content
    ][-HISTORY_LIMIT:]

    text = content.strip() or "请描述这张图片"
    messages.append(
        {"role": "user", "content": [{"type": "text", "text": text}, *image_parts]}
    )

    full_text = ""
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    error_message: str | None = None
    start = time.monotonic()

    try:
        async for chunk in vision_provider.chat_stream(messages):
            if chunk.content:
                full_text += chunk.content
                yield {"type": "delta", "content": chunk.content}
            if chunk.usage:
                usage = chunk.usage
    except asyncio.CancelledError:
        if full_text:
            await msg_repo.create(
                conv.id, user_id, "assistant", full_text, model=vision_provider.model
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            await usage_repo.create(
                user_id, conv.id, "vision", vision_provider.model,
                usage["prompt_tokens"], usage["completion_tokens"], latency_ms, "success", None,
            )
            conv.updated_at = datetime.now(timezone.utc)
            await db.commit()
        raise
    except AppException as exc:
        error_message = exc.message
        yield {"type": "error", "message": exc.message}
    except Exception as exc:
        error_message = str(exc)
        yield {"type": "error", "message": "AI 服务调用失败，请稍后重试"}

    latency_ms = int((time.monotonic() - start) * 1000)
    status = "failed" if error_message else "success"

    await usage_repo.create(
        user_id, conv.id, "vision", vision_provider.model,
        usage["prompt_tokens"], usage["completion_tokens"], latency_ms, status, error_message,
    )

    if status == "success":
        assistant_msg = None
        if full_text:
            assistant_msg = await msg_repo.create(
                conv.id, user_id, "assistant", full_text, model=vision_provider.model
            )
        conv.updated_at = datetime.now(timezone.utc)
        await db.commit()
        yield {
            "type": "done",
            "conversation_id": conv.id,
            "message_id": assistant_msg.id if assistant_msg else None,
            "usage": {
                **usage,
                "total_tokens": usage["prompt_tokens"] + usage["completion_tokens"],
            },
        }
    else:
        await db.commit()
        yield {
            "type": "done",
            "conversation_id": conv.id,
            "message_id": None,
            "usage": None,
            "error": error_message,
        }


# ==================== RAG 分支（Phase 5 行为保持不变）====================


async def _rag_chat(
    db: AsyncSession,
    provider,
    user_id: int,
    conv: Conversation,
    content: str,
    knowledge_base_ids: list[int],
) -> AsyncIterator[dict]:
    msg_repo = MessageRepository(db)
    conv_repo = ConversationRepository(db)
    usage_repo = AiUsageLogRepository(db)

    try:
        chunks = await rag_service.search_knowledge(db, user_id, knowledge_base_ids, content)
    except AppException as exc:
        await usage_repo.create(
            user_id, conv.id, "rag", provider.model, 0, 0, 0, "failed", exc.message
        )
        await db.commit()
        yield {"type": "error", "message": exc.message}
        yield {
            "type": "done",
            "conversation_id": conv.id,
            "message_id": None,
            "usage": None,
            "error": exc.message,
        }
        return

    if not chunks:
        # 诚实原则：检索不足 → 固定话术，不调 LLM
        reply = NO_RELEVANT_CONTENT_REPLY
        assistant_msg = await msg_repo.create(conv.id, user_id, "assistant", reply, model=None)
        await usage_repo.create(
            user_id, conv.id, "rag", provider.model, 0, 0, 0, "success", None
        )
        conv.updated_at = datetime.now(timezone.utc)
        await db.commit()
        yield {"type": "delta", "content": reply}
        yield {"type": "sources", "sources": []}
        yield {
            "type": "done",
            "conversation_id": conv.id,
            "message_id": assistant_msg.id,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
        return

    context_text, sources = build_context(chunks)
    llm_messages = build_rag_messages(context_text, content)

    full_text = ""
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    error_message: str | None = None
    start = time.monotonic()

    try:
        async for chunk in provider.chat_stream(llm_messages):
            if chunk.content:
                full_text += chunk.content
                yield {"type": "delta", "content": chunk.content}
            if chunk.usage:
                usage = chunk.usage
    except asyncio.CancelledError:
        if full_text:
            await msg_repo.create(conv.id, user_id, "assistant", full_text, model=provider.model)
            latency_ms = int((time.monotonic() - start) * 1000)
            await usage_repo.create(
                user_id, conv.id, "rag", provider.model,
                usage["prompt_tokens"], usage["completion_tokens"], latency_ms, "success", None,
            )
            conv.updated_at = datetime.now(timezone.utc)
            await db.commit()
        raise
    except AppException as exc:
        error_message = exc.message
        yield {"type": "error", "message": exc.message}
    except Exception as exc:
        error_message = str(exc)
        yield {"type": "error", "message": "AI 服务调用失败，请稍后重试"}

    latency_ms = int((time.monotonic() - start) * 1000)
    status = "failed" if error_message else "success"

    await usage_repo.create(
        user_id, conv.id, "rag", provider.model,
        usage["prompt_tokens"], usage["completion_tokens"], latency_ms, status, error_message,
    )

    if status == "success":
        assistant_msg = None
        if full_text:
            assistant_msg = await msg_repo.create(
                conv.id, user_id, "assistant", full_text, model=provider.model
            )
        conv.updated_at = datetime.now(timezone.utc)
        await db.commit()
        yield {"type": "sources", "sources": sources or []}
        yield {
            "type": "done",
            "conversation_id": conv.id,
            "message_id": assistant_msg.id if assistant_msg else None,
            "usage": {
                **usage,
                "total_tokens": usage["prompt_tokens"] + usage["completion_tokens"],
            },
        }
    else:
        await db.commit()
        yield {
            "type": "done",
            "conversation_id": conv.id,
            "message_id": None,
            "usage": None,
            "error": error_message,
        }


# ==================== Agent 分支（真实 Tool Calling 循环）====================


async def _agent_chat(
    db: AsyncSession,
    provider,
    user_id: int,
    conv: Conversation,
    history: list[Message],
    content: str,
) -> AsyncIterator[dict]:
    msg_repo = MessageRepository(db)
    conv_repo = ConversationRepository(db)
    usage_repo = AiUsageLogRepository(db)
    tool_call_repo = AgentToolCallRepository(db)
    ctx = AgentContext(user_id=user_id, conversation_id=conv.id, db=db)

    messages = _build_llm_messages(history, content)
    tools = registry.tool_schemas()

    full_text = ""
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    tool_failures = 0
    start = time.monotonic()

    try:
        for _round in range(MAX_AGENT_ROUNDS):
            round_tool_calls: list[dict] = []

            async for chunk in provider.chat_stream(messages, tools=tools):
                if chunk.content:
                    full_text += chunk.content
                    yield {"type": "delta", "content": chunk.content}
                if chunk.usage:
                    total_usage["prompt_tokens"] += chunk.usage["prompt_tokens"]
                    total_usage["completion_tokens"] += chunk.usage["completion_tokens"]
                if chunk.tool_calls:
                    round_tool_calls = chunk.tool_calls

            if not round_tool_calls:
                break  # 模型不再调用工具：最终回答已流式输出完毕

            # 回填 assistant 的 tool_calls 消息
            messages.append(
                {"role": "assistant", "content": None, "tool_calls": round_tool_calls}
            )
            for tc in round_tool_calls:
                fn = tc["function"]
                name = fn["name"]
                try:
                    arguments = json.loads(fn["arguments"] or "{}")
                except json.JSONDecodeError:
                    arguments = {}

                yield {"type": "tool", "name": name, "status": "running"}

                tool_start = time.monotonic()
                result = await registry.execute(name, ctx, arguments)
                latency_ms = int((time.monotonic() - tool_start) * 1000)

                await tool_call_repo.create(
                    user_id=user_id,
                    conversation_id=conv.id,
                    message_id=None,
                    tool_name=name,
                    arguments=arguments,
                    result=result.data if result.success else None,
                    status="success" if result.success else "failed",
                    error_message=result.error,
                    latency_ms=latency_ms,
                )

                if result.success:
                    yield {"type": "tool", "name": name, "status": "done"}
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(result.data, ensure_ascii=False),
                        }
                    )
                else:
                    tool_failures += 1
                    yield {"type": "tool", "name": name, "status": "failed", "message": result.error or "工具执行失败"}
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": f"错误: {result.error}",
                        }
                    )

            await db.commit()

            if tool_failures >= MAX_TOOL_FAILURES:
                break  # 工具连续失败达到上限：停止循环，返回当前结果
    except asyncio.CancelledError:
        if full_text:
            await msg_repo.create(conv.id, user_id, "assistant", full_text, model=provider.model)
            await usage_repo.create(
                user_id, conv.id, "agent", provider.model,
                total_usage["prompt_tokens"], total_usage["completion_tokens"],
                int((time.monotonic() - start) * 1000), "success", None,
            )
            conv.updated_at = datetime.now(timezone.utc)
            await db.commit()
        raise
    except AppException as exc:
        yield {"type": "error", "message": exc.message}
        await usage_repo.create(
            user_id, conv.id, "agent", provider.model,
            total_usage["prompt_tokens"], total_usage["completion_tokens"],
            int((time.monotonic() - start) * 1000), "failed", exc.message,
        )
        await db.commit()
        yield {
            "type": "done",
            "conversation_id": conv.id,
            "message_id": None,
            "usage": None,
            "error": exc.message,
        }
        return
    except Exception as exc:
        yield {"type": "error", "message": "AI 服务调用失败，请稍后重试"}
        await usage_repo.create(
            user_id, conv.id, "agent", provider.model,
            total_usage["prompt_tokens"], total_usage["completion_tokens"],
            int((time.monotonic() - start) * 1000), "failed", str(exc),
        )
        await db.commit()
        yield {
            "type": "done",
            "conversation_id": conv.id,
            "message_id": None,
            "usage": None,
            "error": str(exc),
        }
        return

    # 收尾：保存最终回答 + 用量日志
    latency_ms = int((time.monotonic() - start) * 1000)
    assistant_msg = None
    if full_text:
        assistant_msg = await msg_repo.create(
            conv.id, user_id, "assistant", full_text, model=provider.model
        )
    await usage_repo.create(
        user_id, conv.id, "agent", provider.model,
        total_usage["prompt_tokens"], total_usage["completion_tokens"], latency_ms, "success", None,
    )
    conv.updated_at = datetime.now(timezone.utc)
    await db.commit()

    yield {
        "type": "done",
        "conversation_id": conv.id,
        "message_id": assistant_msg.id if assistant_msg else None,
        "usage": {
            **total_usage,
            "total_tokens": total_usage["prompt_tokens"] + total_usage["completion_tokens"],
        },
    }
