"""
Uniform error-response system.

Every error response — regardless of origin — has this envelope:

    {
        "success": false,
        "error": {
            "code":    "NOT_FOUND",          # machine-readable constant
            "message": "Student not found.", # human-readable, shown in the UI
            "details": [...]                 # optional — validation field errors
        }
    }

Exception hierarchy
-------------------
    ApiError                    base; maps to HTTP 500 by default
    ├── BadRequestError         400 — malformed input, failed business rules
    ├── ValidationError         422 — field-level validation failures
    ├── NotFoundError           404 — resource does not exist
    ├── ConflictError           409 — duplicate / state conflict
    └── UnprocessableFileError  422 — file-level import errors (bad CSV, wrong type…)

Registering the handler
-----------------------
In ``main.py``:

    from app.core.apiError import ApiError, api_error_handler, validation_error_handler
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

Usage
-----
    raise NotFoundError(f"Student '{student_id}' not found.")
    raise BadRequestError("File exceeds the 10 MB size limit.", code="FILE_TOO_LARGE")
    raise ValidationError("Validation failed.", details=[{"field": "email", "message": "Invalid format."}])
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class ApiError(Exception):
    """Base class for all application errors.

    Parameters
    ----------
    message:
        Human-readable description shown to the caller.
    code:
        Machine-readable constant (defaults to the class default).
    status_code:
        HTTP status code (defaults to the class default).
    details:
        Optional list of supplementary objects — e.g. per-field validation
        errors: ``[{"field": "email", "message": "Invalid format."}]``.
    """

    status_code: int = 500
    default_code: str = "INTERNAL_SERVER_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or []

    def to_response(self) -> JSONResponse:
        body: dict[str, Any] = {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
            },
        }
        if self.details:
            body["error"]["details"] = self.details
        return JSONResponse(status_code=self.status_code, content=body)


class BadRequestError(ApiError):
    """400 — the request is syntactically valid but semantically wrong."""
    status_code = 400
    default_code = "BAD_REQUEST"


class NotFoundError(ApiError):
    """404 — the requested resource does not exist."""
    status_code = 404
    default_code = "NOT_FOUND"


class ConflictError(ApiError):
    """409 — the request conflicts with current state (e.g. duplicate)."""
    status_code = 409
    default_code = "CONFLICT"


class ValidationError(ApiError):
    """422 — one or more fields failed validation.

    ``details`` should be a list of ``{"field": str, "message": str}`` dicts.
    """
    status_code = 422
    default_code = "VALIDATION_ERROR"


class UnprocessableFileError(ApiError):
    """422 — the uploaded file is structurally invalid (not a CSV, missing
    required columns, binary content, etc.).  Row-level errors are returned
    in the normal 200 import summary, not here."""
    status_code = 422
    default_code = "UNPROCESSABLE_FILE"


# ---------------------------------------------------------------------------
# FastAPI exception handlers
# ---------------------------------------------------------------------------

async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    """Handler for all ``ApiError`` subclasses.

    Log 5xx errors as ERROR, 4xx as WARNING so the noise level is appropriate.
    """
    if exc.status_code >= 500:
        logger.error(
            "ApiError %s on %s %s: %s",
            exc.code,
            request.method,
            request.url.path,
            exc.message,
            exc_info=exc,
        )
    else:
        logger.warning(
            "ApiError %s on %s %s: %s",
            exc.code,
            request.method,
            request.url.path,
            exc.message,
        )
    return exc.to_response()


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler for FastAPI / Pydantic request-body validation errors.

    Converts Pydantic's nested error list into the same flat
    ``[{"field": "...", "message": "..."}]`` shape used by ``ValidationError``.
    """
    details = [
        {
            "field": " → ".join(str(loc) for loc in err["loc"] if loc != "body"),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    logger.warning(
        "RequestValidationError on %s %s: %d field(s)",
        request.method,
        request.url.path,
        len(details),
    )
    body: dict[str, Any] = {
        "success": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": details,
        },
    }
    return JSONResponse(status_code=422, content=body)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for any exception not covered by the above handlers.

    Logs the full traceback but returns a generic message to the caller
    so internal details are never leaked.
    """
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    body: dict[str, Any] = {
        "success": False,
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        },
    }
    return JSONResponse(status_code=500, content=body)
