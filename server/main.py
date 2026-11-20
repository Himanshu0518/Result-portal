import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core import (
    ApiError,
    api_error_handler,
    validation_error_handler,
    unhandled_error_handler,
)
from app.core.logging import configure_logging, new_request_id
from app.api import router as api_router

# Configure logging before anything else runs so startup output is consistent.
configure_logging()

logger = logging.getLogger("app.request")

app = FastAPI(title="Result Portal API")


# ── Request logging ───────────────────────────────────────────────────────────
@app.middleware("http")
async def log_request(request: Request, call_next):
    """Log exactly one line per request, with its id, status and duration."""
    request.state.request_id = new_request_id()
    started = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - started) * 1000
        logger.error(
            "%s %s failed after %.1fms request=%s",
            request.method,
            request.url.path,
            elapsed,
            request.state.request_id,
        )
        raise

    elapsed = (time.perf_counter() - started) * 1000
    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"

    logger.log(
        logging.ERROR if response.status_code >= 500 else logging.INFO,
        "%s %s %d %.1fms request=%s",
        request.method,
        target,
        response.status_code,
        elapsed,
        request.state.request_id,
    )
    response.headers["X-Request-ID"] = request.state.request_id
    return response


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

# ── Serve React SPA (production) ─────────────────────────────────────────────
_client_dist = os.path.join(os.path.dirname(__file__), "..", "client", "dist")

if os.path.isdir(_client_dist):
    # Serve hashed JS/CSS bundles at /assets
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(_client_dist, "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Serve static files from client/dist; fall back to index.html for SPA routing."""
        file_path = os.path.join(_client_dist, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_client_dist, "index.html"))
