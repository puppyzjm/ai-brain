"""RAG 检索器：混合检索（向量 + BM25）→ RRF 融合。"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_embedding_provider
from app.infrastructure.vector_store import PgVectorStore
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.bm25 import bm25_search
from app.rag.fusion import rrf_fusion

TOP_K = 6
SIMILARITY_THRESHOLD = 0.5
# 两路各自召回的上限（粗排）
CANDIDATE_K = 30

# 抑制 jieba 词典加载日志
jieba_logger = logging.getLogger("jieba")
jieba_logger.setLevel(logging.ERROR)


async def retrieve(
    db: AsyncSession,
    user_id: int,
    kb_ids: list[int],
    question: str,
    top_k: int = TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict]:
    """混合检索：向量路（语义）+ BM25 路（关键词）→ RRF 融合取 Top-K。

    诚实原则：向量路全部低于阈值且 BM25 无任何命中 → 返回空列表
    （由上层走「知识库中没有找到足够的信息」固定话术，不调 LLM）。
    """
    # 路 1：向量语义召回（粗排 30，不过滤低分）
    provider = get_embedding_provider()
    query_vector = (await provider.embed([question]))[0]
    vector_chunks = await PgVectorStore(db).search(
        user_id, kb_ids, query_vector, top_k=CANDIDATE_K, threshold=0.0
    )

    # 路 2：BM25 关键词召回
    bm25_hits = await bm25_search(db, user_id, kb_ids, question, top_k=CANDIDATE_K)

    # 诚实原则判断：两路都无有效信号
    vector_best = vector_chunks[0]["similarity"] if vector_chunks else 0.0
    if not bm25_hits and vector_best < threshold:
        return []

    # RRF 融合
    fused = rrf_fusion(
        [
            [(c["chunk_id"], c["similarity"]) for c in vector_chunks],
            bm25_hits,
        ]
    )
    ranked_ids = sorted(fused, key=lambda cid: fused[cid], reverse=True)[:top_k]

    # 组装结果（向量路的 chunk 带完整详情；BM25 独占命中补查详情）
    by_id = {c["chunk_id"]: c for c in vector_chunks}
    bm25_by_id = dict(bm25_hits)
    missing_ids = [cid for cid in ranked_ids if cid not in by_id]
    details = await _load_chunk_details(db, user_id, missing_ids)

    results: list[dict] = []
    for cid in ranked_ids:
        if cid in by_id:
            item = dict(by_id[cid])
        elif cid in details:
            item = details[cid]
        else:
            # 缓存残留的已删除 chunk（失效竞态）：安全跳过，绝不 500
            continue
        item["bm25_score"] = round(bm25_by_id.get(cid, 0.0), 4)
        results.append(item)
    return results


async def _load_chunk_details(
    db: AsyncSession, user_id: int, chunk_ids: list[int]
) -> dict[int, dict]:
    """补查 BM25 独占命中 chunk 的详情（含文档名）。"""
    if not chunk_ids:
        return {}
    stmt = (
        select(DocumentChunk, Document.filename)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.id.in_(chunk_ids),
            DocumentChunk.user_id == user_id,
            Document.deleted_at.is_(None),
        )
    )
    rows = (await db.execute(stmt)).all()
    return {
        chunk.id: {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "knowledge_base_id": chunk.knowledge_base_id,
            "content": chunk.content,
            "metadata": chunk.chunk_metadata,
            "filename": filename,
            "similarity": 0.0,  # 向量路未召回，相似度记为 0
        }
        for chunk, filename in rows
    }
