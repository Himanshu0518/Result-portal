"""Logging setup for the API.

The server emits one line per event instead of SQLAlchemy's multi-line SQL
dumps. Requests are logged by ``RequestLogMiddleware`` in ``main.py``:

    18:06:50.588 INFO     app.request | GET /api/students?q=rohit 200 12.4ms request=ab12cd34

SQL statements are only echoed when ``SQL_ECHO=true``; set ``LOG_LEVEL`` to
change the root level (default ``INFO``).
"""
from __future__ import annotations

import logging
import uuid
from logging.config import dictConfig
from typing import Any

from app.config.env import settings

LOG_FORMAT = "%(asctime)s %(levelname)-5s %(name)s | %(message)s"
DATE_FORMAT = "%H:%M:%S"


def configure_logging() -> None:
    """Install a single compact console format and quiet noisy libraries."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {"format": LOG_FORMAT, "datefmt": DATE_FORMAT},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "console",
                    "stream": "ext://sys.stderr",
                },
            },
            "root": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL.upper(),
            },
            "loggers": {
                # Uvicorn startup/shutdown messages keep the same format...
                "uvicorn": {"handlers": ["console"], "level": "INFO", "propagate": False},
                "uvicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
                # ...but its request line is replaced by our own middleware so
                # each request also carries a request id and a duration.
                "uvicorn.access": {"handlers": [], "level": "WARNING", "propagate": False},
                # SQL is opt-in: it is useful when debugging a query, not while
                # clicking through the UI.
                "sqlalchemy.engine": {
                    "handlers": [],
                    "level": "INFO" if settings.SQL_ECHO else "WARNING",
                    "propagate": True,
                },
                "sqlalchemy.pool": {"handlers": [], "level": "WARNING", "propagate": True},
                "httpx": {"handlers": [], "level": "WARNING", "propagate": True},
                "watchfiles": {"handlers": [], "level": "WARNING", "propagate": True},
            },
        }
    )


def new_request_id() -> str:
    """Short id that ties a request line to the errors it produced."""
    return uuid.uuid4().hex[:8]


def get_request_id(request: Any) -> str:
    """Request id set by ``RequestLogMiddleware``, or ``-`` outside a request."""
    return getattr(request.state, "request_id", "-")
