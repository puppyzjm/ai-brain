"""应用配置：从环境变量 / .env 读取。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Brain API"
    debug: bool = False

    # 数据库 / Redis
    database_url: str = "postgresql+asyncpg://aibrain:aibrain@localhost:5432/aibrain"
    redis_url: str = "redis://localhost:6379/0"

    # 安全
    jwt_secret_key: str = "dev-secret-change-me"

    # AI：LLM（DeepSeek）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # AI：Embedding（SiliconFlow BGE-M3）
    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "BAAI/bge-m3"

    # OCR（扫描版 PDF 文字提取，复用 SiliconFlow 同平台账号）
    ocr_model: str = "deepseek-ai/DeepSeek-OCR"

    # 视觉（多模态图片问答，复用 SiliconFlow 同平台账号）
    vision_model: str = "Qwen/Qwen3-VL-32B-Instruct"

    # 文件存储（用户上传文档）
    upload_dir: str = "uploads"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sync_database_url(self) -> str:
        """Alembic 使用同步驱动（psycopg2）。"""
        return self.database_url.replace("+asyncpg", "+psycopg2")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
