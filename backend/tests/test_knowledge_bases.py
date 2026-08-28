"""Phase 4 知识库 CRUD 测试（不依赖 Embedding API Key）。"""
import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app


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


async def test_knowledge_base_crud_flow() -> None:
    """创建 → 列表 → 更新 → 删除 → 列表确认。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _register_and_login(client)

        resp = await client.post(
            "/api/v1/knowledge-bases",
            json={"name": "学习资料", "description": "测试描述"},
            headers=headers,
        )
        assert resp.status_code == 200
        kb_id = resp.json()["data"]["id"]

        resp = await client.get("/api/v1/knowledge-bases", headers=headers)
        assert resp.status_code == 200
        assert any(k["id"] == kb_id for k in resp.json()["data"])

        resp = await client.patch(
            f"/api/v1/knowledge-bases/{kb_id}",
            json={"name": "改名后的知识库"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "改名后的知识库"

        resp = await client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
        assert resp.status_code == 200

        resp = await client.get("/api/v1/knowledge-bases", headers=headers)
        assert all(k["id"] != kb_id for k in resp.json()["data"])


async def test_knowledge_base_isolation() -> None:
    """用户 A 的知识库对用户 B 不可见。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers_a = await _register_and_login(client)
        resp = await client.post(
            "/api/v1/knowledge-bases", json={"name": "A 的知识库"}, headers=headers_a
        )
        kb_id = resp.json()["data"]["id"]

        headers_b = await _register_and_login(client)
        resp = await client.patch(
            f"/api/v1/knowledge-bases/{kb_id}", json={"name": "越权"}, headers=headers_b
        )
        assert resp.status_code == 404
        # B 在 A 的知识库下查文档 → 404
        resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=headers_b)
        assert resp.status_code == 404


async def test_knowledge_base_requires_auth() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/knowledge-bases")
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010
