"""Text Splitter：递归字符切分（约 600 字符、overlap 约 100，优先段落/句子边界）。"""

DEFAULT_CHUNK_SIZE = 600
DEFAULT_CHUNK_OVERLAP = 100

# 边界分隔符（按优先级）
_BOUNDARY_SEPARATORS = ("\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", "；", "; ")


def split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """把文本切分为 chunk 列表。"""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            boundary = _find_boundary(text, start, end, chunk_overlap)
            if boundary is not None:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        # 下一段起点：带上 overlap，且必须前进
        start = max(end - chunk_overlap, start + 1)

    return chunks


def _find_boundary(text: str, start: int, end: int, max_lookback: int) -> int | None:
    """在 [end-max_lookback, end) 内找最近的边界位置，返回切割点（不含分隔符）。"""
    lookback_start = max(start + 1, end - max_lookback)
    window = text[lookback_start:end]
    best = -1
    for sep in _BOUNDARY_SEPARATORS:
        idx = window.rfind(sep)
        if idx > best:
            best = idx
    if best < 0:
        return None
    return lookback_start + best
