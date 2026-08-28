"""Document Loader：从文件提取文本（PDF 按页返回，TXT/MD 整篇返回）。"""
try:
    import pymupdf as fitz  # PyMuPDF 新版本推荐
except ImportError:  # 兼容旧版本
    import fitz

SUPPORTED_TYPES = {"pdf", "txt", "markdown"}


def load_text(path: str, file_type: str) -> list[dict]:
    """提取文本，返回 [{text, metadata}] 分段列表。"""
    if file_type == "pdf":
        return _load_pdf(path)
    if file_type in ("txt", "markdown"):
        return _load_text_file(path)
    raise ValueError(f"不支持的文件类型: {file_type}")


def _load_pdf(path: str) -> list[dict]:
    sections: list[dict] = []
    with fitz.open(path) as doc:
        for page_index in range(len(doc)):
            text = doc[page_index].get_text("text")
            if text.strip():
                sections.append({"text": text, "metadata": {"page": page_index + 1}})
    return sections


def _load_text_file(path: str) -> list[dict]:
    text = _read_with_encoding_detection(path)
    return [{"text": text, "metadata": {}}]


def _read_with_encoding_detection(path: str) -> str:
    """按 UTF-8 → GBK 顺序探测编码，均失败时用替换模式兜底。"""
    with open(path, "rb") as f:
        raw = f.read()
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")
