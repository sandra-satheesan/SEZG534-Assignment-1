"""Safe, centralized HTTP error handling."""

from __future__ import annotations

from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.responses import ErrorDetail, ErrorResponse


class ApplicationError(Exception):
    status_code = 500
    error_code = "internal_error"
    public_message = "Internal server error."

    def __init__(self, internal_detail: str | None = None) -> None:
        super().__init__(internal_detail or self.public_message)


class ProviderOutputError(ApplicationError):
    status_code = 502
    error_code = "provider_error"
    public_message = "The model provider returned an invalid response."


class ProviderUnavailableError(ApplicationError):
    status_code = 503
    error_code = "provider_unavailable"
    public_message = "Provider unavailable."


class ProviderTimeoutError(ApplicationError):
    status_code = 504
    error_code = "provider_timeout"
    public_message = "The model provider timed out."


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


async def handle_application_error(request: Request, exc: Exception) -> JSONResponse:
    error = cast(ApplicationError, exc)
    return _error_response(error.status_code, error.error_code, error.public_message)


async def handle_request_validation_error(
    request: Request, exc: Exception
) -> JSONResponse:
    return _error_response(422, "invalid_request", "Request validation failed.")


async def handle_http_error(request: Request, exc: Exception) -> JSONResponse:
    http_error = cast(StarletteHTTPException, exc)
    if http_error.status_code == 404:
        return _error_response(404, "not_found", "Resource not found.")
    if http_error.status_code == 405:
        return _error_response(405, "method_not_allowed", "Method not allowed.")
    return _error_response(http_error.status_code, "request_failed", "Request failed.")


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(500, "internal_error", "Internal server error.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, handle_application_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)