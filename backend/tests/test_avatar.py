"""用户头像测试：上传校验 / 更换 / 删除 / 用户隔离。"""
import uuid

import fitz
from httpx import ASGITransport, AsyncClient

from app.main import app


def _make_png_bytes(width: int = 64, height: int = 64) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    page.draw_rect(page.rect, color=(0, 0.6, 0.5), fill=(0, 0.6, 0.5))
    png = page.get_pixmap().tobytes("png")
    doc.close()
    return png


async def _register_and_login(client: AsyncClient, username: str) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "test123456"},
    )
    assert resp.status_code == 200
    resp = await client.post(
        "/api/v1/auth/login",
        json={"account": username, "password": "test123456"},
    )
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_avatar_upload_replace_delete_flow() -> None:
    """上传 → me 返回 avatar → 更换 → 删除 → avatar 为空。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")

        # 上传
        resp = await client.post(
            "/api/v1/users/avatar",
            headers=_auth(token),
            files={"file": ("a.png", _make_png_bytes(), "image/png")},
        )
        assert resp.status_code == 200
        name1 = resp.json()["data"]["avatar"]

        # me 返回 avatar 字段
        me = await client.get("/api/v1/users/me", headers=_auth(token))
        assert me.json()["data"]["avatar"] == name1

        # 鉴权读取
        resp = await client.get(f"/api/v1/users/avatar/{name1}", headers=_auth(token))
        assert resp.status_code == 200

        # 更换
        resp = await client.post(
            "/api/v1/users/avatar",
            headers=_auth(token),
            files={"file": ("b.png", _make_png_bytes(80, 80), "image/png")},
        )
        assert resp.status_code == 200
        name2 = resp.json()["data"]["avatar"]
        assert name2 != name1
        # 旧头像已被删除
        resp = await client.get(f"/api/v1/users/avatar/{name1}", headers=_auth(token))
        assert resp.status_code == 404

        # 删除
        resp = await client.delete("/api/v1/users/avatar", headers=_auth(token))
        assert resp.status_code == 200
        me = await client.get("/api/v1/users/me", headers=_auth(token))
        assert me.json()["data"]["avatar"] is None
        resp = await client.get(f"/api/v1/users/avatar/{name2}", headers=_auth(token))
        assert resp.status_code == 404


async def test_avatar_rejects_non_image() -> None:
    """伪装扩展名的非图片内容必须被魔数校验拒绝。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")
        resp = await client.post(
            "/api/v1/users/avatar",
            headers=_auth(token),
            files={"file": ("evil.png", b"not an image", "image/png")},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 4004


async def test_avatar_user_isolation() -> None:
    """用户 A 的头像不能被用户 B 读取。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token_a = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")
        token_b = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")

        resp = await client.post(
            "/api/v1/users/avatar",
            headers=_auth(token_a),
            files={"file": ("a.png", _make_png_bytes(), "image/png")},
        )
        name = resp.json()["data"]["avatar"]

        resp = await client.get(f"/api/v1/users/avatar/{name}", headers=_auth(token_b))
        assert resp.status_code == 404
