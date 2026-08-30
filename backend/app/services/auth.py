"""注册 / 登录 / 刷新 / 登出业务逻辑。"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
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


async def login(db: AsyncSession, account: str, password: str) -> dict:
    """校验账号密码，签发双 token（access 30 分钟 + refresh 30 天）。"""
    repo = UserRepository(db)
    user = await repo.get_by_username_or_email(account)
    if user is None or not verify_password(password, user.password_hash):
        # 不区分「用户不存在」与「密码错误」，避免账号枚举
        raise AppException(code=4003, message="用户名或密码错误", http_status=401)

    raw_refresh, token_hash, expires_at = generate_refresh_token()
    await RefreshTokenRepository(db).create(user.id, token_hash, expires_at)
    await db.commit()

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": raw_refresh,
    }


async def refresh(db: AsyncSession, raw_refresh: str) -> dict:
    """刷新 access token（轮换：旧 refresh 立即作废，签发新 refresh，防重放）。"""
    token_hash = hash_refresh_token(raw_refresh)
    repo = RefreshTokenRepository(db)
    record = await repo.get_by_hash(token_hash)

    if record is None:
        raise UnauthorizedError("刷新令牌无效")
    if record.expires_at < datetime.now(timezone.utc):
        await repo.delete_by_hash(token_hash)
        await db.commit()
        raise UnauthorizedError("刷新令牌已过期，请重新登录")

    # 轮换：删除旧令牌，签发新令牌（同一用户）
    await repo.delete_by_hash(token_hash)
    raw_new, new_hash, new_expires = generate_refresh_token()
    await repo.create(record.user_id, new_hash, new_expires)
    await db.commit()

    return {
        "access_token": create_access_token(record.user_id),
        "refresh_token": raw_new,
    }


async def logout(db: AsyncSession, raw_refresh: str) -> None:
    """登出：撤销该 refresh token（若提供），使轮换链断裂。"""
    if raw_refresh:
        await RefreshTokenRepository(db).delete_by_hash(hash_refresh_token(raw_refresh))
        await db.commit()
