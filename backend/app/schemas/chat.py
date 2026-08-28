from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: int | None = Field(default=None, description="会话 ID，不传则新建会话")
    content: str = Field(min_length=1, max_length=8000)
    # RAG 模式：指定知识库（不传 = 普通对话；传了 = 基于知识库问答）
    knowledge_base_ids: list[int] | None = Field(default=None)
