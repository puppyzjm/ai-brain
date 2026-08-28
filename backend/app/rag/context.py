"""Context 组装与引用来源构建。"""

MAX_CONTEXT_CHARS = 4000
PREVIEW_LENGTH = 100


def build_context(chunks: list[dict]) -> tuple[str, list[dict]]:
    """把检索结果组装为 LLM Context 与 sources 列表。

    返回 (context 文本, sources)。chunks 元素结构见 PgVectorStore.search。
    """
    parts: list[str] = []
    sources: list[dict] = []
    total = 0

    for idx, c in enumerate(chunks, start=1):
        text = c["content"]
        if total + len(text) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total
            if remaining < 200:
                break  # 剩余空间太小，不再截断塞入
            text = text[:remaining]
        parts.append(f"[来源{idx}]（{c['filename']}）\n{text}")
        total += len(text)
        sources.append(
            {
                "chunk_id": c["chunk_id"],
                "document_id": c["document_id"],
                "filename": c["filename"],
                "content_preview": c["content"][:PREVIEW_LENGTH],
                "similarity": c["similarity"],
                "page": (c.get("metadata") or {}).get("page"),
            }
        )
        if total >= MAX_CONTEXT_CHARS:
            break

    return "\n\n".join(parts), sources
