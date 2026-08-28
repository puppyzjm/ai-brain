"""AI Provider 工厂：根据配置创建 Provider 实例。"""
from functools import lru_cache

from app.ai.providers.deepseek import DeepSeekProvider
from app.ai.providers.siliconflow import SiliconFlowEmbeddingProvider
from app.core.config import settings
from app.core.exceptions import AppException


@lru_cache
def get_llm_provider() -> DeepSeekProvider:
    if not settings.deepseek_api_key:
        raise AppException(
            code=6001,
            message="未配置 DEEPSEEK_API_KEY，请在 .env 中填写后重启服务",
            http_status=503,
        )
    return DeepSeekProvider(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
    )


@lru_cache
def get_embedding_provider() -> SiliconFlowEmbeddingProvider:
    if not settings.embedding_api_key:
        raise AppException(
            code=6002,
            message="未配置 EMBEDDING_API_KEY，请在 .env 中填写后重启服务",
            http_status=503,
        )
    return SiliconFlowEmbeddingProvider(
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        model=settings.embedding_model,
    )
