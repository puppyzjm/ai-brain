"""文档总结测试。

- 错误路径不依赖外部 API（快速、稳定）。
- 正常流程真实调用 DeepSeek（容器内已配置 Key，符合「不 Mock 核心业务逻辑」）。
"""
import uuid

from httpx import ASGITransport, AsyncClient

from app.infrastructure.database import async_session_factory
from app.main import app
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User


def _random_username() -> str:
    return f"test_{uuid.uuid4().hex[:10]}"


async def _register_and_login(client: AsyncClient) -> dict:
    username = _random_username()
    await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "test123456"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"account": username, "password": "test123456"},
    )
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_ready_document(user_id: int) -> tuple[int, int]:
    """直接 ORM 构造：知识库 + ready 文档 + 2 个 chunk（零向量），返回 (kb_id, doc_id)。"""
    async with async_session_factory() as db:
        kb = KnowledgeBase(user_id=user_id, name="总结测试库")
        db.add(kb)
        await db.flush()
        doc = Document(
            user_id=user_id,
            knowledge_base_id=kb.id,
            filename="test_doc.txt",
            stored_path="fake/path.txt",
            file_type="txt",
            file_size=100,
            status="ready",
            chunk_count=2,
        )
        db.add(doc)
        await db.flush()
        db.add_all(
            [
                DocumentChunk(
                    user_id=user_id,
                    document_id=doc.id,
                    knowledge_base_id=kb.id,
                    seq=0,
                    content=(
                        "AI Brain 是一个个人智能知识库与 AI 助理平台。"
                        "用户可以将 PDF、TXT、Markdown 资料上传到知识库，"
                        "并通过 AI 对资料进行问答、总结和检索。"
                    ),
                    char_count=60,
                    embedding=[0.0] * 1024,
                ),
                DocumentChunk(
                    user_id=user_id,
                    document_id=doc.id,
                    knowledge_base_id=kb.id,
                    seq=1,
                    content=(
                        "AI Brain 还支持任务管理与 Agent 工具调用，"
                        "AI 可以根据用户意图创建、查询和修改任务。"
                    ),
                    char_count=45,
                    embedding=[0.0] * 1024,
                ),
            ]
        )
        await db.commit()
        return kb.id, doc.id


async def test_summarize_requires_auth() -> None:
    """未登录 → 401。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/documents/1/summarize")
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010


async def test_summarize_document_not_found() -> None:
    """文档不存在 → 404。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _register_and_login(client)
        resp = await client.post("/api/v1/documents/999999/summarize", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["code"] == 4040


async def test_summarize_document_not_owned() -> None:
    """他人的文档 → 404（user_id 隔离）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers_a = await _register_and_login(client)
        # 找到用户 A 的 id（从 /users/me）
        resp = await client.get("/api/v1/users/me", headers=headers_a)
        user_a_id = resp.json()["data"]["id"]
        _, doc_id = await _create_ready_document(user_a_id)

        headers_b = await _register_and_login(client)
        resp = await client.post(f"/api/v1/documents/{doc_id}/summarize", headers=headers_b)
        assert resp.status_code == 404


async def test_summarize_document_not_ready() -> None:
    """文档未解析完成（无 chunks）→ 400。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _register_and_login(client)
        resp = await client.get("/api/v1/users/me", headers=headers)
        user_id = resp.json()["data"]["id"]

        # 构造 uploaded 状态（未解析）文档
        async with async_session_factory() as db:
            kb = KnowledgeBase(user_id=user_id, name="未解析库")
            db.add(kb)
            await db.flush()
            doc = Document(
                user_id=user_id,
                knowledge_base_id=kb.id,
                filename="pending.txt",
                stored_path="fake/pending.txt",
                file_type="txt",
                file_size=10,
                status="uploaded",
            )
            db.add(doc)
            await db.commit()
            doc_id = doc.id

        resp = await client.post(f"/api/v1/documents/{doc_id}/summarize", headers=headers)
        assert resp.status_code == 400
        assert resp.json()["code"] == 4006


async def test_summarize_success_flow() -> None:
    """正常总结流程：真实调用 DeepSeek，返回结构化摘要。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _register_and_login(client)
        resp = await client.get("/api/v1/users/me", headers=headers)
        user_id = resp.json()["data"]["id"]
        _, doc_id = await _create_ready_document(user_id)

        resp = await client.post(f"/api/v1/documents/{doc_id}/summarize", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["document_id"] == doc_id
        assert len(data["summary"]) > 10  # 真实 LLM 返回非空摘要
