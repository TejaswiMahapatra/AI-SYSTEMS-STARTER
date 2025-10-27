"""
Database connection and session management for PostgreSQL.

Copyright 2025 Tejaswi Mahapatra
Licensed under the Apache License, Version 2.0
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from backend.config import settings


# Base class for all SQLAlchemy models
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Async engine for database operations
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug, 
    future=True,
    pool_pre_ping=True,  # Verify connections before using
    poolclass=NullPool if settings.environment == "development" else None,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get a database session.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db_session():
    """
    Context manager for getting a database session in background workers.

    Usage:
        async with get_db_session() as db:
            result = await db.execute(select(Document))
            documents = result.scalars().all()
    """
    return AsyncSessionLocal()


async def init_db() -> None:
    """
    Initialize database tables.
    This creates all tables defined in models.

    NOTE: In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections gracefully."""
    await engine.dispose()


async def check_db_health() -> bool:
    """
    Check if database connection is healthy.
    Returns True if connection is successful, False otherwise.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return True
    except Exception:
        return False
