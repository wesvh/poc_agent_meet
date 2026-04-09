"""Recall.ai bot session bridge.

Each active bot maps to a RecallBotSession that wires:
  audio_separate_raw.data (WS) → participant filter → VAD → Whisper STT → agent_inbox
  token_queue → TTS → output-media page WS → meeting

Audio arrives per-participant with identity labels. The bot's own audio is dropped
immediately before VAD — only human participant audio is transcribed via Whisper.
No timing hacks, no echo prevention needed.

Secondary safety net: Jaccard word-overlap on STT output catches the rare case where
the bot participant name is missing or mismatched in the Recall.ai event.
"""
from __future__ import annotations

import asyncio
import io
import logging
import math
import struct
import time
import wave
from collections import deque
from typing import Awaitable, Callable, Dict

from fastapi import WebSocket, WebSocketDisconnect


log = logging.getLogger(__name__)

_OUTPUT_WS_WAIT_TIMEOUT = 30.0   # seconds to wait for output page on first TTS
_ECHO_WINDOW_S          = 20.0   # seconds to keep bot sentences for similarity check
_ECHO_THRESHOLD         = 0.70   # Jaccard similarity above which we treat text as echo

# ── VAD constants ─────────────────────────────────────────────────────────────
_SAMPLE_RATE      = 16000   # Hz — Recall.ai default for separate audio
_BYTES_PER_SAMPLE = 2       # 16-bit signed little-endian PCM

_RMS_SPEECH       = 300     # minimum RMS to consider a frame as speech (raised to filter background noise)
_SPEECH_MIN_S     = 0.25    # seconds of speech before entering speech state (raised to avoid noise spikes)
_SILENCE_END_S    = 0.90    # seconds of silence to end utterance (raised to handle natural speech pauses)
_MIN_SPEECH_DUR_S = 0.40    # minimum active speech duration to emit; shorter = discard as noise
_MAX_UTTERANCE_S  = 15.0    # force-flush after this many seconds


def _compute_rms(pcm: bytes) -> float:
    """Compute RMS energy of 16-bit little-endian mono PCM."""
    n = len(pcm) // _BYTES_PER_SAMPLE
    if n == 0:
        return 0.0
    samples = struct.unpack_from(f"<{n}h", pcm)
    return math.sqrt(sum(s * s for s in samples) / n)


def _pcm_to_wav(pcm: bytes) -> bytes:
    """Wrap raw PCM bytes in a WAV container (needed by Whisper/LiteLLM)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(_BYTES_PER_SAMPLE)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm)
    return buf.getvalue()


def _pcm_duration_s(pcm: bytes) -> float:
    return len(pcm) / (_SAMPLE_RATE * _BYTES_PER_SAMPLE)


UtteranceCallback = Callable[[bytes], Awaitable[None]]


class ParticipantAudioBuffer:
    """VAD + accumulation buffer for one meeting participant.

    Receives raw PCM frames from audio_separate_raw.data events.
    Invokes on_utterance(wav_bytes) when a complete utterance is detected.
    """

    def __init__(self, participant_id: int | str, name: str, on_utterance: UtteranceCallback):
        self.participant_id = participant_id
        self.name           = name
        self._on_utterance  = on_utterance

        self._buf: list[bytes] = []
        self._in_speech       = False
        self._speech_start_ts: float = 0.0  # when speech state began
        self._last_speech_ts:  float = 0.0  # last frame with speech energy
        self._first_speech_ts: float = 0.0  # first frame with energy (pre-gate accumulator)
        self._pre_speech_dur:  float = 0.0  # accumulated speech seconds before gate opens

    async def push(self, pcm_frame: bytes) -> None:
        now       = time.monotonic()
        is_speech = _compute_rms(pcm_frame) >= _RMS_SPEECH

        if is_speech:
            self._last_speech_ts = now
            self._buf.append(pcm_frame)

            if not self._in_speech:
                if self._first_speech_ts == 0.0:
                    self._first_speech_ts = now
                self._pre_speech_dur += _pcm_duration_s(pcm_frame)
                if self._pre_speech_dur >= _SPEECH_MIN_S:
                    self._in_speech       = True
                    self._speech_start_ts = self._first_speech_ts
                    log.info("[vad] speech_start stream=%s", str(self.participant_id)[:8])
        else:
            if self._in_speech:
                self._buf.append(pcm_frame)
                if now - self._last_speech_ts >= _SILENCE_END_S:
                    await self._emit()
            else:
                # Reset pre-speech accumulator if silence before gate opens
                if self._first_speech_ts and now - self._last_speech_ts >= _SILENCE_END_S:
                    self._first_speech_ts = 0.0
                    self._pre_speech_dur  = 0.0
                    self._buf.clear()

        if self._in_speech and _pcm_duration_s(b"".join(self._buf)) >= _MAX_UTTERANCE_S:
            await self._emit()

    async def _emit(self) -> None:
        if self._buf:
            pcm = b"".join(self._buf)
            self._buf.clear()
            now         = time.monotonic()
            speech_dur  = self._last_speech_ts - self._speech_start_ts
            silence_dur = now - self._last_speech_ts
            audio_dur   = _pcm_duration_s(pcm)
            if speech_dur < _MIN_SPEECH_DUR_S:
                log.info(
                    "[vad] utterance_discard stream=%s | speech=%.2fs < min=%.2fs (noise)",
                    str(self.participant_id)[:8], speech_dur, _MIN_SPEECH_DUR_S,
                )
            else:
                log.info(
                    "[vad] utterance_emit stream=%s | speech=%.2fs silence_wait=%.2fs audio=%.2fs bytes=%d",
                    str(self.participant_id)[:8], speech_dur, silence_dur, audio_dur, len(pcm),
                )
                await self._on_utterance(_pcm_to_wav(pcm))
        self._in_speech       = False
        self._first_speech_ts = 0.0
        self._pre_speech_dur  = 0.0


class RecallBotSession:
    """Shared state for one active Recall.ai bot session."""

    def __init__(self, bot_id: str, store_id: str, bot_name: str = ""):
        self.bot_id    = bot_id
        self.store_id  = store_id
        self.bot_name  = bot_name   # matched against participant.name to drop bot audio

        self.agent_inbox: asyncio.Queue = asyncio.Queue()
        self._output_ws: WebSocket | None = None
        self._output_ws_ready: asyncio.Event = asyncio.Event()

        # Per-participant VAD buffers (keyed by audio_separate.id from Recall.ai)
        self._participant_buffers: Dict[int | str, ParticipantAudioBuffer] = {}

        # TTS state — used to suppress echo while bot is speaking or just finished
        self.bot_is_speaking: bool = False
        self._last_tts_end_ts: float = 0.0   # monotonic ts when last TTS chunk was sent

        # Secondary echo filter: (monotonic_ts, frozenset_of_words) per bot sentence
        self._recent_bot_sentences: deque[tuple[float, frozenset[str]]] = deque(maxlen=30)

    # ── Per-participant audio buffers ─────────────────────────────────────────

    def get_participant_buffer(
        self,
        participant_id: int | str,
        name: str,
        on_utterance: UtteranceCallback,
    ) -> ParticipantAudioBuffer:
        """Return the VAD buffer for this participant, creating one on first call."""
        if participant_id not in self._participant_buffers:
            self._participant_buffers[participant_id] = ParticipantAudioBuffer(
                participant_id, name, on_utterance
            )
            log.info("[recall:bridge] New participant buffer: id=%s name='%s'", participant_id, name)
        return self._participant_buffers[participant_id]

    # ── Output WebSocket ──────────────────────────────────────────────────────

    def set_output_ws(self, ws: WebSocket) -> None:
        self._output_ws = ws
        self._output_ws_ready.set()

    def clear_output_ws(self) -> None:
        self._output_ws = None
        self._output_ws_ready.clear()

    async def send_tts_audio(self, audio_bytes: bytes) -> bool:
        """Forward a TTS chunk to the output-media page WebSocket.

        Waits up to _OUTPUT_WS_WAIT_TIMEOUT for the page to connect.
        """
        if self._output_ws is None:
            try:
                await asyncio.wait_for(
                    self._output_ws_ready.wait(),
                    timeout=_OUTPUT_WS_WAIT_TIMEOUT,
                )
            except asyncio.TimeoutError:
                log.warning("[recall:bridge] Timed out waiting for output-ws bot=%s", self.bot_id)
                return False

        if self._output_ws is None:
            return False
        try:
            await self._output_ws.send_bytes(audio_bytes)
            return True
        except (RuntimeError, WebSocketDisconnect):
            self.clear_output_ws()
            return False

    # ── Echo filter (secondary safety net) ───────────────────────────────────

    def log_bot_sentence(self, text: str) -> None:
        """Record a sentence the bot is about to say, for secondary echo detection."""
        words = frozenset(text.lower().split())
        if words:
            self._recent_bot_sentences.append((time.monotonic(), words))

    def is_echo(self, text: str) -> bool:
        """Return True if text is likely the bot's own voice echoing back.

        Only needed as a safety net when participant.name is missing or wrong.
        """
        text_words = frozenset(text.lower().split())
        if not text_words:
            return False
        now = time.monotonic()
        for ts, bot_words in self._recent_bot_sentences:
            if now - ts > _ECHO_WINDOW_S:
                continue
            union = text_words | bot_words
            if union and len(text_words & bot_words) / len(union) >= _ECHO_THRESHOLD:
                return True
        return False


# ─── Registry ─────────────────────────────────────────────────────────────────

_sessions: Dict[str, RecallBotSession] = {}


def register_session(bot_id: str, store_id: str, bot_name: str = "") -> RecallBotSession:
    session = RecallBotSession(bot_id, store_id, bot_name=bot_name)
    _sessions[bot_id] = session
    log.info("[recall:bridge] Registered session bot=%s store=%s", bot_id, store_id)
    return session


def get_session(bot_id: str) -> RecallBotSession | None:
    return _sessions.get(bot_id)


def remove_session(bot_id: str) -> None:
    _sessions.pop(bot_id, None)
    log.info("[recall:bridge] Removed session bot=%s", bot_id)
