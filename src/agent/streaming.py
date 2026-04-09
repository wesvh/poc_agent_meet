"""Token streaming support via asyncio.Queue.

The LLM node streams tokens into a queue. The WebSocket server
consumes from this queue and sends tokens to the client in real-time.

This decouples LLM generation from WebSocket delivery, allowing
the TTS pipeline to start processing tokens immediately.
"""
from __future__ import annotations

import asyncio
import contextvars
from typing import AsyncIterator

# Context variable holding the active token queue for the current session.
# Set by the server before invoking the graph; read by the node.
_token_queue_var: contextvars.ContextVar[asyncio.Queue | None] = contextvars.ContextVar(
    "_token_queue_var", default=None
)

# Sentinel to signal end-of-stream
END_OF_STREAM = object()

# Sentinel to signal WebSocket disconnection (shared across text and voice sessions)
DISCONNECT = object()


def set_token_queue(q: asyncio.Queue) -> None:
    """Set the token queue for the current async context."""
    _token_queue_var.set(q)


def get_token_queue() -> asyncio.Queue | None:
    """Get the token queue for the current async context."""
    return _token_queue_var.get()
