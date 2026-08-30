"""聊天图片接口：上传（多模态对话附图）+ 鉴权读取。"""
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.core.response import ok
from app.infrastructure.storage import (
    EXT_TO_IMAGE_MIME,
    resolve_chat_image_path,
    save_chat_image,
)
from app.models.user import User

router = APIRouter(prefix="/chat-images", tags=["chat-images"])


@router.post("")
async def upload_chat_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传聊天附图（PNG/JPG/WebP，≤5MB，魔数校验），返回存储文件名。

    文件名随后放入 POST /chat 的 images 列表，用于多模态问答。
    """
    content = await file.read()
    name = save_chat_image(current_user.id, content)
    return ok({"name": name})


@router.get("/{name}")
async def get_chat_image(
    name: str,
    current_user: User = Depends(get_current_user),
):
    """按文件名读取自己上传的图片（JWT 鉴权 + 用户目录隔离）。"""
    path = resolve_chat_image_path(current_user.id, name)
    if path is None:
        raise NotFoundError("图片不存在")
    ext = path.suffix.lower()
    return FileResponse(
        path,
        media_type=EXT_TO_IMAGE_MIME.get(ext, "application/octet-stream"),
    )
