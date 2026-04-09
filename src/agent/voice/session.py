"""Voice session handlers — drop-in replacements for text _listener and _token_sender.

voice_listener:  receives binary audio frames → STT → text into inbox queue
tts_token_sender: consumes token queue → sentence buffer → TTS → audio bytes to WebSocket

Performance: TTS synthesis runs concurrently with token accumulation.
While one sentence is being synthesized, the next is already buffering.
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from src.agent.streaming import DISCONNECT, END_OF_STREAM
from src.agent.voice.stt import LiteLLMSTT, STTProvider
from src.agent.voice.tts import TTSProvider, get_tts
from src.agent.voice.tts_buffer import SentenceBuffer

log = logging.getLogger(__name__)

_THINKING_DESCRIPTIONS = {
    "get_store_context": "Consultando informacion de su tienda...",
    "get_meeting_info": "Verificando informacion de la reunion...",
    "update_onboarding_status": "Actualizando estado...",
    "update_store_info": "Actualizando informacion...",
    "update_meeting_status": "Actualizando reunion...",
    "schedule_followup": "Programando seguimiento...",
}


async def _safe_send_json(ws: WebSocket, data: dict) -> bool:
    """Send JSON, return False if connection is closed."""
    try:
        await ws.send_json(data)
        return True
    except (RuntimeError, WebSocketDisconnect):
        return False


async def _safe_send_bytes(ws: WebSocket, data: bytes) -> bool:
    """Send binary, return False if connection is closed."""
    try:
        await ws.send_bytes(data)
        return True
    except (RuntimeError, WebSocketDisconnect):
        return False


async def voice_listener(
    websocket: WebSocket,
    inbox: asyncio.Queue,
    *,
    stt: STTProvider | None = None,
):
    """Receive audio or text from WebSocket, transcribe if needed, push to inbox."""
    if stt is None:
        stt = LiteLLMSTT()

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
                log.info("[voice] Received %d bytes audio", len(audio_bytes))
                text = await stt.transcribe(audio_bytes)
                if text:
                    log.info("[voice] STT: '%s'", text[:80])
                    await inbox.put(text)

            elif "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                    content = data.get("content") or data.get("type") == "text_input" and data.get("content")
                    if content:
                        await inbox.put(content)
                except json.JSONDecodeError:
                    await inbox.put(message["text"])

    except (WebSocketDisconnect, RuntimeError):
        await inbox.put(DISCONNECT)
    except Exception:
        log.exception("[voice] Listener error")
        await inbox.put(DISCONNECT)


async def tts_token_sender(
    token_queue: asyncio.Queue,
    websocket: WebSocket,
    session_id: str,
    *,
    tts: TTSProvider | None = None,
):
    """Consume tokens, buffer into sentences, synthesize TTS concurrently, send audio.

    Performance strategy:
    - Tokens are buffered until sentence boundary
    - TTS synthesis is launched as a background task
    - While one sentence synthesizes, the next sentence buffers
    - Audio is sent as soon as synthesis completes
    """
    if tts is None:
        tts = get_tts()

    buffer = SentenceBuffer()
    pending_tts: list[asyncio.Task] = []  # Background TTS tasks
    connected = True

    async def _synthesize_and_send(text: str):
        """Synthesize text and send audio bytes. Runs as background task."""
        nonlocal connected
        if not connected:
            return
        audio = await tts.synthesize(text)
        if audio and connected:
            connected = await _safe_send_bytes(websocket, audio)

    while True:
        item = await token_queue.get()

        if item is END_OF_STREAM:
            # Flush remaining buffer
            remaining = buffer.flush()
            if remaining and connected:
                pending_tts.append(asyncio.create_task(_synthesize_and_send(remaining)))
            # Wait for all pending TTS to finish
            if pending_tts:
                await asyncio.gather(*pending_tts, return_exceptions=True)
            if connected:
                await _safe_send_json(websocket, {"type": "audio_end", "session_id": session_id})
            break

        msg_type, payload = item

        if not connected:
            continue  # Drain queue but don't send

        if msg_type == "token":
            # Send text token for subtitles
            connected = await _safe_send_json(websocket, {
                "type": "token", "content": payload, "session_id": session_id,
            })

            # Buffer and launch TTS on sentence boundary
            sentence = buffer.add_token(payload)
            if sentence:
                # Wait for previous TTS to finish before starting new one
                # (ensures audio arrives in order)
                if pending_tts:
                    await asyncio.gather(*pending_tts, return_exceptions=True)
                    pending_tts.clear()
                pending_tts.append(asyncio.create_task(_synthesize_and_send(sentence)))

        elif msg_type == "message_end":
            remaining = buffer.flush()
            if remaining:
                if pending_tts:
                    await asyncio.gather(*pending_tts, return_exceptions=True)
                    pending_tts.clear()
                pending_tts.append(asyncio.create_task(_synthesize_and_send(remaining)))

            # Wait for all audio to be sent before signaling message_end
            if pending_tts:
                await asyncio.gather(*pending_tts, return_exceptions=True)
                pending_tts.clear()

            await _safe_send_json(websocket, {"type": "message_end", "session_id": session_id})

        elif msg_type == "thinking":
            detail = _THINKING_DESCRIPTIONS.get(payload, "Procesando...")
            await _safe_send_json(websocket, {
                "type": "thinking", "detail": detail, "session_id": session_id,
            })
            # Don't synthesize thinking messages — wastes latency
