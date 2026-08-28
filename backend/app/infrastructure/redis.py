"""Redis 连接（redis-py 异步客户端）。"""
import redis.asyncio as aioredis

from app.core.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def ping() -> bool:
    """Redis 健康检查。"""
    try:
        return bool(await redis_client.ping())
    except Exception:
        return False
