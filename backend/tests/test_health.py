"""基础测试：健康检查、数据库连接、Redis 连接。"""
from httpx import AsyncClient

from app.services import health as health_service


async def test_health_endpoint_returns_valid_structure(client: AsyncClient) -> None:
    """/health 应返回结构正确的 JSON（DB/Redis 可用时 200，否则 503）。"""
    resp = await client.get("/health")
    assert resp.status_code in (200, 503)

    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert body["database"] in ("ok", "error")
    assert body["redis"] in ("ok", "error")


async def test_database_connection_returns_bool() -> None:
    """数据库连接检查应返回布尔值，不抛异常。"""
    result = await health_service.check_database()
    assert isinstance(result, bool)


async def test_redis_connection_returns_bool() -> None:
    """Redis 连接检查应返回布尔值，不抛异常。"""
    result = await health_service.check_redis()
    assert isinstance(result, bool)
