# server

A project created with FastAPI CLI.

## Quick Start

### Start the development server

```bash
uv run fastapi dev
```

Visit http://localhost:8000

### Deploy to FastAPI Cloud

Sign up and log in at https://fastapicloud.com, then deploy with:

```bash
uv run fastapi deploy
```

## Project Structure

- `main.py` - Your FastAPI application
- `pyproject.toml` - Project dependencies

## Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [FastAPI Cloud](https://fastapicloud.com)


# Apply all pending migrations
uv run alembic upgrade head

# After changing a model, generate a new migration
uv run alembic revision --autogenerate -m "add student photo_url"

# Roll back one step
uv run alembic downgrade -1

# See current revision
uv run alembic current

# See full history
uv run alembic history --verbose
