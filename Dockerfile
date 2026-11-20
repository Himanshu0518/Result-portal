# =============================================================================
# Result Portal — Multi-stage Dockerfile
# Single container: React SPA + FastAPI backend on port 8000
#
# Build:  docker build -t result-portal .
# Run:    docker run -p 8000:8000 -v portal-data:/app/server/data result-portal
# Open:   http://localhost:8000
# =============================================================================


# -----------------------------------------------------------------------------
# Stage 1 — Build the React SPA
# -----------------------------------------------------------------------------
FROM node:22-slim AS build

WORKDIR /app/client

# Enable pnpm via corepack (ships with Node 22)
RUN corepack enable

# Install dependencies first so this layer is cached when only source changes
COPY client/package.json client/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copy source and build
COPY client/ ./
RUN pnpm build
# Output: /app/client/dist


# -----------------------------------------------------------------------------
# Stage 2 — Python runtime
# -----------------------------------------------------------------------------
FROM python:3.13-slim

# gosu: minimal privilege-drop tool used in the entrypoint.
# It correctly exec-replaces the process (no parent shell left behind),
# unlike `su` or `sudo`. Needed because Docker volumes are mounted as root
# at runtime — we fix ownership in the entrypoint then drop to appuser.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app/server

# --- Python dependencies (cached layer — only rebuilds when toml/lock change)
COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen --no-dev

# --- Application source
COPY server/ ./

# --- Built React SPA (served by FastAPI at runtime)
COPY --from=build /app/client/dist /app/client/dist

# --- Entrypoint script (fixes volume ownership then drops to appuser)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# --- Non-root user
# The data directory is created here so it exists in the image as a fallback
# (e.g. when running without a volume in development/CI).
# The entrypoint re-chowns it at runtime after the volume is mounted.
RUN useradd -m appuser \
    && mkdir -p /app/server/data \
    && chown -R appuser:appuser /app/server /app/client/dist
# Note: we do NOT set USER here — the entrypoint starts as root so it can
# fix the volume ownership, then drops to appuser via gosu.

# --- Runtime environment
ENV APP_ENV=production \
    DEBUG=false \
    DATABASE_URL=sqlite:////app/server/data/result_portal.db
# SECRET_KEY is intentionally absent — never put secrets in a Dockerfile.
# Override at runtime:  docker run -e SECRET_KEY=your-secret result-portal

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

ENTRYPOINT ["/entrypoint.sh"]
