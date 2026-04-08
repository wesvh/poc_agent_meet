"""SQLAlchemy async engine and session factory.

This is the only place in the codebase that knows about the database URL and
connection pool configuration. Everything else receives a session via session_scope().
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import Config

DATABASE_URL = (
    f"postgresql+asyncpg://{quote_plus(Config.DB_USER)}:{quote_plus(Config.DB_PASSWORD)}"
    f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
)

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    future=True,
    json_serializer=json.dumps,
    json_deserializer=json.loads,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
