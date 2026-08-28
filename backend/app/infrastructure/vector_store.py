"""VectorStore：pgvector 写入与相似度检索。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class PgVectorStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_chunks(self, records: list[dict]) -> int:
        """批量插入 chunks。

        records 每项：{user_id, document_id, knowledge_base_id, seq,
                      content, char_count, chunk_metadata, embedding}
        返回插入数量。
        """
        objs = [
            DocumentChunk(
                user_id=r["user_id"],
                document_id=r["document_id"],
                knowledge_base_id=r["knowledge_base_id"],
                seq=r["seq"],
                content=r["content"],
                char_count=r["char_count"],
                chunk_metadata=r.get("chunk_metadata"),
                embedding=r["embedding"],
            )
            for r in records
        ]
        self.db.add_all(objs)
        await self.db.flush()
        return len(objs)

    async def search(
        self,
        user_id: int,
        kb_ids: list[int],
        query_vector: list[float],
        top_k: int = 6,
        threshold: float = 0.5,
    ) -> list[dict]:
        """向量相似度检索（HNSW + cosine），强制 user_id / 知识库过滤。

        返回 [{chunk_id, document_id, knowledge_base_id, content,
               metadata, filename, similarity}]（已按阈值过滤，按相似度降序）。
        """
        distance = DocumentChunk.embedding.cosine_distance(query_vector)
        stmt = (
            select(
                DocumentChunk,
                Document.filename,
                (1 - distance).label("similarity"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.user_id == user_id,
                DocumentChunk.knowledge_base_id.in_(kb_ids),
                Document.deleted_at.is_(None),
            )
            .order_by(distance)
            .limit(top_k)
        )
        rows = (await self.db.execute(stmt)).all()

        results: list[dict] = []
        for chunk, filename, similarity in rows:
            if similarity < threshold:
                continue
            results.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "knowledge_base_id": chunk.knowledge_base_id,
                    "content": chunk.content,
                    "metadata": chunk.chunk_metadata,
                    "filename": filename,
                    "similarity": round(float(similarity), 4),
                }
            )
        return results
