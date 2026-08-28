"""个人用量统计业务逻辑。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stats import StatsRepository


async def get_usage_stats(db: AsyncSession, user_id: int) -> dict:
    repo = StatsRepository(db)
    return {
        "summary": await repo.get_summary(user_id),
        "by_type": await repo.get_by_type(user_id),
        "daily": await repo.get_daily(user_id),
    }
