"""Domain exceptions and global exception handlers.

Every error surfaced to a client goes through the standard response envelope
so the mobile app can rely on one consistent shape.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger("scfms")


class AppError(Exception):
    """Base class for all handled application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "app_error"

    def __init__(self, message: str, *, error_code: str | None = None):
        self.message = message
        if error_code:
            self.error_code = error_code
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_failed"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "permission_denied"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_error"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limited"


def _clean_validation_errors(errors: list[dict]) -> list[dict]:
    """Strip non-JSON-serializable objects (e.g. raw exceptions in pydantic's
    ``ctx``) so the error envelope always serializes cleanly."""
    cleaned: list[dict] = []
    for err in errors:
        item = {k: v for k, v in err.items() if k != "ctx"}
        if "ctx" in err and isinstance(err["ctx"], dict):
            item["ctx"] = {k: str(v) for k, v in err["ctx"].items()}
        cleaned.append(item)
    return cleaned


def _envelope(*, message: str, error_code: str, details: object | None = None) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": error_code, "message": message, "details": details},
        "meta": None,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(message=exc.message, error_code=exc.error_code),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope(
                message="Request validation failed",
                error_code="validation_error",
                details=_clean_validation_errors(exc.errors()),
            ),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("IntegrityError: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_envelope(
                message="The operation conflicts with existing data.",
                error_code="conflict",
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope(message="A database error occurred.", error_code="db_error"),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope(
                message="An unexpected error occurred.", error_code="internal_error"
            ),
        )
