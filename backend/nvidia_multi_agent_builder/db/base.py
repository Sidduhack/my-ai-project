"""Database base configuration and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from nvidia_multi_agent_builder.config.settings import settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Global engine and session maker (initialized lazily)
engine = None
async_session_maker = None


def init_engine(database_url: str | None = None, **kwargs) -> None:
    """Initialize or reinitialize the database engine."""
    global engine, async_session_maker
    url = database_url or settings.database_url
    
    pool_class = kwargs.get("poolclass")
    engine_kwargs = {
        "url": url,
        "echo": kwargs.get("echo", settings.database_echo),
        "pool_pre_ping": True,
    }
    
    # Only add pool_size/max_overflow for non-StaticPool
    if pool_class is not None and pool_class.__name__ != "StaticPool":
        engine_kwargs["pool_size"] = kwargs.get("pool_size", settings.database_pool_size)
        engine_kwargs["max_overflow"] = kwargs.get("max_overflow", settings.database_max_overflow)
        if pool_class:
            engine_kwargs["poolclass"] = pool_class
    
    # Add remaining kwargs
    excluded = {"echo", "pool_size", "max_overflow", "poolclass", "connect_args"}
    if "connect_args" in kwargs:
        engine_kwargs["connect_args"] = kwargs["connect_args"]
    engine_kwargs.update({k: v for k, v in kwargs.items() if k not in excluded})
    
    engine = create_async_engine(**engine_kwargs)
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


# Initialize with default settings
init_engine()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of FastAPI."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()