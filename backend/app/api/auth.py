from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.infrastructure.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register(db, body.username, body.email, body.password)
    return ok(UserResponse.model_validate(user).model_dump(mode="json"))


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    access_token = await auth_service.login(db, body.account, body.password)
    return ok(TokenResponse(access_token=access_token).model_dump())
