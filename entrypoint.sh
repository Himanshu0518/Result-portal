#!/bin/sh
# Entrypoint script for the Result Portal container.
#
# The /app/server/data directory is a Docker volume mounted at runtime.
# Docker mounts volumes owned by root, so we fix ownership here before
# dropping to appuser — this cannot be done at image build time.

set -e

# Fix ownership of the mounted volume so appuser can write the SQLite DB.
chown -R appuser:appuser /app/server/data

# Drop privileges and run the application as appuser.
# gosu is a minimal su replacement that correctly replaces the process
# (unlike su or sudo which leave a parent shell process).
exec gosu appuser sh -c "
  uv run alembic upgrade head &&
  uv run uvicorn main:app --host 0.0.0.0 --port 8000
"
