from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    RateLimitError,
    ExternalServiceError,
    SandboxError,
    app_error_handler,
    validation_error_handler,
    sqlalchemy_error_handler,
    generic_error_handler,
)
from app.core.middleware import CorrelationIdMiddleware, RequestLoggingMiddleware
from app.core.cache import redis_service
from app.models import init_db

import app.core.logging as _logging


limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    logger.info("Database initialized")
    yield
    await redis_service.close()
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="CodePilgrim - AI驱动的沉浸式编程伴学系统 | Vibe为帆，代码为舵",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RateLimitError, app_error_handler)
app.add_exception_handler(NotFoundError, app_error_handler)
app.add_exception_handler(UnauthorizedError, app_error_handler)

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

app.include_router(api_router)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health/live")
async def liveness_probe():
    return {"status": "alive", "version": settings.APP_VERSION}


@app.get("/health/ready")
async def readiness_probe():
    checks = {"database": False, "redis": False}

    try:
        from app.db.session import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    try:
        checks["redis"] = await redis_service.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_healthy else "degraded",
            "version": settings.APP_VERSION,
            "checks": checks,
        },
    )


@app.get("/health")
async def health_check():
    return await readiness_probe()
