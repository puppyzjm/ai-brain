"""个人用量统计接口。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.response import ok
from app.infrastructure.database import get_db
from app.models.user import User
from app.services import stats as stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/usage")
async def usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """个人 AI 使用量统计：汇总 / 按类型 / 近 7 天趋势。"""
    data = await stats_service.get_usage_stats(db, current_user.id)
    return ok(data)
