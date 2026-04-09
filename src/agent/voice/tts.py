"""Text-to-Speech — pluggable backend with factory.

All code should call get_tts() instead of instantiating a backend directly.
Switch backends by changing TTS_BACKEND env var — no other code changes needed.

Backends:
  openai  — LiteLLM → OpenAI TTS-1 (~300ms, high quality)
  kokoro  — Kokoro-82M ONNX, local, high quality Spanish (ef_dora + espeak-ng)
"""
from __future__ import annotations

import logging
from typing import Protocol

import litellm

from src.config import Config

log = logging.getLogger(__name__)

_tts_instance: "TTSProvider | None" = None


# ─── Protocol ────────────────────────────────────────────────────────────────

class TTSProvider(Protocol):
    """All TTS backends must implement this single method."""

    async def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes (MP3 or WAV). Returns b'' on failure."""
        ...


# ─── Factory ─────────────────────────────────────────────────────────────────

def get_tts() -> TTSProvider:
    """Return the configured TTS backend (singleton per process).

    Backend is selected by TTS_BACKEND env var.
    """
    global _tts_instance
    if _tts_instance is not None:
        return _tts_instance

    backend = Config.TTS_BACKEND.lower()

    if backend == "kokoro":
        from src.agent.voice.tts_kokoro import KokoroTTS
        _tts_instance = KokoroTTS(
            model_path=Config.KOKORO_MODEL_PATH,
            voices_path=Config.KOKORO_VOICES_PATH,
            voice=Config.KOKORO_VOICE,
            lang=Config.KOKORO_LANG,
        )
        log.info("[tts] Backend: kokoro (voice=%s lang=%s)", Config.KOKORO_VOICE, Config.KOKORO_LANG)

    else:
        _tts_instance = LiteLLMTTS()
        log.info("[tts] Backend: openai (%s)", Config.TTS_MODEL)

    return _tts_instance


# ─── OpenAI / LiteLLM backend ────────────────────────────────────────────────

class LiteLLMTTS:
    """TTS via LiteLLM → OpenAI TTS-1, ElevenLabs, AWS Polly, etc."""

    async def synthesize(self, text: str) -> bytes:
        if not text.strip():
            return b""
        try:
            response = await litellm.aspeech(
                model=Config.TTS_MODEL,
                voice=Config.TTS_VOICE,
                input=text,
            )
            audio = response.content if hasattr(response, "content") else response.read()
            log.info("[tts:openai] '%s...' → %d bytes", text[:40], len(audio))
            return audio
        except Exception:
            log.exception("[tts:openai] Synthesis failed: '%s...'", text[:40])
            return b""


