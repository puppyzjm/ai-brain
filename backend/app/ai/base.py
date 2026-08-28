"""AI Provider 抽象层（TDD 架构铁律 R1/R2）。

业务层只依赖这里的接口，禁止直接 import DeepSeek / Embedding SDK。
后续替换 OpenAI / Claude / 本地模型时，只需新增实现类。
"""
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ChatChunk:
    """流式对话的一个片段。"""
    content: str = ""
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    # Agent：流结束时累积完成的 tool_calls（OpenAI 兼容格式）
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class ChatResult:
    """非流式对话结果。"""
    content: str = ""
    usage: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str | None = None


class LLMProvider(Protocol):
    """LLM 抽象接口（当前实现：DeepSeekProvider）。"""

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatChunk]:
        """流式对话，逐段 yield ChatChunk（content 为文本片段，usage 在流结束时携带）。"""
        ...

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """非流式对话（用于 Agent 工具调用判断等）。"""
        ...


class EmbeddingProvider(Protocol):
    """Embedding 抽象接口（当前实现：SiliconFlowEmbeddingProvider）。"""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化。"""
        ...
