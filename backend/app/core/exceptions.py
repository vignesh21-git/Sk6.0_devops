import uuid
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = structlog.get_logger(__name__)


class DomainError(Exception):
    code: str = "DOMAIN_ERROR"
    message: str = "A domain error occurred"
    http_status: int = 400

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    message = "Resource not found"
    http_status = 404


class ConflictError(DomainError):
    code = "CONFLICT"
    message = "Conflicting state"
    http_status = 409


class AuthenticationError(DomainError):
    code = "AUTHENTICATION_FAILED"
    message = "Authentication failed"
    http_status = 401


class AuthorizationError(DomainError):
    code = "AUTHORIZATION_FAILED"
    message = "Not authorized"
    http_status = 403


class InvariantViolation(DomainError):
    code = "INVARIANT_VIOLATION"
    message = "A business invariant was violated"
    http_status = 422


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID") or str(uuid.uuid4())


def _envelope(
    *, code: str, message: str, details: dict, request_id: str, status: int
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError):
        rid = _request_id(request)
        log.warning(
            "domain_error",
            code=exc.code,
            message=exc.message,
            request_id=rid,
            path=request.url.path,
        )
        return _envelope(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=rid,
            status=exc.http_status,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        rid = _request_id(request)
        return _envelope(
            code="VALIDATION_ERROR",
            message="Invalid request payload",
            details={"errors": exc.errors()},
            request_id=rid,
            status=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        rid = _request_id(request)
        return _envelope(
            code="HTTP_ERROR",
            message=str(exc.detail),
            details={},
            request_id=rid,
            status=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        rid = _request_id(request)
        log.exception(
            "unhandled_exception", request_id=rid, path=request.url.path
        )
        return _envelope(
            code="INTERNAL_ERROR",
            message="An internal error occurred",
            details={},
            request_id=rid,
            status=500,
        )
