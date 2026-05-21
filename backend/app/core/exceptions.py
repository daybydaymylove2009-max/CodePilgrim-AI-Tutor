from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, detail: Any = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str = ""):
        msg = f"{resource} not found" + (f": {resource_id}" if resource_id else "")
        super().__init__(code="NOT_FOUND", message=msg, status_code=404)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(code="CONFLICT", message=message, status_code=409)


class RateLimitError(AppError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(code="RATE_LIMIT", message=message, status_code=429)


class ExternalServiceError(AppError):
    def __init__(self, service: str, message: str = ""):
        msg = f"External service error: {service}" + (f" - {message}" if message else "")
        super().__init__(code="EXTERNAL_SERVICE_ERROR", message=msg, status_code=502)


class SandboxError(AppError):
    def __init__(self, message: str):
        super().__init__(code="SANDBOX_ERROR", message=message, status_code=500)


def _format_error(code: str, message: str, detail: Any = None, request_id: str = "") -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
            "request_id": request_id,
        }
    }


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    logger.warning(f"AppError [{exc.code}]: {exc.message} | request_id={request_id}")
    return JSONResponse(
        status_code=exc.status_code,
        content=_format_error(exc.code, exc.message, exc.detail, request_id),
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    request_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    logger.warning(f"ValidationError | request_id={request_id}")
    return JSONResponse(
        status_code=422,
        content=_format_error("VALIDATION_ERROR", "Request validation failed", exc.errors(), request_id),
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    request_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    logger.error(f"DatabaseError | request_id={request_id} | {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content=_format_error("DATABASE_ERROR", "A database error occurred", None, request_id),
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    logger.exception(f"UnhandledException | request_id={request_id} | {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content=_format_error("INTERNAL_ERROR", "An unexpected error occurred", None, request_id),
    )
