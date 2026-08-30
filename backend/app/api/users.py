from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.core.response import ok
from app.infrastructure.database import get_db
from app.infrastructure.storage import (
    EXT_TO_IMAGE_MIME,
    resolve_avatar_path,
    save_avatar,
)
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户资料。"""
    return ok(UserResponse.model_validate(current_user).model_dump(mode="json"))


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传/更换头像（PNG/JPG/WebP，≤5MB，魔数校验）。

    上传新头像后自动删除旧头像文件（磁盘清理）。
    """
    content = await file.read()
    new_name = save_avatar(current_user.id, content)

    if current_user.avatar:
        old_path = resolve_avatar_path(current_user.id, current_user.avatar)
        if old_path is not None:
            old_path.unlink(missing_ok=True)

    current_user.avatar = new_name
    await db.commit()
    return ok({"avatar": new_name})


@router.delete("/avatar")
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除头像（同时清理磁盘文件）。"""
    if current_user.avatar:
        old_path = resolve_avatar_path(current_user.id, current_user.avatar)
        if old_path is not None:
            old_path.unlink(missing_ok=True)
        current_user.avatar = None
        await db.commit()
    return ok(None)


@router.get("/avatar/{name}")
async def get_avatar(
    name: str,
    current_user: User = Depends(get_current_user),
):
    """读取头像（JWT 鉴权 + 用户目录隔离）。"""
    path = resolve_avatar_path(current_user.id, name)
    if path is None:
        raise NotFoundError("头像不存在")
    ext = path.suffix.lower()
    return FileResponse(
        path,
        media_type=EXT_TO_IMAGE_MIME.get(ext, "application/octet-stream"),
    )
