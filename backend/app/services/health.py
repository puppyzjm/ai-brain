"""健康检查业务逻辑。"""
from sqlalchemy import text

from app.infrastructure.database import async_session_factory
from app.infrastructure import redis as redis_infra


async def check_database() -> bool:
    """检查数据库连接是否可用。"""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis() -> bool:
    """检查 Redis 连接是否可用。"""
    return await redis_infra.ping()
