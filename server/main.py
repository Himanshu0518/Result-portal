from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.core import (
    ApiError,
    api_error_handler,
    validation_error_handler,
    unhandled_error_handler,
)
from app.api import router as api_router

app = FastAPI(title="Result Portal API")

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api")

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
