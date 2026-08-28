"""RAG 检索器：Query Embedding → pgvector 相似度检索。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_embedding_provider
from app.infrastructure.vector_store import PgVectorStore

TOP_K = 6
SIMILARITY_THRESHOLD = 0.5


async def retrieve(
    db: AsyncSession,
    user_id: int,
    kb_ids: list[int],
    question: str,
    top_k: int = TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict]:
    """问题向量化并在指定知识库内检索 Top-K 相关 chunk（已按阈值过滤）。"""
    provider = get_embedding_provider()
    query_vector = (await provider.embed([question]))[0]
    return await PgVectorStore(db).search(user_id, kb_ids, query_vector, top_k, threshold)
