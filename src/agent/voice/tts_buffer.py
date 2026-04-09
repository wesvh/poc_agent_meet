"""Sentence-boundary buffer for TTS pipeline.

Accumulates LLM tokens until a sentence boundary is detected,
then flushes the sentence for TTS synthesis. This minimizes
time-to-first-audio while producing natural speech segments.

Flow:
  LLM token → add_token() → None (buffering)
  LLM token → add_token() → "Hola, buenas tardes." (sentence ready for TTS)
  message_end → flush() → "remaining text" (force flush)
"""
from __future__ import annotations


class SentenceBuffer:
    """Buffers tokens and flushes on sentence boundaries."""

    BOUNDARIES = frozenset(".!?")
    MIN_CHARS = 15    # Don't synthesize fragments shorter than this
    MAX_CHARS = 180   # Force flush on long clauses (avoid TTS timeouts)

    def __init__(self) -> None:
        self._buffer: str = ""

    def add_token(self, token: str) -> str | None:
        """Add a token. Returns flushed text if a sentence boundary is hit, else None."""
        self._buffer += token

        if self._should_flush():
            text = self._buffer.strip()
            self._buffer = ""
            return text if text else None
        return None

    def flush(self) -> str | None:
        """Force flush whatever is in the buffer (call on message_end)."""
        text = self._buffer.strip()
        self._buffer = ""
        return text if text else None

    def _should_flush(self) -> bool:
        stripped = self._buffer.strip()
        if not stripped:
            return False

        # Force flush if buffer is too long
        if len(stripped) >= self.MAX_CHARS:
            return True

        # Flush on sentence boundary if we have enough text
        if len(stripped) >= self.MIN_CHARS and stripped[-1] in self.BOUNDARIES:
            return True

        return False
