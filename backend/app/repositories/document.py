"""Document 数据访问层（user_id 强制隔离 + 文档软删 + chunk 物理删）。"""
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        knowledge_base_id: int,
        filename: str,
        stored_path: str,
        file_type: str,
        file_size: int,
    ) -> Document:
        doc = Document(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            stored_path=stored_path,
            file_type=file_type,
            file_size=file_size,
            status="uploaded",
        )
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def get_by_id(self, user_id: int, document_id: int) -> Document | None:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
                Document.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_kb(self, user_id: int, kb_id: int) -> list[Document]:
        result = await self.db.execute(
            select(Document)
            .where(
                Document.knowledge_base_id == kb_id,
                Document.user_id == user_id,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.id.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        user_id: int,
        document_id: int,
        status: str,
        error_message: str | None = None,
        chunk_count: int | None = None,
    ) -> Document | None:
        doc = await self.get_by_id(user_id, document_id)
        if doc is None:
            return None
        doc.status = status
        doc.error_message = error_message
        if chunk_count is not None:
            doc.chunk_count = chunk_count
        doc.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return doc

    async def soft_delete(self, user_id: int, document_id: int) -> bool:
        doc = await self.get_by_id(user_id, document_id)
        if doc is None:
            return False
        doc.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def delete_chunks(self, user_id: int, document_id: int) -> int:
        """物理删除某文档的全部 chunks（向量必须物理删）。"""
        result = await self.db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.user_id == user_id,
            )
        )
        await self.db.flush()
        return result.rowcount or 0

    async def list_chunks(self, user_id: int, document_id: int) -> list[DocumentChunk]:
        """按 seq 升序取文档全部 chunks（文档总结用）。"""
        result = await self.db.execute(
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.user_id == user_id,
            )
            .order_by(DocumentChunk.seq.asc())
        )
        return list(result.scalars().all())
