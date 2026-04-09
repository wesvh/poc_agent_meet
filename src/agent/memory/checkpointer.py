"""LangGraph checkpointer — persists graph state between turns.

Uses AsyncPostgresSaver from langgraph-checkpoint-postgres to store
the full conversation state in PostgreSQL. This enables:
- Session reconnection after disconnects
- Full state recovery for debugging
- Persistence across server restarts
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from urllib.parse import quote_plus

from src.config import Config

log = logging.getLogger(__name__)


def get_checkpointer_conn_string() -> str:
    """Build the PostgreSQL connection string for the checkpointer."""
    return (
        f"postgresql://{Config.DB_USER}:{quote_plus(Config.DB_PASSWORD)}"
        f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    )


@asynccontextmanager
async def get_checkpointer():
    """Async context manager that yields an AsyncPostgresSaver.

    Usage:
        async with get_checkpointer() as checkpointer:
            graph = builder.compile(checkpointer=checkpointer)
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    conn_string = get_checkpointer_conn_string()
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        log.info("[checkpointer] PostgreSQL checkpointer ready")
        yield checkpointer
