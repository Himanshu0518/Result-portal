import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
