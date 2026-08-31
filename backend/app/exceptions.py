"""Custom application exceptions and their FastAPI exception handlers.

Handlers are registered on the app instance in `app.main.create_app`.
Routers/services should raise these exceptions instead of `HTTPException`
so error handling stays centralized and consistent.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all application-level errors."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: Any = None) -> None:
        detail = f"{resource} not found"
        if identifier is not None:
            detail = f"{resource} with id '{identifier}' not found"
        super().__init__(detail, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    """Raised when an action conflicts with the current state of a resource."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFLICT", status_code=status.HTTP_409_CONFLICT)


class ValidationAppError(AppError):
    """Raised for domain-level validation failures (distinct from Pydantic's)."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message, code="VALIDATION_ERROR", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle any `AppError` subclass (NotFoundError, ConflictError, ...)."""
    logger.warning(
        "Application error on %s %s: %s (%s)",
        request.method,
        request.url.path,
        exc.message,
        exc.code,
    )
    return _error_response(exc.code, exc.message, exc.status_code)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler so unexpected errors never leak stack traces to clients."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return _error_response(
        "INTERNAL_SERVER_ERROR",
        "An unexpected error occurred.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire up all custom exception handlers on the given FastAPI app."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
