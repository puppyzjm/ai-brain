"""文档解析 Pipeline：文件 → 文本 → 清洗 → chunks。"""
from app.document import cleaner, loader, splitter


def chunks_from_sections(sections: list[dict]) -> list[tuple[str, dict]]:
    """对 (text, metadata) 段列表做清洗+切分，返回 [(chunk_text, metadata), ...]。"""
    chunks: list[tuple[str, dict]] = []
    for section in sections:
        text = cleaner.clean_text(section["text"])
        if not text:
            continue
        for chunk_text in splitter.split_text(text):
            chunks.append((chunk_text, dict(section["metadata"])))
    return chunks


def extract_chunks(path: str, file_type: str) -> list[tuple[str, dict]]:
    """解析文件并切分，返回 [(chunk_text, metadata), ...]。"""
    sections = loader.load_text(path, file_type)
    return chunks_from_sections(sections)
