"""文件存储：类型/大小校验 + UUID 命名保存。"""
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AppException

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
EXT_TO_TYPE = {".pdf": "pdf", ".txt": "txt", ".md": "markdown"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


def get_upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(content: bytes, original_filename: str) -> tuple[str, str, int]:
    """保存上传内容，返回 (stored_path, file_type, file_size)。"""
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AppException(
            code=4004, message="不支持的文件类型，仅支持 PDF / TXT / Markdown", http_status=400
        )
    if len(content) > MAX_FILE_SIZE:
        raise AppException(code=4005, message="文件大小超过 20MB 限制", http_status=400)

    file_type = EXT_TO_TYPE[ext]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = get_upload_dir() / stored_name
    stored_path.write_bytes(content)
    return str(stored_path), file_type, len(content)
