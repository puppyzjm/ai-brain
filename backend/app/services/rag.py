"""RAG 业务编排：知识库权限校验 + 检索组装。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.rag import retriever
from app.repositories.knowledge_base import KnowledgeBaseRepository


async def validate_kb_access(db: AsyncSession, user_id: int, kb_ids: list[int]) -> None:
    """校验知识库归属：任一知识库不存在或不属于当前用户 → 404。"""
    repo = KnowledgeBaseRepository(db)
    for kb_id in kb_ids:
        if await repo.get_by_id(user_id, kb_id) is None:
            raise NotFoundError("知识库不存在")


async def search_knowledge(
    db: AsyncSession, user_id: int, kb_ids: list[int], question: str
) -> list[dict]:
    """Query Embedding → 向量检索，返回命中 chunk（已阈值过滤）。"""
    return await retriever.retrieve(db, user_id, kb_ids, question)
