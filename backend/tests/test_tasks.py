"""Phase 6 Task CRUD 测试（不依赖 AI API Key）。"""
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


async def test_task_crud_flow() -> None:
    """创建 → 列表 → 筛选 → 更新 → 删除 → 列表确认。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _register_and_login(client)

        resp = await client.post(
            "/api/v1/tasks",
            json={"title": "学习 FastAPI", "priority": "high", "due_date": "2026-12-31"},
            headers=headers,
        )
        assert resp.status_code == 200
        task_id = resp.json()["data"]["id"]
        assert resp.json()["data"]["status"] == "todo"

        # 列表 + 状态筛选
        resp = await client.get("/api/v1/tasks", headers=headers)
        assert resp.status_code == 200
        assert any(t["id"] == task_id for t in resp.json()["data"])

        resp = await client.get("/api/v1/tasks?status=done", headers=headers)
        assert all(t["status"] == "done" for t in resp.json()["data"])

        # 更新
        resp = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "done", "priority": "low"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "done"
        assert resp.json()["data"]["priority"] == "low"

        # 删除
        resp = await client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
        assert resp.status_code == 200

        resp = await client.get("/api/v1/tasks", headers=headers)
        assert all(t["id"] != task_id for t in resp.json()["data"])


async def test_task_isolation() -> None:
    """用户 A 的任务对用户 B 不可见（更新/删除返回 404）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers_a = await _register_and_login(client)
        resp = await client.post(
            "/api/v1/tasks", json={"title": "A 的任务"}, headers=headers_a
        )
        task_id = resp.json()["data"]["id"]

        headers_b = await _register_and_login(client)
        resp = await client.patch(
            f"/api/v1/tasks/{task_id}", json={"status": "done"}, headers=headers_b
        )
        assert resp.status_code == 404
        resp = await client.delete(f"/api/v1/tasks/{task_id}", headers=headers_b)
        assert resp.status_code == 404


async def test_task_requires_auth() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks")
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010


async def test_task_validation() -> None:
    """非法优先级应 422。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _register_and_login(client)
        resp = await client.post(
            "/api/v1/tasks",
            json={"title": "非法优先级", "priority": "urgent"},
            headers=headers,
        )
        assert resp.status_code == 422
