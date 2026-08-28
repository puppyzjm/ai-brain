"""DeepSeek Provider（OpenAI 兼容协议）。

注意：openai SDK 只允许在本模块内部 import，
业务层一律通过 app.ai.base.LLMProvider 接口使用（TDD 铁律 R1）。
"""
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.ai.base import ChatChunk, ChatResult


class DeepSeekProvider:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @property
    def model(self) -> str:
        return self._model

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatChunk]:
        params: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            params["tools"] = tools

        stream = await self._client.chat.completions.create(**params)
        # 流式 tool_calls 累积：按 index 组装 id/name/arguments 分片
        tool_calls_acc: dict[int, dict[str, str]] = {}

        async for chunk in stream:
            # 支持 include_usage 的流：最后一个 chunk 携带 usage
            if chunk.usage is not None:
                yield ChatChunk(
                    usage={
                        "prompt_tokens": chunk.usage.prompt_tokens or 0,
                        "completion_tokens": chunk.usage.completion_tokens or 0,
                    }
                )
                continue
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index or 0
                    acc = tool_calls_acc.setdefault(
                        idx, {"id": "", "name": "", "arguments": ""}
                    )
                    if tc.id:
                        acc["id"] = tc.id
                    if tc.function and tc.function.name:
                        acc["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        acc["arguments"] += tc.function.arguments
                continue

            if delta and delta.content:
                yield ChatChunk(content=delta.content, finish_reason=choice.finish_reason)

        # 流结束时统一输出累积完成的 tool_calls
        if tool_calls_acc:
            yield ChatChunk(
                tool_calls=[
                    {
                        "id": acc["id"],
                        "type": "function",
                        "function": {"name": acc["name"], "arguments": acc["arguments"]},
                    }
                    for acc in tool_calls_acc.values()
                ]
            )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        params: dict[str, Any] = {"model": self._model, "messages": messages}
        if tools:
            params["tools"] = tools

        resp = await self._client.chat.completions.create(**params)
        choice = resp.choices[0]
        usage = resp.usage
        return ChatResult(
            content=choice.message.content or "",
            usage=(
                {
                    "prompt_tokens": usage.prompt_tokens or 0,
                    "completion_tokens": usage.completion_tokens or 0,
                }
                if usage
                else None
            ),
            tool_calls=(
                [tc.model_dump() for tc in choice.message.tool_calls]
                if choice.message.tool_calls
                else None
            ),
            finish_reason=choice.finish_reason,
        )
