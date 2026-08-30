"""BM25 缓存失效回归测试：删文档 + 再上传（chunk 总数不变）后索引必须重建。

背景：线上出现「删除文档后提问 500（KeyError）」——缓存版本信号只含 chunk 总数，
删旧 + 传新后总数与缓存相同导致索引不重建、返回已删除 chunk 的脏 id。
修复：版本信号改为 (chunk 总数, max(chunk.id))，id 单调不复用保证唯一性。
"""
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.main import app
from app.rag import bm25

# 1024 维零向量（测试不依赖真实 Embedding API）
_ZERO_VEC = "array_fill(0::real, ARRAY[1024])::vector"


async def _setup_user_kb() -> tuple[int, int]:
    """API 注册随机用户并创建知识库，返回 (user_id, kb_id)。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        username = f"test_{uuid.uuid4().hex[:10]}"
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

        resp = await client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        user_id = resp.json()["data"]["id"]

        resp = await client.post(
            "/api/v1/knowledge-bases",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "缓存回归", "description": ""},
        )
        kb_id = resp.json()["data"]["id"]
        return user_id, kb_id


async def _insert_doc_chunks(
    db: AsyncSession, user_id: int, kb_id: int, related: str, unrelated: str
) -> tuple[list[int], list[int]]:
    """插入一个文档：2 个相关 chunk + 3 个无关 chunk（保证 IDF 为正）。

    返回 (related_ids, all_ids)。无关 chunk 用于稀释词频，避免所有文档都含
    查询词时 BM25 的 IDF 为负、分数全被过滤。
    """
    count = 5
    doc_id = (
        await db.execute(
            text(
                "INSERT INTO documents (user_id, knowledge_base_id, filename, stored_path,"
                " file_type, file_size, status, chunk_count) VALUES"
                " (:uid, :kb, 't.txt', '/tmp/t.txt', 'txt', 0, 'ready', :n) RETURNING id"
            ),
            {"uid": user_id, "kb": kb_id, "n": count},
        )
    ).scalar_one()

    related_ids: list[int] = []
    all_ids: list[int] = []
    contents = [related, related, unrelated, unrelated, unrelated]
    for seq, content in enumerate(contents):
        cid = (
            await db.execute(
                text(
                    f"INSERT INTO document_chunks (user_id, document_id, knowledge_base_id,"
                    f" seq, content, char_count, embedding) VALUES"
                    f" (:uid, :did, :kb, :seq, :content, :n, {_ZERO_VEC}) RETURNING id"
                ),
                {
                    "uid": user_id,
                    "did": doc_id,
                    "kb": kb_id,
                    "seq": seq,
                    "content": content,
                    "n": len(content),
                },
            )
        ).scalar_one()
        all_ids.append(cid)
        if seq < 2:
            related_ids.append(cid)
    await db.commit()
    return related_ids, all_ids


async def test_bm25_cache_rebuilds_after_delete_and_reupload() -> None:
    """删文档 + 再上传（chunk 总数不变）后，BM25 索引必须重建、不返回已删 chunk。"""
    user_id, kb_id = await _setup_user_kb()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        bm25._cache.clear()
        async with session_factory() as db:
            # 1. 第一批 chunk：检索一次，建立缓存（版本 = 总数 5 + max id）
            first_related, first_all = await _insert_doc_chunks(
                db, user_id, kb_id, "向量检索知识库测试内容", "苹果香蕉橙子西瓜葡萄"
            )
            hits = [cid for cid, _ in await bm25.bm25_search(db, user_id, [kb_id], "向量检索")]
            assert set(hits) == set(first_related)

            # 2. 删除第一批（中间不检索，缓存保留旧索引）
            for cid in first_all:
                await db.execute(
                    text("DELETE FROM document_chunks WHERE id = :cid"), {"cid": cid}
                )
            await db.commit()

            # 3. 上传第二批：chunk 总数回到 5。
            #    旧版本信号（仅总数）会与缓存碰撞 → 返回已删除 chunk 的脏 id；
            #    新版本信号 (总数, max id) 因 id 单调递增必然变化 → 强制重建。
            second_related, _ = await _insert_doc_chunks(
                db, user_id, kb_id, "向量检索知识库测试内容", "苹果香蕉橙子西瓜葡萄"
            )
            hits = [cid for cid, _ in await bm25.bm25_search(db, user_id, [kb_id], "向量检索")]
            assert set(hits) == set(second_related), "缓存未重建，返回了已删除 chunk 的脏数据"
    finally:
        bm25._cache.clear()
        async with session_factory() as db:
            await db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})
            await db.commit()
        await engine.dispose()
