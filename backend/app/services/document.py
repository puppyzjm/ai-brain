"""文档服务：上传、异步解析、删除、重新解析、AI 总结。

异步解析采用进程内 asyncio 任务 + DB 状态机（TDD 方案，不引入 Celery）：
  uploaded → parsing → ready / failed
应用重启中断的文档停留在 parsing，可通过「重新解析」恢复。
"""
import asyncio
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_embedding_provider, get_llm_provider
from app.core.config import settings
from app.core.exceptions import AppException, NotFoundError
from app.document import loader
from app.document.ocr import PdfOcrService
from app.document.pipeline import chunks_from_sections, extract_chunks
from app.infrastructure.database import async_session_factory
from app.infrastructure.storage import save_upload
from app.infrastructure.vector_store import PgVectorStore
from app.models.document import Document
from app.repositories.ai_usage_log import AiUsageLogRepository
from app.repositories.document import DocumentRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository

# Embedding 批量大小
EMBED_BATCH_SIZE = 32

# 文档总结：Context 组装上限（字符），超长文档截断（TDD 风险 #3 的 MVP 处理）
MAX_SUMMARY_CHARS = 8000

SUMMARY_SYSTEM_PROMPT = (
    "你是一个文档总结助手。请基于提供的【文档内容】生成结构化摘要，包含：\n"
    "1. 核心主题（一句话概括）\n"
    "2. 关键要点（3~6 条，使用 Markdown 列表）\n"
    "3. 结论或行动建议（如有）\n"
    "规则：只基于文档内容总结，不要编造文档中不存在的信息。"
)

# 保存后台任务引用，防止被 GC
_background_tasks: set[asyncio.Task] = set()


def _track(task: asyncio.Task) -> None:
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def upload_document(
    db: AsyncSession,
    user_id: int,
    kb_id: int,
    filename: str,
    content: bytes,
) -> Document:
    kb = await KnowledgeBaseRepository(db).get_by_id(user_id, kb_id)
    if kb is None:
        raise NotFoundError("知识库不存在")

    stored_path, file_type, file_size = save_upload(content, filename)
    doc = await DocumentRepository(db).create(
        user_id, kb_id, filename, stored_path, file_type, file_size
    )
    await db.commit()
    await db.refresh(doc)

    task = asyncio.create_task(_process_document(user_id, doc.id))
    _track(task)
    return doc


async def list_documents(db: AsyncSession, user_id: int, kb_id: int) -> list[Document]:
    kb = await KnowledgeBaseRepository(db).get_by_id(user_id, kb_id)
    if kb is None:
        raise NotFoundError("知识库不存在")
    return await DocumentRepository(db).list_by_kb(user_id, kb_id)


async def delete_document(db: AsyncSession, user_id: int, document_id: int) -> None:
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(user_id, document_id)
    if doc is None:
        raise NotFoundError("文档不存在")
    # 软删文档 + 同事务物理删除 chunks（向量必须物理删）
    await repo.delete_chunks(user_id, document_id)
    await repo.soft_delete(user_id, document_id)
    await db.commit()


async def reprocess_document(db: AsyncSession, user_id: int, document_id: int) -> Document:
    """重新解析：清空旧 chunks，重新走解析 pipeline（用于失败重试/重启恢复）。"""
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(user_id, document_id)
    if doc is None:
        raise NotFoundError("文档不存在")
    await repo.delete_chunks(user_id, document_id)
    await repo.update_status(user_id, document_id, "uploaded", chunk_count=0)
    await db.commit()

    task = asyncio.create_task(_process_document(user_id, document_id))
    _track(task)

    await db.refresh(doc)
    return doc


async def _process_document(user_id: int, document_id: int) -> None:
    """后台解析 pipeline（独立 DB 会话，不依赖请求会话）。"""
    async with async_session_factory() as db:
        repo = DocumentRepository(db)
        doc = await repo.get_by_id(user_id, document_id)
        if doc is None:
            return

        await repo.update_status(user_id, document_id, "parsing", error_message=None)
        await db.commit()

        try:
            chunks = extract_chunks(doc.stored_path, doc.file_type)

            # OCR fallback：扫描版 PDF（无文字层的页 → 视觉模型提取文字）
            if doc.file_type == "pdf":
                empty_pages = loader.find_empty_pages(doc.stored_path)
                if empty_pages:
                    try:
                        ocr_service = PdfOcrService(
                            api_key=settings.embedding_api_key,
                            base_url=settings.embedding_base_url,
                            model=settings.ocr_model,
                        )
                        ocr_texts = await ocr_service.ocr_pages(doc.stored_path, empty_pages)
                    except Exception as exc:
                        raise ValueError(f"扫描页 OCR 提取失败：{str(exc)[:200]}") from exc
                    ocr_sections = [
                        {"text": text, "metadata": {"page": page}}
                        for page, text in ocr_texts.items()
                    ]
                    chunks.extend(chunks_from_sections(ocr_sections))

            if not chunks:
                raise ValueError("文档内容为空或无法解析")

            provider = get_embedding_provider()
            texts = [c[0] for c in chunks]
            embeddings: list[list[float]] = []
            for i in range(0, len(texts), EMBED_BATCH_SIZE):
                batch = texts[i : i + EMBED_BATCH_SIZE]
                embeddings.extend(await provider.embed(batch))

            records = []
            for idx, ((text, meta), emb) in enumerate(zip(chunks, embeddings)):
                records.append(
                    {
                        "user_id": user_id,
                        "document_id": document_id,
                        "knowledge_base_id": doc.knowledge_base_id,
                        "seq": idx,
                        "content": text,
                        "char_count": len(text),
                        "chunk_metadata": meta or None,
                        "embedding": emb,
                    }
                )
            await PgVectorStore(db).add_chunks(records)
            await repo.update_status(
                user_id, document_id, "ready", chunk_count=len(records), error_message=None
            )
            await db.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await db.rollback()
            await repo.update_status(
                user_id, document_id, "failed", error_message=str(exc)[:500]
            )
            await db.commit()


async def summarize_document(
    db: AsyncSession, user_id: int, document_id: int
) -> dict:
    """AI 总结文档：基于已解析 chunks 组装内容 → DeepSeek 生成结构化摘要。

    - 文档必须属于当前用户（否则 404）
    - 文档必须已解析完成（ready）且有 chunks
    - 多 chunks 按 seq 顺序组装，超过上限截断（不破坏 RAG 逻辑）
    - 写 ai_usage_logs（type=summary）
    """
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(user_id, document_id)
    if doc is None:
        raise NotFoundError("文档不存在")
    if doc.status != "ready":
        raise AppException(code=4006, message="文档尚未解析完成，请稍后再试", http_status=400)

    chunks = await repo.list_chunks(user_id, document_id)
    if not chunks:
        raise AppException(code=4007, message="文档没有可总结的内容", http_status=400)

    # 按 seq 组装（list_chunks 已排序），超长截断
    parts = [c.content for c in chunks]
    doc_text = "\n\n".join(parts)
    if len(doc_text) > MAX_SUMMARY_CHARS:
        doc_text = doc_text[:MAX_SUMMARY_CHARS]

    provider = get_llm_provider()
    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": f"【文档内容】\n{doc_text}\n\n请总结以上文档。"},
    ]

    start = time.monotonic()
    try:
        result = await provider.chat(messages)
        summary = result.content or ""
        usage = result.usage or {"prompt_tokens": 0, "completion_tokens": 0}
        status = "success"
        error_message: str | None = None
    except AppException as exc:
        summary = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        status = "failed"
        error_message = exc.message
        raise AppException(code=6003, message=f"AI 总结失败：{exc.message}", http_status=502)
    except Exception as exc:
        summary = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        status = "failed"
        error_message = str(exc)
        raise AppException(code=6003, message="AI 总结失败，请稍后重试", http_status=502)
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        await AiUsageLogRepository(db).create(
            user_id=user_id,
            conversation_id=None,
            type_="summary",
            model=provider.model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        await db.commit()

    return {"document_id": doc.id, "summary": summary}
