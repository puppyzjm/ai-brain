"""Agent 工具调用记录数据访问层。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_tool_call import AgentToolCall


class AgentToolCallRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        conversation_id: int | None,
        message_id: int | None,
        tool_name: str,
        arguments: dict,
        result: dict | None,
        status: str,
        error_message: str | None,
        latency_ms: int,
    ) -> AgentToolCall:
        record = AgentToolCall(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status=status,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        self.db.add(record)
        await self.db.flush()
        return record
