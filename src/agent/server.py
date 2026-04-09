"""Handoff Agent server — FastAPI entry point.

Endpoints:
  /ws/handoff/{store_id}           — text mode (JSON tokens)
  /ws/handoff/{store_id}/voice     — voice mode (binary audio)

  POST /recall/bots                — create a Recall.ai bot for a meeting
  GET  /recall/bots/{bot_id}       — get bot status from Recall.ai
  GET  /recall/output/{bot_id}     — output-media HTML page (Recall.ai loads this)
  WS   /recall/output-ws/{bot_id}  — output-media page connects here to receive TTS audio
  WS   /recall/ws/{bot_id}         — Recall.ai pushes audio_separate_raw.data events here

Text and voice share _session_core() (graph setup, conversation loop, state persistence).
Recall.ai reuses _session_core() via a NullWebSocket + custom I/O adapters.
Audio arrives per-participant — bot audio is dropped by identity before VAD/Whisper STT.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
import uuid
from functools import partial
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from langchain_core.messages import HumanMessage

from src.agent.graph import build_graph
from src.agent.mcp.factory import create_all_tools
from src.agent.memory.checkpointer import get_checkpointer
from src.agent.observability import flush as langfuse_flush, get_turn_handler
from src.agent.recall.bridge import (
    RecallBotSession,
    get_session,
    register_session,
    remove_session,
)
from src.agent.state import HandoffState
from src.agent.streaming import DISCONNECT, END_OF_STREAM, set_token_queue
from src.agent.voice.tts_buffer import SentenceBuffer
from src.config import Config
from src.infrastructure.db.repositories import (
    SqlAlchemyHandoffSessionRepo,
    SqlAlchemyMeetingRepo,
    SqlAlchemyStoreRepo,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [agent] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

app = FastAPI(title="Handoff Agent", version="1.0.0")

_store_repo = SqlAlchemyStoreRepo()
_meeting_repo = SqlAlchemyMeetingRepo()
_session_repo = SqlAlchemyHandoffSessionRepo()


_THINKING_DESCRIPTIONS = {
    "get_store_context": "Consultando informacion de su tienda...",
    "get_meeting_info": "Verificando informacion de la reunion...",
    "update_onboarding_status": "Actualizando estado de onboarding...",
    "update_store_info": "Actualizando informacion de la tienda...",
    "update_meeting_status": "Actualizando estado de la reunion...",
    "schedule_followup": "Programando sesion de seguimiento...",
}

# Type aliases for pluggable I/O
ListenerFn = Callable[[WebSocket, asyncio.Queue], Awaitable[None]]
SenderFn = Callable[[asyncio.Queue, WebSocket, str], Awaitable[None]]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "handoff-agent"}


# ─── TEXT I/O ADAPTERS ────────────────────────────────────────────────────

async def _listener(websocket: WebSocket, inbox: asyncio.Queue):
    """Text mode: receive JSON messages, extract text, push to inbox."""
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                user_text = data.get("content", data.get("message", raw))
            except json.JSONDecodeError:
                user_text = raw
            await inbox.put(user_text)
    except WebSocketDisconnect:
        await inbox.put(DISCONNECT)
    except Exception:
        await inbox.put(DISCONNECT)


async def _token_sender(token_queue: asyncio.Queue, ws: WebSocket, sid: str):
    """Text mode: forward tokens as JSON to WebSocket."""
    while True:
        item = await token_queue.get()
        if item is END_OF_STREAM:
            break
        msg_type, payload = item
        if msg_type == "token":
            await ws.send_json({"type": "token", "content": payload, "session_id": sid})
        elif msg_type == "message_end":
            await ws.send_json({"type": "message_end", "session_id": sid})
        elif msg_type == "thinking":
            detail = _THINKING_DESCRIPTIONS.get(payload, "Procesando...")
            await ws.send_json({"type": "thinking", "detail": detail, "session_id": sid})


# ─── SHARED SESSION CORE ─────────────────────────────────────────────────

class _NullWebSocket:
    """Stand-in WebSocket for server-side sessions (Recall.ai) that have no direct client."""

    async def accept(self) -> None:
        pass

    async def send_json(self, data: Any) -> None:
        pass

    async def send_bytes(self, data: bytes) -> None:
        pass


async def _run_turn(compiled_graph, input_data, config, sender_fn: SenderFn, ws, sid) -> str | None:
    """Execute one graph turn with pluggable sender."""
    token_queue: asyncio.Queue = asyncio.Queue()
    set_token_queue(token_queue)

    sender_task = asyncio.create_task(sender_fn(token_queue, ws, sid))

    try:
        result = await compiled_graph.ainvoke(input_data, config=config)
    finally:
        await token_queue.put(END_OF_STREAM)
        await sender_task

    session_status = result.get("session_status")
    if session_status in ("completed", "abandoned"):
        messages = result.get("messages", [])
        try:
            for msg in reversed(messages):
                if hasattr(msg, "type") and msg.type == "ai" and hasattr(msg, "content") and msg.content:
                    await ws.send_json({"type": "message", "content": msg.content, "session_id": sid})
                    break
            await ws.send_json({"type": "session_end", "status": session_status, "session_id": sid})
        except (RuntimeError, WebSocketDisconnect):
            log.debug("[ws] Client already disconnected, skipping session_end")

    return session_status if session_status in ("completed", "abandoned") else None


async def _session_core(
    websocket: WebSocket,
    store_id: str,
    listener_fn: ListenerFn,
    sender_fn: SenderFn,
):
    """Shared session logic for text, voice, and Recall.ai endpoints.

    Handles: graph setup, checkpointer, DB records, conversation loop, state persistence.
    The only variable parts are listener_fn (how input arrives) and sender_fn (how output is delivered).
    Works with real WebSockets and with _NullWebSocket for server-side sessions.
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    log.info("[ws] Connection accepted: store=%s session=%s", store_id, session_id)

    tools = create_all_tools(_store_repo, _meeting_repo, _session_repo, store_id=store_id)
    graph_builder = build_graph(tools)

    turn_counter = 0
    config = {}

    async with get_checkpointer() as checkpointer:
        compiled_graph = graph_builder.compile(checkpointer=checkpointer)

        meeting_info = await _meeting_repo.get_pending_by_store_id(store_id)
        meeting_id = meeting_info["id"] if meeting_info else None
        await _session_repo.create(session_id, store_id, meeting_id)

        store_context = await _store_repo.get_by_id(store_id) or {}
        if meeting_info:
            store_context["meeting"] = meeting_info

        initial_state: HandoffState = {
            "session_id": session_id,
            "store_id": store_id,
            "meeting_id": meeting_id,
            "messages": [],
            "store_context": store_context,
            "meeting_context": meeting_info or {},
            "blocks_completed": {},
            "current_block": None,
            "active_skill_prompt": None,
            "collected_data": {},
            "issues_detected": [],
            "commitments": [],
            "session_status": "active",
            "turn_count": 0,
        }

        def _make_config():
            """Build config with per-turn Langfuse handler under the session trace."""
            nonlocal turn_counter, config
            handler = get_turn_handler(session_id, store_id, turn_counter)
            turn_counter += 1
            callbacks = [handler] if handler else []
            config = {
                "configurable": {"thread_id": session_id},
                "callbacks": callbacks,
            }
            return config

        inbox: asyncio.Queue = asyncio.Queue()
        listener_task = asyncio.create_task(listener_fn(websocket, inbox))

        try:
            cfg = _make_config()
            ended = await _run_turn(compiled_graph, initial_state, cfg, sender_fn, websocket, session_id)
            if ended:
                return

            while True:
                user_text = await inbox.get()
                if user_text is DISCONNECT:
                    log.info("[ws] Client disconnected: store=%s", store_id)
                    break

                log.info("[ws] User message: store=%s len=%d", store_id, len(user_text))

                extra = []
                while not inbox.empty():
                    msg = inbox.get_nowait()
                    if msg is DISCONNECT:
                        break
                    extra.append(msg)
                if extra:
                    user_text = user_text + "\n" + "\n".join(extra)

                cfg = _make_config()
                ended = await _run_turn(
                    compiled_graph,
                    {"messages": [HumanMessage(content=user_text)]},
                    cfg,
                    sender_fn,
                    websocket,
                    session_id,
                )
                if ended:
                    break

        except WebSocketDisconnect:
            log.info("[ws] Client disconnected: store=%s session=%s", store_id, session_id)
        except Exception:
            log.exception("[ws] Error in session: store=%s session=%s", store_id, session_id)
        finally:
            listener_task.cancel()
            try:
                final_state = await compiled_graph.aget_state(config)
                sv = final_state.values if final_state else {}
                await _session_repo.update_session_data(
                    session_id,
                    blocks_completed=sv.get("blocks_completed"),
                    issues_detected=sv.get("issues_detected"),
                    commitments=sv.get("commitments"),
                    turn_count=sv.get("turn_count"),
                )
                transcript = [
                    {"type": m.type, "content": m.content}
                    for m in sv.get("messages", [])
                    if hasattr(m, "content") and hasattr(m, "type")
                ]
                if transcript:
                    await _session_repo.save_transcript(session_id, transcript)
                if sv.get("session_status") != "completed":
                    await _session_repo.update_status(session_id, "abandoned")
                log.info("[ws] Session persisted: session=%s", session_id)
            except Exception:
                log.exception("[ws] Failed to persist session: session=%s", session_id)
            finally:
                langfuse_flush()


# ─── TEXT / VOICE ENDPOINTS ──────────────────────────────────────────────

@app.websocket("/ws/handoff/{store_id}")
async def handoff_session(websocket: WebSocket, store_id: str):
    """Text-mode WebSocket endpoint."""
    await _session_core(websocket, store_id, _listener, _token_sender)


@app.websocket("/ws/handoff/{store_id}/voice")
async def handoff_voice_session(websocket: WebSocket, store_id: str):
    """Voice-mode WebSocket endpoint. Audio in, audio out."""
    from src.agent.voice.session import tts_token_sender, voice_listener
    from src.agent.voice.stt import LiteLLMSTT
    from src.agent.voice.tts import get_tts

    await _session_core(
        websocket,
        store_id,
        listener_fn=partial(voice_listener, stt=LiteLLMSTT()),
        sender_fn=partial(tts_token_sender, tts=get_tts()),
    )


# ─── RECALL.AI — OUTPUT MEDIA PAGE ───────────────────────────────────────

_CAMERA_IMAGE_URL = "https://w7.pngwing.com/pngs/643/709/png-transparent-line-moustache-design-funny-moustache-joke.png"

_OUTPUT_PAGE_HTML = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Handoff Agent</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{
      width: 1280px;
      height: 720px;
      overflow: hidden;
      background: #111;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
    }}
  </style>
</head>
<body>
  <img src="{_CAMERA_IMAGE_URL}" alt="Handoff Agent">
  <script>
  (function() {{
    const parts = location.pathname.split('/').filter(Boolean);
    const botId = parts[parts.length - 1];
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(proto + '//' + location.host + '/recall/output-ws/' + botId);
    ws.binaryType = 'arraybuffer';

    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    let nextStart = 0;

    ws.onmessage = async function(ev) {{
      if (!(ev.data instanceof ArrayBuffer) || ev.data.byteLength === 0) return;
      try {{
        const buf = await ctx.decodeAudioData(ev.data.slice(0));
        const src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(ctx.destination);
        const now = ctx.currentTime;
        const start = Math.max(now + 0.05, nextStart);
        src.start(start);
        nextStart = start + buf.duration;
      }} catch(e) {{ console.error('[output] decode error', e); }}
    }};

    ws.onopen  = function() {{ console.log('[output] WS connected bot=' + botId); }};
    ws.onclose = function() {{ console.log('[output] WS closed'); }};
    ws.onerror = function(e) {{ console.error('[output] WS error', e); }};
  }})();
  </script>
</body>
</html>"""


@app.get("/recall/output/{bot_id}")
async def recall_output_page(bot_id: str):
    """Serve the output-media HTML page. Recall.ai loads this in its headless browser."""
    return HTMLResponse(content=_OUTPUT_PAGE_HTML)


@app.websocket("/recall/output-ws/{bot_id}")
async def recall_output_ws(websocket: WebSocket, bot_id: str):
    """Output-media page connects here to receive TTS audio bytes."""
    await websocket.accept()
    session = get_session(bot_id)
    if not session:
        log.warning("[recall] output-ws: unknown bot_id=%s", bot_id)
        await websocket.close(code=4004)
        return

    session.set_output_ws(websocket)
    log.info("[recall] Output page connected: bot=%s", bot_id)

    try:
        # Keep connection open until the bot leaves the meeting
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        session.clear_output_ws()
        log.info("[recall] Output page disconnected: bot=%s", bot_id)


# ─── RECALL.AI — AUDIO STREAM I/O ADAPTERS ───────────────────────────────

async def _recall_inbox_listener(
    websocket: WebSocket,
    inbox: asyncio.Queue,
    *,
    recall_session: RecallBotSession,
):
    """Listener for Recall.ai sessions — bridges session.agent_inbox → inbox queue."""
    try:
        while True:
            text = await recall_session.agent_inbox.get()
            await inbox.put(text)
            if text is DISCONNECT:
                break
    except Exception:
        await inbox.put(DISCONNECT)


async def _recall_tts_sender(
    token_queue: asyncio.Queue,
    ws,  # _NullWebSocket — not used for output
    session_id: str,
    *,
    tts,
    recall_session: RecallBotSession,
):
    """TTS sender for Recall.ai: token stream → sentences → audio → output-media page.

    Echo prevention is handled upstream: Recall.ai labels transcripts with participant
    info, so the bot's own voice is filtered by name before reaching agent_inbox.
    No timing hacks needed here.
    """
    buffer = SentenceBuffer()
    connected = True

    async def _send(text: str) -> None:
        nonlocal connected
        recall_session.log_bot_sentence(text)
        recall_session.bot_is_speaking = True
        log.info("[recall:tts] '%s...'", text[:60])
        try:
            if hasattr(tts, "synthesize_stream"):
                async for chunk, _ in tts.synthesize_stream(text):
                    if connected and not await recall_session.send_tts_audio(chunk):
                        connected = False
                        break
            else:
                audio = await tts.synthesize(text)
                if audio and not await recall_session.send_tts_audio(audio):
                    connected = False
        except Exception:
            log.exception("[recall:tts] synthesis error: '%s...'", text[:40])
        finally:
            recall_session.bot_is_speaking = False
            recall_session._last_tts_end_ts = time.monotonic()

    while True:
        item = await token_queue.get()

        if item is END_OF_STREAM:
            remaining = buffer.flush()
            if remaining and connected:
                await _send(remaining)
            break

        msg_type, payload = item
        if not connected:
            continue

        if msg_type == "token":
            sentence = buffer.add_token(payload)
            if sentence:
                await _send(sentence)

        elif msg_type == "message_end":
            remaining = buffer.flush()
            if remaining and connected:
                await _send(remaining)


# ─── RECALL.AI — AUDIO STREAM WEBSOCKET ──────────────────────────────────

@app.websocket("/recall/ws/{bot_id}")
async def recall_ws(websocket: WebSocket, bot_id: str):
    """Recall.ai connects here and pushes audio_separate_raw.data events (per-participant PCM).

    Each frame is tagged with participant.id and participant.name.
    Bot audio is dropped immediately — only human audio goes through VAD + Whisper STT.

    Pipeline:
      audio_separate_raw.data → bot identity filter → VAD buffer → Whisper STT
      → agent_inbox → LangGraph → Kokoro TTS → output page WS → meeting
    """
    await websocket.accept()

    session = get_session(bot_id)
    if not session:
        log.warning("[recall] ws: unknown bot_id=%s — closing", bot_id)
        await websocket.close(code=4004, reason="Unknown bot_id")
        return

    log.info("[recall] WS connected: bot=%s store=%s", bot_id, session.store_id)

    from src.agent.voice.stt import LiteLLMSTT
    from src.agent.voice.tts import get_tts

    stt = LiteLLMSTT()

    # One STT callback per participant (created lazily, cached by participant_id)
    _callbacks: dict = {}

    # Audio shorter than this while bot is/was speaking → treated as echo, not user
    _ECHO_GRACE_S    = 1.5   # seconds after TTS ends to keep echo suppression active
    _MIN_INTERRUPT_S = 1.2   # minimum audio duration to treat as a real user interruption

    def _utterance_callback(stream_id: str):
        async def _on_utterance(wav_bytes: bytes) -> None:
            # WAV header is 44 bytes; rest is 16-bit 16kHz mono PCM
            audio_dur = max(0.0, (len(wav_bytes) - 44) / (16000 * 2))
            since_tts = time.monotonic() - session._last_tts_end_ts

            # Suppress echo: short audio while bot is speaking or just finished
            if (session.bot_is_speaking or since_tts < _ECHO_GRACE_S) and audio_dur < _MIN_INTERRUPT_S:
                log.info(
                    "[recall:stt] SKIP_ECHO stream=%s audio=%.2fs bot_speaking=%s since_tts=%.2fs",
                    stream_id[:8], audio_dur, session.bot_is_speaking, since_tts,
                )
                return

            t0 = time.monotonic()
            log.info("[recall:stt] START stream=%s bytes=%d audio=%.2fs", stream_id[:8], len(wav_bytes), audio_dur)
            text = await stt.transcribe(wav_bytes, format="wav")
            t1 = time.monotonic()
            if not text or len(text) < 3:
                log.info("[recall:stt] EMPTY stream=%s stt=%.2fs", stream_id[:8], t1 - t0)
                return
            if session.is_echo(text):
                log.debug("[recall:stt] ECHO_TEXT stream=%s stt=%.2fs: '%s...'", stream_id[:8], t1 - t0, text[:40])
                return
            log.info("[recall:stt] OK stream=%s stt=%.2fs audio=%.2fs → '%s'", stream_id[:8], t1 - t0, audio_dur, text[:80])
            await session.agent_inbox.put(text)
        return _on_utterance

    agent_task = asyncio.create_task(
        _session_core(
            _NullWebSocket(),
            session.store_id,
            partial(_recall_inbox_listener, recall_session=session),
            partial(_recall_tts_sender, tts=get_tts(), recall_session=session),
        )
    )

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                log.debug("[recall:ws] unexpected binary frame %d bytes", len(message["bytes"]))
                continue

            if "text" not in message or not message["text"]:
                continue

            try:
                data = json.loads(message["text"])
            except json.JSONDecodeError:
                log.warning("[recall:ws] non-JSON text: %s", message["text"][:100])
                continue

            event = data.get("event", "<no-event>")
            if event != "audio_separate_raw.data":
                log.info("[recall:ws] event=%s payload=%s", event, str(data)[:200])
                continue

            # Payload structure:
            #   data["data"]["data"]["buffer"]     → base64 PCM audio
            #   data["data"]["audio_separate"]["id"] → audio stream UUID
            # Note: audio_separate has no participant name — rely on Jaccard echo filter
            # for bot-echo safety net (bot logs sentences via log_bot_sentence()).
            outer          = data.get("data", {})
            audio_info     = outer.get("data", {})
            audio_separate = outer.get("audio_separate", {})

            stream_id = audio_separate.get("id") if isinstance(audio_separate, dict) else None
            audio_b64 = audio_info.get("buffer", "") if isinstance(audio_info, dict) else ""

            if not audio_b64 or not stream_id:
                continue

            try:
                pcm_bytes = base64.b64decode(audio_b64)
            except Exception:
                log.debug("[recall:ws] bad base64 from stream=%s", stream_id)
                continue

            if stream_id not in _callbacks:
                _callbacks[stream_id] = _utterance_callback(stream_id)

            buf = session.get_participant_buffer(stream_id, stream_id, _callbacks[stream_id])
            await buf.push(pcm_bytes)

    except (WebSocketDisconnect, RuntimeError):
        log.info("[recall] WS disconnected: bot=%s", bot_id)
    except Exception:
        log.exception("[recall] Error in WS: bot=%s", bot_id)
    finally:
        await session.agent_inbox.put(DISCONNECT)
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
        remove_session(bot_id)
        log.info("[recall] Session cleaned up: bot=%s", bot_id)


# ─── RECALL.AI — BOT MANAGEMENT ──────────────────────────────────────────

# Recall.ai bot status codes that mean the bot is live in the meeting.
_IN_CALL_STATUSES = {"in_call_not_recording", "in_call_recording"}
# Terminal statuses — stop polling.
_TERMINAL_STATUSES = {"call_ended", "done", "fatal", "recording_done"}


async def _setup_bot_when_ready(bot_id: str, screenshare_url: str | None) -> None:
    """Background task: poll bot status and activate outputs once in call.

    Sets screenshare (if provided) and avatar frame as soon as the bot joins.
    Both output_media and output_video endpoints require the bot to be in-call.
    Polls every 3 s (up to 2 min).
    """
    from src.agent.recall.assets import ALIA_AVATAR_B64
    from src.agent.recall.client import RecallClient

    client = RecallClient()
    deadline = time.monotonic() + 120
    poll_interval = 3

    log.info("[recall:setup] Waiting for bot to join: bot=%s", bot_id)
    while time.monotonic() < deadline:
        await asyncio.sleep(poll_interval)
        try:
            bot = await client.get_bot(bot_id)
            changes = bot.get("status_changes") or []
            status = changes[-1].get("code", "") if changes else ""
            log.debug("[recall:setup] bot=%s status=%s", bot_id, status)

            if status in _IN_CALL_STATUSES:
                if screenshare_url:
                    await client.update_output_media(bot_id, screenshare_url=screenshare_url)
                    log.info("[recall:setup] Screenshare active: bot=%s url=%s", bot_id, screenshare_url)

                if ALIA_AVATAR_B64:
                    await client.update_output_video(bot_id, b64_data=ALIA_AVATAR_B64, kind="jpeg")
                    log.info("[recall:setup] Avatar frame set: bot=%s", bot_id)

                return

            if status in _TERMINAL_STATUSES:
                log.info("[recall:setup] Bot ended before joining, giving up: bot=%s status=%s",
                         bot_id, status)
                return
        except Exception:
            log.exception("[recall:setup] Error while waiting for bot: bot=%s", bot_id)

    log.warning("[recall:setup] Timed out waiting for bot to join: bot=%s", bot_id)


@app.post("/recall/bots")
async def create_recall_bot(body: dict):
    """Create a Recall.ai bot and send it to a meeting.

    The bot's camera is set to our TTS audio page (enables voice output).
    If screenshare_url is provided, a background task waits until the bot is
    in the call and then activates screenshare via POST /output_media/.

    Body:
        meeting_url:     str — Google Meet / Zoom / Teams URL
        store_id:        str — store identifier for the Handoff session
        bot_name:        str (optional) — display name in the meeting
        screenshare_url: str (optional) — URL to share as screenshare.
                         Defaults to SCREENSHARE_DEFAULT_URL env var.
                         Pass "" or null explicitly to disable screenshare.
    """
    if not Config.RECALL_API_KEY:
        return JSONResponse({"error": "RECALL_API_KEY not configured"}, status_code=503)

    meeting_url = body.get("meeting_url")
    store_id    = body.get("store_id")
    bot_name    = body.get("bot_name", "Asistente Handoff")

    if "screenshare_url" in body:
        screenshare_url = body["screenshare_url"] or None
    elif Config.SCREENSHARE_DEFAULT_URL:
        # Append store_id as session_id so the frontend poll channel matches
        # the agent's presentation tool, which always uses store_id.
        base_ss = Config.SCREENSHARE_DEFAULT_URL.rstrip("/")
        screenshare_url = f"{base_ss}?session_id={store_id}"
    else:
        screenshare_url = None

    if not meeting_url or not store_id:
        return JSONResponse({"error": "meeting_url and store_id are required"}, status_code=400)

    from src.agent.recall.client import RecallClient

    session_id  = str(uuid.uuid4())
    register_session(session_id, store_id, bot_name=bot_name)
    base_url    = Config.PUBLIC_BASE_URL.rstrip("/")
    ws_base     = base_url.replace("https://", "wss://").replace("http://", "ws://")
    realtime_ws = f"{ws_base}/recall/ws/{session_id}"
    output_page = f"{base_url}/recall/output/{session_id}"

    try:
        client = RecallClient()
        bot = await client.create_bot(
            meeting_url=meeting_url,
            bot_name=bot_name,
            realtime_ws_url=realtime_ws,
            output_page_url=output_page,
        )
        real_bot_id = bot["id"]
        log.info("[recall] Bot created: recall_id=%s session=%s store=%s screenshare=%s",
                 real_bot_id, session_id, store_id, screenshare_url or "none")

        # Always fire: sets screenshare + avatar once the bot is in the call.
        asyncio.create_task(_setup_bot_when_ready(real_bot_id, screenshare_url))

        status_changes = bot.get("status_changes") or []
        status = status_changes[-1].get("code", "created") if status_changes else "created"
        return {
            "recall_bot_id": real_bot_id,
            "session_id": session_id,
            "store_id": store_id,
            "status": status,
            "realtime_ws_url": realtime_ws,
            "output_page_url": output_page,
            "screenshare_url": screenshare_url,
        }
    except Exception as exc:
        remove_session(session_id)
        log.exception("[recall] Failed to create bot")
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/recall/bots/{bot_id}")
async def get_recall_bot(bot_id: str):
    """Get bot status from Recall.ai."""
    if not Config.RECALL_API_KEY:
        return JSONResponse({"error": "RECALL_API_KEY not configured"}, status_code=503)

    from src.agent.recall.client import RecallClient

    try:
        client = RecallClient()
        bot = await client.get_bot(bot_id)
        session = get_session(bot_id)
        return {
            "bot_id": bot_id,
            "status": (bot.get("status_changes") or [{}])[-1].get("code"),
            "session_active": session is not None,
            "output_page_connected": session._output_ws is not None if session else False,
        }
    except Exception as exc:
        log.exception("[recall] Failed to get bot")
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/recall/bots/{bot_id}/screenshare")
async def update_screenshare(bot_id: str, body: dict):
    """Change the screenshare URL for a bot that is already in a meeting.

    Use this to navigate between pages during a session (e.g. switch from
    the intro deck to the Portal Partners mockup).

    Body:
        url: str — New URL to share as screenshare
    """
    if not Config.RECALL_API_KEY:
        return JSONResponse({"error": "RECALL_API_KEY not configured"}, status_code=503)

    url = body.get("url")
    if not url:
        return JSONResponse({"error": "url is required"}, status_code=400)

    from src.agent.recall.client import RecallClient

    try:
        client = RecallClient()
        result = await client.update_output_media(bot_id, screenshare_url=url)
        log.info("[recall] Screenshare updated: bot=%s url=%s", bot_id, url)
        return {"bot_id": bot_id, "screenshare_url": url, "status": "updated", "bot": result}
    except Exception as exc:
        log.exception("[recall] Failed to update screenshare: bot=%s", bot_id)
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.delete("/recall/bots/{bot_id}/screenshare")
async def stop_screenshare(bot_id: str):
    """Stop the screenshare for a bot that is in a meeting."""
    if not Config.RECALL_API_KEY:
        return JSONResponse({"error": "RECALL_API_KEY not configured"}, status_code=503)

    from src.agent.recall.client import RecallClient

    try:
        client = RecallClient()
        await client.stop_output_media(bot_id, screenshare=True)
        log.info("[recall] Screenshare stopped: bot=%s", bot_id)
        return {"bot_id": bot_id, "status": "screenshare_stopped"}
    except Exception as exc:
        log.exception("[recall] Failed to stop screenshare: bot=%s", bot_id)
        return JSONResponse({"error": str(exc)}, status_code=500)
