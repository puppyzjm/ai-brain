"""多模态视觉问答测试：图片上传校验 / 读取 / 用户隔离 / 带图 chat。

真实视觉模型调用用例（vision_success_flow）在 CI 中被排除（无 SiliconFlow Key），
本地 .env 有 Key 时正常执行。
"""
import uuid

import fitz
from httpx import ASGITransport, AsyncClient

from app.main import app


def _make_png_bytes(width: int = 64, height: int = 64) -> bytes:
    """用 PyMuPDF 生成纯红色测试图片（Qwen3-VL 要求宽高 ≥28px）。"""
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    page.draw_rect(page.rect, color=(1, 0, 0), fill=(1, 0, 0))
    png = page.get_pixmap().tobytes("png")
    doc.close()
    return png


PNG_BYTES = _make_png_bytes()


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


async def _upload_png(client: AsyncClient, token: str, name: str = "test.png") -> str:
    resp = await client.post(
        "/api/v1/chat-images",
        headers=_auth(token),
        files={"file": (name, PNG_BYTES, "image/png")},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["name"]


async def test_upload_chat_image_rejects_non_image() -> None:
    """伪装扩展名的非图片内容必须被魔数校验拒绝。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")
        resp = await client.post(
            "/api/v1/chat-images",
            headers=_auth(token),
            files={"file": ("evil.png", b"not an image", "image/png")},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 4004


async def test_upload_chat_image_rejects_oversize() -> None:
    """超过 5MB 的图片必须被拒绝。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")
        big = b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024)
        resp = await client.post(
            "/api/v1/chat-images",
            headers=_auth(token),
            files={"file": ("big.png", big, "image/png")},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 4005


async def test_upload_and_read_chat_image() -> None:
    """上传后可经鉴权接口读回原图；不存在的文件返回 404。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")
        name = await _upload_png(client, token)

        resp = await client.get(f"/api/v1/chat-images/{name}", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.content == PNG_BYTES

        resp = await client.get(
            "/api/v1/chat-images/does-not-exist.png", headers=_auth(token)
        )
        assert resp.status_code == 404


async def test_chat_image_user_isolation() -> None:
    """用户 A 的图片不能被用户 B 读取（即使知道文件名）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token_a = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")
        token_b = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")
        name = await _upload_png(client, token_a)

        resp = await client.get(f"/api/v1/chat-images/{name}", headers=_auth(token_b))
        assert resp.status_code == 404


async def test_chat_rejects_empty_content_and_images() -> None:
    """content 与 images 同时为空 → 参数校验失败。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")
        resp = await client.post(
            "/api/v1/chat",
            headers=_auth(token),
            json={"content": "", "images": None},
        )
        assert resp.status_code == 422


async def test_chat_rejects_images_with_rag() -> None:
    """RAG 模式带图片 → SSE error 提示（第一版划界）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")
        kb_resp = await client.post(
            "/api/v1/knowledge-bases",
            headers=_auth(token),
            json={"name": "kb", "description": ""},
        )
        kb_id = kb_resp.json()["data"]["id"]
        name = await _upload_png(client, token)

        resp = await client.post(
            "/api/v1/chat",
            headers=_auth(token),
            json={
                "content": "这张图里有什么",
                "knowledge_base_ids": [kb_id],
                "images": [name],
            },
        )
        assert resp.status_code == 200
        assert "RAG 知识库问答暂不支持图片" in resp.text


async def test_vision_chat_success_flow() -> None:
    """真实视觉模型调用：上传红色像素图 → 带图提问 → 流式回答 + done。

    依赖真实 SiliconFlow Key 与视觉模型，CI 排除（见 ci.yml）。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _register_and_login(client, f"test_{uuid.uuid4().hex[:10]}")
        name = await _upload_png(client, token)

        resp = await client.post(
            "/api/v1/chat",
            headers=_auth(token),
            json={"content": "这张图片是什么颜色？", "images": [name]},
        )
        assert resp.status_code == 200
        body = resp.text
        assert '"type": "delta"' in body  # 有流式回答
        assert '"type": "done"' in body
        assert '"message_id": null' not in body.split('"type": "done"')[-1][:200]
