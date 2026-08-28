"""Phase 3 会话管理测试（不依赖外部 API Key）。"""
import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app


def _random_username() -> str:
    return f"test_{uuid.uuid4().hex[:10]}"


async def _register_and_login(client: AsyncClient) -> dict:
    username = _random_username()
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "test123456"},
    )
    assert resp.status_code == 200
    resp = await client.post(
        "/api/v1/auth/login",
        json={"account": username, "password": "test123456"},
    )
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_conversation_crud_flow() -> None:
    """新建 → 列表 → 重命名 → 查看历史 → 删除 → 列表确认。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _register_and_login(client)

        # 新建
        resp = await client.post("/api/v1/conversations", json={"title": "测试会话"}, headers=headers)
        assert resp.status_code == 200
        conv_id = resp.json()["data"]["id"]
        assert resp.json()["data"]["title"] == "测试会话"

        # 列表
        resp = await client.get("/api/v1/conversations", headers=headers)
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()["data"]]
        assert conv_id in ids

        # 重命名
        resp = await client.patch(
            f"/api/v1/conversations/{conv_id}", json={"title": "新标题"}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "新标题"

        # 历史（空会话）
        resp = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []

        # 删除
        resp = await client.delete(f"/api/v1/conversations/{conv_id}", headers=headers)
        assert resp.status_code == 200

        # 删除后列表不可见
        resp = await client.get("/api/v1/conversations", headers=headers)
        ids = [c["id"] for c in resp.json()["data"]]
        assert conv_id not in ids

        # 删除后访问历史应 404
        resp = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["code"] == 4040


async def test_conversation_isolation() -> None:
    """用户 A 的会话对用户 B 不可见（越权防护）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers_a = await _register_and_login(client)
        resp = await client.post("/api/v1/conversations", json={"title": "A 的会话"}, headers=headers_a)
        conv_id = resp.json()["data"]["id"]

        headers_b = await _register_and_login(client)
        # B 访问 A 的会话历史 → 404
        resp = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers_b)
        assert resp.status_code == 404
        # B 重命名 A 的会话 → 404
        resp = await client.patch(
            f"/api/v1/conversations/{conv_id}", json={"title": "越权"}, headers=headers_b
        )
        assert resp.status_code == 404


async def test_conversation_requires_auth() -> None:
    """未登录访问会话接口应 401。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/conversations")
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010
