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


# ==================== 聊天图片存储（多模态对话临时附图） ====================

MAX_CHAT_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

EXT_TO_IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}


def _detect_image_ext(content: bytes) -> str | None:
    """按文件头魔数识别真实图片类型（不信任扩展名）。"""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


def get_chat_image_dir(user_id: int) -> Path:
    """聊天图片按用户隔离存储。"""
    path = get_upload_dir() / "chat_images" / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_chat_image(user_id: int, content: bytes) -> str:
    """保存聊天图片（魔数校验 + 大小限制 + 用户目录隔离），返回存储文件名。"""
    if not content:
        raise AppException(code=4004, message="图片内容为空", http_status=400)
    if len(content) > MAX_CHAT_IMAGE_SIZE:
        raise AppException(code=4005, message="图片大小超过 5MB 限制", http_status=400)
    ext = _detect_image_ext(content)
    if ext is None:
        raise AppException(
            code=4004, message="仅支持 PNG / JPG / WebP 格式的图片", http_status=400
        )

    name = f"{uuid.uuid4().hex}{ext}"
    (get_chat_image_dir(user_id) / name).write_bytes(content)
    return name


def resolve_chat_image_path(user_id: int, name: str) -> Path | None:
    """按用户目录解析图片路径（防路径穿越）；不存在返回 None。"""
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    path = get_chat_image_dir(user_id) / name
    return path if path.is_file() else None
