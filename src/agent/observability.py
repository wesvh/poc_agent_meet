"""Langfuse observability integration.

Strategy: All turns share the same session_id in trace_context.
Langfuse groups traces by session_id automatically, giving a complete
view of the conversation in the Sessions tab.

Langfuse v4 reads credentials from env vars:
- LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
"""
from __future__ import annotations

import logging

from src.config import Config

log = logging.getLogger(__name__)

_langfuse_client = None
_langfuse_initialized = False

if Config.LANGFUSE_PUBLIC_KEY and Config.LANGFUSE_SECRET_KEY:
    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=Config.LANGFUSE_PUBLIC_KEY,
            secret_key=Config.LANGFUSE_SECRET_KEY,
            host=Config.LANGFUSE_HOST,
        )
        _langfuse_initialized = _langfuse_client.auth_check()
        if _langfuse_initialized:
            log.info("[observability] Langfuse initialized OK")
    except Exception:
        log.exception("[observability] Failed to initialize Langfuse")


def get_turn_handler(session_id: str, store_id: str, turn: int):
    """Create a Langfuse callback handler for one conversation turn.

    All turns with the same session_id are grouped together in
    Langfuse's Sessions view, giving a complete conversation trace.
    """
    if not _langfuse_initialized:
        return None

    from langfuse.langchain import CallbackHandler as LangfuseHandler

    return LangfuseHandler(
        public_key=Config.LANGFUSE_PUBLIC_KEY,
        trace_context={
            "session_id": session_id,
            "metadata": {"store_id": store_id, "turn": turn},
        },
    )


def flush():
    """Flush pending Langfuse events. Call at session end."""
    if _langfuse_client:
        _langfuse_client.flush()
