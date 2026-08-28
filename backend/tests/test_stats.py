"""Phase 7 用量统计接口测试。"""
import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_usage_stats_structure() -> None:
    """统计接口应返回 summary/by_type/daily 结构（新用户为空数据）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        username = f"test_{uuid.uuid4().hex[:10]}"
        await client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "test123456"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"account": username, "password": "test123456"},
        )
        token = resp.json()["data"]["access_token"]

        resp = await client.get(
            "/api/v1/stats/usage",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert "summary" in data and "by_type" in data and "daily" in data
        summary = data["summary"]
        assert summary["total_requests"] == 0
        assert summary["total_tokens"] == 0
        assert isinstance(summary["success_rate"], float)


async def test_usage_stats_requires_auth() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/stats/usage")
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010
