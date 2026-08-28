"""SiliconFlow Embedding Provider（BGE-M3，OpenAI 兼容协议）。

注意：openai SDK 只允许在本模块内部 import（TDD 铁律 R2）。
"""
from openai import AsyncOpenAI

# BGE-M3 输出维度，与 document_chunks.embedding vector(1024) 一致
DIMENSION = 1024


class SiliconFlowEmbeddingProvider:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return DIMENSION

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化，返回与输入顺序一致的向量列表。"""
        resp = await self._client.embeddings.create(model=self._model, input=texts)
        sorted_data = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in sorted_data]
