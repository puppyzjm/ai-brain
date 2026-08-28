"""AI 用量统计聚合查询（按 user_id 隔离）。"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_usage_log import AiUsageLog


class StatsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self, user_id: int) -> dict:
        """总请求数 / 成功率 / token 汇总 / 平均耗时。"""
        stmt = select(
            func.count(AiUsageLog.id),
            func.coalesce(
                func.sum(case((AiUsageLog.status == "success", 1), else_=0)), 0
            ),
            func.coalesce(func.sum(AiUsageLog.prompt_tokens), 0),
            func.coalesce(func.sum(AiUsageLog.completion_tokens), 0),
            func.coalesce(func.sum(AiUsageLog.total_tokens), 0),
            func.coalesce(func.avg(AiUsageLog.latency_ms), 0),
        ).where(AiUsageLog.user_id == user_id)
        total, success, prompt, completion, total_tokens, avg_latency = (
            await self.db.execute(stmt)
        ).one()

        return {
            "total_requests": int(total or 0),
            "success_count": int(success or 0),
            "failed_count": int(total or 0) - int(success or 0),
            "success_rate": round(int(success or 0) / int(total or 0) * 100, 1) if total else 100.0,
            "prompt_tokens": int(prompt or 0),
            "completion_tokens": int(completion or 0),
            "total_tokens": int(total_tokens or 0),
            "avg_latency_ms": int(avg_latency or 0),
        }

    async def get_by_type(self, user_id: int) -> list[dict]:
        """按用途类型聚合（chat/rag/agent/summary）。"""
        stmt = (
            select(
                AiUsageLog.type,
                func.count(AiUsageLog.id),
                func.coalesce(func.sum(AiUsageLog.total_tokens), 0),
            )
            .where(AiUsageLog.user_id == user_id)
            .group_by(AiUsageLog.type)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {"type": r[0], "count": int(r[1]), "total_tokens": int(r[2])} for r in rows
        ]

    async def get_daily(self, user_id: int, days: int = 7) -> list[dict]:
        """近 N 天每日请求数与 token（按 UTC 日期）。"""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                func.date(AiUsageLog.created_at).label("day"),
                func.count(AiUsageLog.id),
                func.coalesce(func.sum(AiUsageLog.total_tokens), 0),
            )
            .where(AiUsageLog.user_id == user_id, AiUsageLog.created_at >= since)
            .group_by("day")
            .order_by("day")
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {"date": str(r[0]), "count": int(r[1]), "total_tokens": int(r[2])}
            for r in rows
        ]
