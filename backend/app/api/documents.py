"""文档接口：上传 / 列表 / 删除 / 重新解析 / AI 总结。"""
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.response import ok
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.document import DocumentResponse, SummarizeResponse
from app.services import document as document_service

router = APIRouter(tags=["documents"])


@router.post("/knowledge-bases/{kb_id}/documents")
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    doc = await document_service.upload_document(
        db, current_user.id, kb_id, file.filename or "unnamed", content
    )
    return ok(DocumentResponse.model_validate(doc).model_dump(mode="json"))


@router.get("/knowledge-bases/{kb_id}/documents")
async def list_documents(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    docs = await document_service.list_documents(db, current_user.id, kb_id)
    data = [DocumentResponse.model_validate(d).model_dump(mode="json") for d in docs]
    return ok(data)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await document_service.delete_document(db, current_user.id, document_id)
    return ok(None)


@router.post("/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await document_service.reprocess_document(db, current_user.id, document_id)
    return ok(DocumentResponse.model_validate(doc).model_dump(mode="json"))


@router.post("/documents/{document_id}/summarize")
async def summarize_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 总结文档（基于已解析内容，复用 DeepSeekProvider）。"""
    data = await document_service.summarize_document(db, current_user.id, document_id)
    return ok(SummarizeResponse(**data).model_dump())
