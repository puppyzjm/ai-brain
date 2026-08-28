"""注册 / 登录业务逻辑。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository


async def register(
    db: AsyncSession,
    username: str,
    email: str | None,
    password: str,
) -> User:
    repo = UserRepository(db)
    if await repo.get_by_username(username):
        raise AppException(code=4001, message="用户名已存在", http_status=409)
    if email and await repo.get_by_email(email):
        raise AppException(code=4002, message="邮箱已被注册", http_status=409)

    user = await repo.create(
        username=username,
        email=email,
        password_hash=hash_password(password),
    )
    await db.commit()
    await db.refresh(user)
    return user


async def login(db: AsyncSession, account: str, password: str) -> str:
    """校验账号密码，成功返回 JWT access token。"""
    repo = UserRepository(db)
    user = await repo.get_by_username_or_email(account)
    if user is None or not verify_password(password, user.password_hash):
        # 不区分「用户不存在」与「密码错误」，避免账号枚举
        raise AppException(code=4003, message="用户名或密码错误", http_status=401)
    return create_access_token(user.id)
