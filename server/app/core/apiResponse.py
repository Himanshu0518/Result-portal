"""
Uniform success-response helpers.

Every successful API response has this envelope:

    {
        "success": true,
        "message": "...",          # optional human-readable note
        "data": <payload>,         # None for 204-style responses
        "meta": {                  # optional — used for paginated lists
            "page": 1,
            "page_size": 20,
            "total": 500
        }
    }

Usage
-----
    # Simple object
    return ApiResponse.ok(student)

    # With a custom message
    return ApiResponse.created(import_summary, message="File imported successfully.")

    # Paginated list
    return ApiResponse.paginated(items, total=500, page=2, page_size=20)

    # 204-style (no body content)
    return ApiResponse.no_content()
"""
from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


class ApiResponse:
    """Factory for uniform JSON success responses."""

    # ------------------------------------------------------------------
    # Core builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build(
        *,
        status_code: int,
        data: Any = None,
        message: str = "",
        meta: dict[str, Any] | None = None,
    ) -> JSONResponse:
        body: dict[str, Any] = {"success": True}
        if message:
            body["message"] = message
        body["data"] = data
        if meta is not None:
            body["meta"] = meta
        return JSONResponse(status_code=status_code, content=body)

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    @classmethod
    def ok(
        cls,
        data: Any = None,
        *,
        message: str = "",
    ) -> JSONResponse:
        """200 OK — standard fetch / update response."""
        return cls._build(status_code=200, data=data, message=message)

    @classmethod
    def created(
        cls,
        data: Any = None,
        *,
        message: str = "",
    ) -> JSONResponse:
        """201 Created — resource was successfully created."""
        return cls._build(status_code=201, data=data, message=message)

    @classmethod
    def accepted(
        cls,
        data: Any = None,
        *,
        message: str = "",
    ) -> JSONResponse:
        """202 Accepted — work was queued for background processing."""
        return cls._build(status_code=202, data=data, message=message)

    @classmethod
    def paginated(
        cls,
        items: list[Any],
        *,
        total: int,
        page: int,
        page_size: int,
        message: str = "",
    ) -> JSONResponse:
        """200 OK with pagination metadata in ``meta``."""
        return cls._build(
            status_code=200,
            data=items,
            message=message,
            meta={"page": page, "page_size": page_size, "total": total},
        )

    @classmethod
    def no_content(cls) -> JSONResponse:
        """204 No Content — action succeeded with nothing to return."""
        return JSONResponse(status_code=204, content=None)
