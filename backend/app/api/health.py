from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.health import HealthResponse
from app.services import health as health_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> JSONResponse:
    """健康检查：FastAPI + PostgreSQL + Redis。"""
    db_ok = await health_service.check_database()
    redis_ok = await health_service.check_redis()

    status = "ok" if db_ok and redis_ok else "degraded"
    status_code = 200 if status == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    )
