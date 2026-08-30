from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    conversation_id: int | None = Field(default=None, description="会话 ID，不传则新建会话")
    content: str = Field(default="", max_length=8000)
    # RAG 模式：指定知识库（不传 = 普通对话；传了 = 基于知识库问答）
    knowledge_base_ids: list[int] | None = Field(default=None)
    # 多模态：聊天图片文件名列表（先经 /chat-images 上传获取），最多 3 张，仅普通对话支持
    images: list[str] | None = Field(default=None, max_length=3)

    @model_validator(mode="after")
    def _check_content_or_images(self) -> "ChatRequest":
        if not self.content.strip() and not self.images:
            raise ValueError("content 和 images 不能同时为空")
        return self
