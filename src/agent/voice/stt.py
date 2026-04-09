"""Speech-to-Text via LiteLLM.

Converts audio bytes to text using litellm.atranscription().
Supports any provider that LiteLLM supports (OpenAI Whisper, Deepgram, Groq, etc.)
— change the model via STT_MODEL env var.
"""
from __future__ import annotations

import io
import logging
from typing import Protocol

import litellm

from src.config import Config

log = logging.getLogger(__name__)


class STTProvider(Protocol):
    """Abstract interface for speech-to-text."""

    async def transcribe(self, audio_bytes: bytes, format: str = "webm") -> str:
        """Convert audio bytes to text. Returns empty string on failure."""
        ...


class LiteLLMSTT:
    """STT implementation using LiteLLM (delegates to OpenAI Whisper, Deepgram, etc.)."""

    async def transcribe(self, audio_bytes: bytes, format: str = "webm") -> str:
        if not audio_bytes:
            return ""

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio.{format}"

        try:
            response = await litellm.atranscription(
                model=Config.STT_MODEL,
                file=audio_file,
                language=Config.STT_LANGUAGE,
            )
            text = response.text.strip() if hasattr(response, "text") else ""
            log.info("[stt] Transcribed %d bytes → '%s' (%d chars)", len(audio_bytes), text[:50], len(text))
            return text
        except Exception:
            log.exception("[stt] Transcription failed for %d bytes", len(audio_bytes))
            return ""
