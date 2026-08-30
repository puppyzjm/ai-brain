"""Refresh Token 测试：双 token 签发 / 轮换 / 防重放 / 撤销。"""
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
    return resp.json()["data"]


async def test_login_returns_both_tokens() -> None:
    """登录应同时返回 access_token 与 refresh_token。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tokens = await _register_and_login(client)
        assert tokens["access_token"]
        assert tokens["refresh_token"]
        assert tokens["token_type"] == "bearer"
        # refresh token 不应是 JWT 格式（随机字符串）
        assert tokens["refresh_token"].count(".") == 0


async def test_refresh_rotates_tokens() -> None:
    """刷新成功：返回新 access + 新 refresh；旧 refresh 立即失效（防重放）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tokens = await _register_and_login(client)
        old_refresh = tokens["refresh_token"]

        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert resp.status_code == 200
        new_tokens = resp.json()["data"]
        assert new_tokens["access_token"]
        assert new_tokens["refresh_token"] != old_refresh

        # 新 access 可用
        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert resp.status_code == 200

        # 旧 refresh 重放 → 401（轮换已作废）
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010


async def test_refresh_with_invalid_token() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "invalid-token-value"}
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010


async def test_logout_revokes_refresh() -> None:
    """登出后 refresh token 被撤销，无法再刷新。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tokens = await _register_and_login(client)

        resp = await client.post(
            "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
        )
        assert resp.status_code == 200

        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert resp.status_code == 401
