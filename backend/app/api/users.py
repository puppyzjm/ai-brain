from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.response import ok
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户资料。"""
    return ok(UserResponse.model_validate(current_user).model_dump(mode="json"))
