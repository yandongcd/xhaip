"""Database abstraction layer — SQLAlchemy async engine + session.

Supports:
    - PostgreSQL via asyncpg (production)
    - SQLite via aiosqlite (development/CI fallback)
    - Connection pooling with configurable pool size
    - Alembic migration support
    - FastAPI dependency injection

Environment:
    DATABASE_URL: Full connection string (e.g. postgresql+asyncpg://...)
    If not set, falls back to local SQLite in the project root.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

# Default connection string with SQLite fallback
_DEFAULT_SQLITE = os.environ.get(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{Path(__file__).resolve().parent.parent.parent.parent / 'xhaip.db'}",
)

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url() -> str:
    """Get the database URL from environment or config."""
    return os.environ.get("DATABASE_URL", _DEFAULT_SQLITE)


def _create_engine(url: str) -> AsyncEngine:
    """Create SQLAlchemy async engine with appropriate pool settings."""
    is_postgres = url.startswith("postgresql")
    pool_class = QueuePool if is_postgres else NullPool
    pool_size = int(os.environ.get("DB_POOL_SIZE", "10"))

    kwargs = {
        "echo": os.environ.get("DB_ECHO", "").lower() == "true",
    }
    if is_postgres:
        kwargs["poolclass"] = pool_class
        kwargs["pool_size"] = pool_size
        kwargs["max_overflow"] = int(os.environ.get("DB_MAX_OVERFLOW", "5"))
    else:
        kwargs["poolclass"] = NullPool  # SQLite doesn't work well with pool

    return create_async_engine(url, **kwargs)


def init_database(url: Optional[str] = None):
    """Initialize the database engine and session factory.

    Called once at application startup.
    """
    global _engine, _sessionmaker
    db_url = url or get_database_url()
    _engine = _create_engine(db_url)
    _sessionmaker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def close_database():
    """Close the database engine. Called at application shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a database session."""
    if _sessionmaker is None:
        init_database()
    session: AsyncSession = _sessionmaker()  # type: ignore[union-attr]
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def session_scope():
    """Context manager for database sessions (non-FastAPI usage)."""
    if _sessionmaker is None:
        init_database()
    session: AsyncSession = _sessionmaker()  # type: ignore[union-attr]
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def create_tables():
    """Create all tables if they don't exist (development convenience)."""
    from sqlalchemy import text

    async with session_scope() as session:
        # Users table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                display_name TEXT,
                department TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT DEFAULT ''
            )
        """))
        # Roles table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL REFERENCES users(id),
                role_name TEXT NOT NULL,
                UNIQUE(user_id, role_name)
            )
        """))
        # Audit events table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                action TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                resource TEXT,
                status TEXT,
                detail TEXT,
                ip_address TEXT,
                session_id TEXT
            )
        """))
        # Create index
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id)
        """))
        await session.commit()
