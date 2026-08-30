"""BM25 关键词检索（jieba 中文分词 + rank-bm25，进程内索引缓存）。

缓存策略：以 (user_id, kb_id 元组) 为键缓存索引；以「(chunk 总数, max(chunk.id))」
作版本号。chunk 为硬删除且 id 单调不复用，因此该二元组能唯一确定现存 chunk
集合——删除文档导致总数回落到历史值时版本也不会碰撞（单纯用总数会碰撞）。
构建开销在个人规模下为毫秒级。
"""
import jieba
from rank_bm25 import BM25Okapi
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk

# 进程内缓存：key=(user_id, tuple(kb_ids)) -> ((chunk_total, max_chunk_id), index, chunk_ids)
_cache: dict[tuple, tuple[tuple[int, int], BM25Okapi, list[int]]] = {}
_CACHE_MAX_ENTRIES = 32


def tokenize(text: str) -> list[str]:
    """中文分词 + 英文小写化，过滤空白 token。"""
    return [t.lower() for t in jieba.lcut(text) if t.strip()]


async def _load_chunks(db: AsyncSession, user_id: int, kb_ids: list[int]) -> tuple[int, list[int], list[str]]:
    """取指定知识库全部 chunk 的 (id, content)，按 id 稳定排序。"""
    stmt = (
        select(DocumentChunk.id, DocumentChunk.content)
        .where(DocumentChunk.user_id == user_id, DocumentChunk.knowledge_base_id.in_(kb_ids))
        .order_by(DocumentChunk.id.asc())
    )
    rows = (await db.execute(stmt)).all()
    ids = [r[0] for r in rows]
    contents = [r[1] for r in rows]
    return len(ids), ids, contents


async def _chunk_stats(db: AsyncSession, user_id: int, kb_ids: list[int]) -> tuple[int, int]:
    """返回 (chunk 总数, max(chunk.id)) 作为缓存版本信号。"""
    stmt = select(func.count(DocumentChunk.id), func.max(DocumentChunk.id)).where(
        DocumentChunk.user_id == user_id, DocumentChunk.knowledge_base_id.in_(kb_ids)
    )
    count, max_id = (await db.execute(stmt)).one()
    return int(count), int(max_id or 0)


def _build_index(contents: list[str]) -> BM25Okapi:
    return BM25Okapi([tokenize(c) for c in contents])


async def bm25_search(
    db: AsyncSession,
    user_id: int,
    kb_ids: list[int],
    query: str,
    top_k: int = 30,
) -> list[tuple[int, float]]:
    """返回 [(chunk_id, bm25_score), ...] 按分数降序（分数 > 0）。"""
    key = (user_id, tuple(sorted(kb_ids)))

    total, max_id = await _chunk_stats(db, user_id, kb_ids)
    if total == 0:
        return []

    version = (total, max_id)
    cached = _cache.get(key)
    if cached is None or cached[0] != version:
        if len(_cache) >= _CACHE_MAX_ENTRIES:
            _cache.pop(next(iter(_cache)))
        _, ids, contents = await _load_chunks(db, user_id, kb_ids)
        _cache[key] = (version, _build_index(contents), ids)

    _, index, ids = _cache[key]
    scores = index.get_scores(tokenize(query))
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [(ids[i], float(s)) for i, s in ranked[:top_k] if s > 0]
