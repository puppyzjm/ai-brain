"""FastAPI 依赖注入：当前登录用户。"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.infrastructure.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Authorization: Bearer <token> 解析并加载当前用户。

    - 无凭证 / token 无效 / 用户不存在 → 401（统一错误码 4010）
    - 用户数据隔离铁律：业务层一律使用这里返回的 user.id，不信任前端传入的 user_id
    """
    if credentials is None:
        raise UnauthorizedError()
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise UnauthorizedError("Token 无效或已过期")
    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("用户不存在")
    return user
