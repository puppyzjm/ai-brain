"""OCR 服务：扫描版 PDF 页面 → 渲染图片 → 视觉模型提取文字。

复用 SiliconFlow 平台（与 Embedding 同账号同 Key），模型由 OCR_MODEL 配置。
openai SDK 仅在本模块内部使用（铁律 R2）。
"""
import base64

import fitz  # PyMuPDF

from openai import AsyncOpenAI


class PdfOcrService:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @property
    def model(self) -> str:
        return self._model

    async def ocr_pages(self, pdf_path: str, page_indexes: list[int]) -> dict[int, str]:
        """对指定页做 OCR，返回 {页码(从1起): 提取文本}。"""
        results: dict[int, str] = {}
        doc = fitz.open(pdf_path)
        try:
            for page_index in page_indexes:
                page = doc[page_index]
                # 渲染为 PNG（200 DPI 保证中文识别质量）
                pix = page.get_pixmap(dpi=200)
                png_bytes = pix.tobytes("png")
                b64 = base64.b64encode(png_bytes).decode("ascii")

                resp = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                                },
                                # DeepSeek-OCR 官方推荐提示词
                                {"type": "text", "text": "<image>\nFree OCR."},
                            ],
                        }
                    ],
                    max_tokens=2048,
                )
                text = (resp.choices[0].message.content or "").strip()
                if text:
                    results[page_index + 1] = text
        finally:
            doc.close()
        return results
