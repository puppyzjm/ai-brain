"""Agent 工具接口与执行上下文（TDD 铁律 R3：工具只能调 Service，AI 不碰数据库）。"""
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AgentContext:
    """工具执行上下文：绑定当前登录用户，工具执行时强制按 user_id 校验。"""

    user_id: int
    conversation_id: int | None
    db: AsyncSession


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None


class Tool(Protocol):
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema

    async def execute(self, ctx: AgentContext, **kwargs: Any) -> ToolResult: ...
