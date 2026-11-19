from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.core import (
    ApiError,
    api_error_handler,
    validation_error_handler,
    unhandled_error_handler,
)

app = FastAPI(title="Result Portal API")

# ── Exception handlers ────────────────────────────────────────────────────────
# All ApiError subclasses (NotFoundError, BadRequestError, etc.)
app.add_exception_handler(ApiError, api_error_handler)
# Pydantic / FastAPI request-body validation failures
app.add_exception_handler(RequestValidationError, validation_error_handler)
# Anything else — log the traceback, return a generic 500
app.add_exception_handler(Exception, unhandled_error_handler)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
