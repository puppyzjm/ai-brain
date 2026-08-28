"""知识检索工具：AI 主动检索用户知识库（复用 Phase 5 RAG，含 user_id 隔离）。"""
from app.agent.base import AgentContext, ToolResult
from app.services import rag as rag_service


class SearchKnowledgeTool:
    name = "search_knowledge"
    description = (
        "在用户指定的知识库中检索相关内容。"
        "当用户的问题需要基于其上传的资料回答、或需要查找知识库中的信息时使用。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "检索查询语句"},
            "knowledge_base_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "要检索的知识库 ID 列表（必填）",
            },
        },
        "required": ["query", "knowledge_base_ids"],
    }

    async def execute(
        self,
        ctx: AgentContext,
        query: str,
        knowledge_base_ids: list[int],
    ) -> ToolResult:
        try:
            chunks = await rag_service.search_knowledge(
                ctx.db, ctx.user_id, knowledge_base_ids, query
            )
            if not chunks:
                return ToolResult(
                    success=True,
                    data={"message": "知识库中没有找到相关信息", "chunks": []},
                )
            return ToolResult(
                success=True,
                data={
                    "chunks": [
                        {
                            "filename": c["filename"],
                            "content": c["content"][:500],
                            "similarity": c["similarity"],
                        }
                        for c in chunks
                    ]
                },
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
