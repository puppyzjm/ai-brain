"""文档解析 Pipeline：文件 → 文本 → 清洗 → chunks。"""
from app.document import cleaner, loader, splitter


def extract_chunks(path: str, file_type: str) -> list[tuple[str, dict]]:
    """解析文件并切分，返回 [(chunk_text, metadata), ...]。"""
    sections = loader.load_text(path, file_type)
    chunks: list[tuple[str, dict]] = []
    for section in sections:
        text = cleaner.clean_text(section["text"])
        if not text:
            continue
        for chunk_text in splitter.split_text(text):
            chunks.append((chunk_text, dict(section["metadata"])))
    return chunks
