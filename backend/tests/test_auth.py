"""Phase 2 用户系统测试：注册 / 登录 / 资料 / 鉴权。"""
import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app


def _random_username() -> str:
    return f"test_{uuid.uuid4().hex[:10]}"


async def test_register_login_me_flow() -> None:
    """完整流程：注册 → 登录 → 获取 /users/me。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        username = _random_username()

        # 注册
        resp = await client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "test123456"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["username"] == username

        # 登录
        resp = await client.post(
            "/api/v1/auth/login",
            json={"account": username, "password": "test123456"},
        )
        assert resp.status_code == 200
        token = resp.json()["data"]["access_token"]
        assert token

        # 获取资料
        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == username


async def test_register_duplicate_username() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        username = _random_username()
        payload = {"username": username, "password": "test123456"}

        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 200

        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409
        assert resp.json()["code"] == 4001


async def test_login_wrong_password() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        username = _random_username()
        await client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "test123456"},
        )

        resp = await client.post(
            "/api/v1/auth/login",
            json={"account": username, "password": "wrong-password"},
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == 4003


async def test_me_without_token() -> None:
    """未登录访问受保护接口应返回 401。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010
