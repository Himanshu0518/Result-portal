from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config.env import settings


# SQLite-specific: enable WAL mode and foreign keys on every connection
def _set_sqlite_pragmas(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Engine
# - check_same_thread=False is required for SQLite when FastAPI uses
#   multiple threads (default behaviour with async routes).
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=settings.DEBUG,  # logs SQL in development; silent in production
)

if settings.DATABASE_URL.startswith("sqlite"):
    event.listen(engine, "connect", _set_sqlite_pragmas)


# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# Declarative base shared by all models
class Base(DeclarativeBase):
    pass


# FastAPI dependency — yields a DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
