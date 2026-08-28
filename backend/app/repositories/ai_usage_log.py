"""AI 用量日志数据访问层。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_usage_log import AiUsageLog


class AiUsageLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        conversation_id: int | None,
        type_: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        status: str,
        error_message: str | None = None,
    ) -> AiUsageLog:
        log = AiUsageLog(
            user_id=user_id,
            conversation_id=conversation_id,
            type=type_,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.flush()
        return log
