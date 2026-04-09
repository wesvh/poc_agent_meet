"""Kokoro-ONNX TTS backend — local inference, high-quality Spanish.

Uses kokoro-onnx (no PyTorch required, runs on CPU via ONNX runtime).
Voice ef_dora (female) with lang='es' + espeak-ng for Spanish phonemization.

Model files (~310 MB onnx + ~26 MB voices.bin) must be downloaded at image build time.
SHA256 prefix for ef_dora: d9d69b0f
"""
from __future__ import annotations

import asyncio
import io
import logging
import wave

log = logging.getLogger(__name__)


class KokoroTTS:
    """TTS synthesizer using kokoro-onnx (local ONNX inference)."""

    def __init__(
        self,
        model_path: str,
        voices_path: str,
        voice: str = "ef_dora",
        lang: str = "es",
        speed: float = 1.0,
    ):
        self.model_path = model_path
        self.voices_path = voices_path
        self.voice = voice
        self.lang = lang
        self.speed = speed
        self._kokoro = None

    def _load(self):
        if self._kokoro is not None:
            return
        try:
            from kokoro_onnx import Kokoro
        except ImportError:
            raise RuntimeError(
                "kokoro-onnx not installed. Add 'kokoro-onnx>=0.5.0' to requirements-agent.txt"
            )
        log.info("[tts:kokoro] Loading model: %s | voice: %s | lang: %s", self.model_path, self.voice, self.lang)
        self._kokoro = Kokoro(self.model_path, self.voices_path)

    def _warmup_sync(self) -> None:
        """Load model and run one short synthesis to JIT the ONNX kernels."""
        self._load()
        try:
            self._kokoro.create("Hola.", voice=self.voice, speed=self.speed, lang=self.lang)
            log.info("[tts:kokoro] Warmup complete — model and ONNX kernels ready")
        except Exception:
            log.warning("[tts:kokoro] Warmup synthesis failed (model is loaded, JIT skipped)")

    async def warmup(self) -> None:
        """Pre-load model in a thread so the first real synthesis has no cold-start lag."""
        if self._kokoro is not None:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._warmup_sync)

    @staticmethod
    def _samples_to_wav(samples, sample_rate: int) -> bytes:
        import numpy as np
        pcm = (samples * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())
        return buf.getvalue()

    def _synthesize_sync(self, text: str) -> bytes:
        self._load()
        samples, sample_rate = self._kokoro.create(
            text, voice=self.voice, speed=self.speed, lang=self.lang,
        )
        audio = self._samples_to_wav(samples, sample_rate)
        log.info("[tts:kokoro] Synthesized '%s...' → %d bytes", text[:40], len(audio))
        return audio

    async def synthesize(self, text: str) -> bytes:
        """Synthesize full text to WAV bytes (blocking, runs in thread executor)."""
        if not text.strip():
            return b""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._synthesize_sync, text)

    async def synthesize_stream(self, text: str):
        """Async generator: yield (wav_bytes, sample_rate) chunks as they are synthesized.

        Sends first audio chunk faster than synthesize() — ideal for low-latency streaming.
        Each yielded chunk is a self-contained WAV buffer ready to send over WebSocket.
        """
        if not text.strip():
            return
        self._load()
        async for samples, sample_rate in self._kokoro.create_stream(
            text, voice=self.voice, speed=self.speed, lang=self.lang,
        ):
            if len(samples) == 0:
                continue
            chunk = self._samples_to_wav(samples, sample_rate)
            log.debug("[tts:kokoro] Stream chunk '%s...' → %d bytes", text[:30], len(chunk))
            yield chunk, sample_rate
