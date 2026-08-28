"""工具注册表：向 LLM 导出工具 schema 并按名执行。"""
from app.agent.base import AgentContext, Tool, ToolResult
from app.agent.tools.knowledge import SearchKnowledgeTool
from app.agent.tools.tasks import (
    CreateTaskTool,
    DeleteTaskTool,
    ListTasksTool,
    UpdateTaskTool,
)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in (
            CreateTaskTool(),
            ListTasksTool(),
            UpdateTaskTool(),
            DeleteTaskTool(),
            SearchKnowledgeTool(),
        ):
            self._tools[tool.name] = tool

    def tool_schemas(self) -> list[dict]:
        """导出 OpenAI 兼容的 tools 定义。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    async def execute(self, name: str, ctx: AgentContext, arguments: dict) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(success=False, error=f"未知工具: {name}")
        return await tool.execute(ctx, **arguments)


registry = ToolRegistry()
