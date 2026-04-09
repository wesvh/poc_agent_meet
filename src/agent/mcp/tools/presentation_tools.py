"""Presentation control tools for the Handoff agent.

Tools:
  - inspect_portal_screen: fetches a semantic description of a Portal Partners
    screen so the agent knows what is visible, where it is placed, and which
    selectors exist for visual guidance.
  - demo_portal: sends commands to the Portal Partners frontend screenshare.

Commands are sent directly to the frontend container via the internal Docker
network. Login is always prepended automatically to demo_portal, so the agent
only needs to provide navigation/visual commands for the section it wants to
show.

Demo commands are dispatched as a background task so the agent can continue
speaking without waiting for HTTP delivery — avoids blocking TTS during demo
sequences.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from langchain_core.tools import StructuredTool

from src.agent.recall.bridge import get_session_by_store
from src.config import Config

log = logging.getLogger(__name__)

_TOKEN = "rappi_ai_agent_2024"

# Holds references to fire-and-forget tasks to prevent premature GC.
_background_tasks: set[asyncio.Task] = set()

# Prepended automatically to every demo_portal call.
# Resets state and logs in regardless of what the screen was showing.
_LOGIN_PREAMBLE: list[dict] = [
    {"cmd": "simulate_logout",  "payload": {}},
    {"cmd": "set_auth_view",    "payload": {"view": "login"}},
    {"cmd": "wait",             "payload": {"ms": 400}},
    {"cmd": "simulate_login",   "payload": {
        "email": "admin@latoscana.com",
        "password": "demo123",
        "typeSpeed": 35,
    }},
    {"cmd": "wait",             "payload": {"ms": 2500}},
]


def create_presentation_tools(store_id: str) -> list[StructuredTool]:
    """Create presentation control tools with injected store_id."""

    # Auth memory: tracks whether the frontend screenshare is already logged in
    # for this session. Avoids redundant logout→login sequences on every demo call.
    _auth_state: dict = {"authenticated": False}

    # Portal position: tracks which section is currently visible on the screenshare.
    # Updated on every navigate command so the agent always knows where it is.
    # Starts as None (unknown) — set to "dashboard" after login.
    _portal_position: dict = {"section": None}

    async def _inspect_portal_screen(
        screen: str = "dashboard",
        authenticated: bool = True,
    ) -> dict:
        """Inspect a Portal Partners screen and return semantic UI context.

        Use this BEFORE explaining or demoing a screen when you need grounding.
        It returns a structured description of:
        - screen goal and layout
        - key regions and where they appear
        - important buttons/inputs/cards and their selectors
        - suggested demo steps and talking points

        Good use cases:
        - You want to explain what the ally should be seeing on a screen
        - You need to know which selector can be highlighted safely
        - You are about to call demo_portal and want factual UI context first

        Args:
            screen: login|register|forgot-password|dashboard|catalog|finances|disputes|schedule|support
            authenticated: Whether to resolve the screen as an authenticated portal view.

        Returns:
            Full JSON payload from /api/inspect-screen with rich screen context.
        """
        base = Config.FRONTEND_BASE_URL.rstrip("/")
        url = f"{base}/api/inspect-screen"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url,
                params={
                    "token": _TOKEN,
                    "screen": screen,
                    "authenticated": str(authenticated).lower(),
                    "store_id": store_id,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def _demo_portal(commands: Any) -> dict:
        """Control the Portal Partners screenshare to demonstrate features to the ally.

        Sends commands that execute in order on the live screenshare.
        Login is handled automatically — you only need to provide the commands
        for what you want to show (navigate, show_card, highlight, etc.).

        Use this when:
        - The ally asks how a section of the portal works
        - You want to navigate to a specific section to show an example
        - You need to demonstrate a feature visually during the session
        - You already inspected the screen or you are certain about the selectors

        IMPORTANT: Do NOT include login commands — they are prepended automatically.
        Always start your commands with a navigate command to go to the intended section
        BEFORE using highlight, show_card, or show_tooltip. Never assume the portal is
        already on the right section — always navigate explicitly.
        After login the portal is always on "dashboard". Each call to demo_portal
        returns "portal_section" so you always know where the screen is.
        If you are unsure what the screen contains, call inspect_portal_screen first.

        Args:
            commands: Ordered list of commands to run AFTER login. Each item:
                      {"cmd": "<type>", "payload": {...}}

                      NAVIGATION
                        navigate       {"section": "dashboard|catalog|finances|disputes|schedule|support"}

                      VISUAL FEEDBACK
                        show_card    {"title":"...", "body":"...", "type":"info|success|warning|error",
                                      "position":"top-right|bottom-right|center", "duration": 2500}
                        highlight    {"selector":"#id", "style":"pulse|glow|outline", "duration":2000,
                                      "label":"optional text"}
                        show_tooltip {"selector":"#id", "text":"...", "position":"top|bottom|left|right",
                                      "duration":3000}
                        clear_overlays {"scope":"all|highlights|tooltips|cards"}

                      FLOW
                        wait         {"ms": 1500}
                        get_state    {}   ← returns auth status, current section, active overlays

        Returns:
            {"queued": N, "total": N, "portal_section": "current section"} — commands dispatched
            in background, agent continues immediately. portal_section tells you where the
            screen will be after the commands execute.
        """
        # Normalize: LLMs sometimes pass commands as a JSON string instead of a list.
        if isinstance(commands, str):
            try:
                commands = json.loads(commands)
            except Exception:
                commands = []
        if not isinstance(commands, list):
            commands = []

        if _auth_state["authenticated"]:
            full_sequence = commands
        else:
            full_sequence = _LOGIN_PREAMBLE + commands
            _auth_state["authenticated"] = True
            # After login the portal always lands on the dashboard.
            _portal_position["section"] = "dashboard"

        # Track the last navigate command so the agent knows where it will end up.
        for cmd in commands:
            if cmd.get("cmd") == "navigate":
                section = cmd.get("payload", {}).get("section")
                if section:
                    _portal_position["section"] = section

        base = Config.FRONTEND_BASE_URL.rstrip("/")
        url = f"{base}/api/ai-socket/sse?session_id={store_id}&token={_TOKEN}"

        async def _send_commands():
            delivered = 0
            async with httpx.AsyncClient(timeout=10.0) as client:
                for i, cmd in enumerate(full_sequence):
                    cmd_type = cmd.get("cmd", "unknown")
                    try:
                        resp = await client.post(url, json={
                            "cmd": cmd_type,
                            "payload": cmd.get("payload", {}),
                            "request_id": f"agent_{store_id}_{i:03d}",
                        })
                        if resp.is_success:
                            delivered += 1
                        else:
                            log.warning(
                                "[presentation] cmd[%d] %s: HTTP %d — %s",
                                i, cmd_type, resp.status_code, resp.text[:120],
                            )
                    except Exception as exc:
                        log.error("[presentation] cmd[%d] %s: %s", i, cmd_type, exc)
            log.info(
                "[presentation] demo_portal store=%s delivered=%d/%d",
                store_id, delivered, len(full_sequence),
            )

        task = asyncio.create_task(_send_commands())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        log.info("[presentation] demo_portal queued %d commands for store=%s", len(full_sequence), store_id)
        return {
            "queued": len(full_sequence),
            "total": len(full_sequence),
            "portal_section": _portal_position["section"],
        }

    async def _show_slide(slide_number: int) -> dict:
        """Display a presentation slide full-screen on the shared frontend.

        Slides are rendered by the frontend (Portal Partners screenshare page),
        covering the entire screen. All meeting participants see the slide immediately.
        Use this to advance through the 7-slide deck during the session.

        Slide map (block → slide):
          1 — Portada / Bienvenida        (saludo — shown automatically on join)
          2 — Agenda de la sesión         (verificacion)
          3 — Objetivo principal          (diagnostico)
          4 — RappiAliados vs Portal      (capacitacion) ← start_screenshare() for live demo
          5 — Checklist de activación     (configuracion)
          6 — Condiciones y próximos      (compromiso)
          7 — Cierre y preguntas          (cierre)

        Rules:
        - Advance to the next slide BEFORE explaining that section's content.
        - For slides 4, 5, or 7: if the ally wants to see the live portal, call
          start_screenshare() — this hides the slide and shows the live portal.
        - Do NOT skip slides unless the ally explicitly asks to.

        Args:
            slide_number: Integer 1–7.

        Returns:
            {"status": "shown", "slide": N, "portal_suggested": bool} on success.
            {"status": "error", "reason": "..."} if slide out of range.
        """
        from src.agent.recall.slides import PORTAL_SLIDES, TOTAL_SLIDES

        if not (1 <= slide_number <= TOTAL_SLIDES):
            return {"status": "error", "reason": f"slide {slide_number} out of range (1-{TOTAL_SLIDES})"}

        base = Config.FRONTEND_BASE_URL.rstrip("/")
        url = f"{base}/api/ai-socket/sse?session_id={store_id}&token={_TOKEN}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json={
                    "cmd": "show_slide",
                    "payload": {"slide": slide_number},
                    "request_id": f"slide_{store_id}_{slide_number}",
                })
                if not resp.is_success:
                    log.warning(
                        "[presentation] show_slide %d HTTP %d: %s",
                        slide_number, resp.status_code, resp.text[:120],
                    )
                    return {"status": "error", "reason": f"HTTP {resp.status_code}"}
            except Exception as exc:
                log.error("[presentation] show_slide %d: %s", slide_number, exc)
                return {"status": "error", "reason": str(exc)}

        log.info("[presentation] show_slide %d sent to frontend for store=%s", slide_number, store_id)
        return {
            "status": "shown",
            "slide": slide_number,
            "portal_suggested": slide_number in PORTAL_SLIDES,
        }

    async def _start_screenshare() -> dict:
        """Activate the screenshare in the current Recall.ai meeting session.

        Call this ONLY after the ally has confirmed they are ready to see the screen.
        This sends the Portal Partners page as a screenshare visible to all meeting
        participants. The tool is a no-op when there is no active Recall session
        (e.g. text or voice-only mode).

        Typical usage:
        1. Say "Enseguida te comparto la pantalla, ¿me confirmas cuando estés listo?"
        2. Wait for the ally's confirmation.
        3. Call start_screenshare().
        4. Proceed with demo_portal commands.

        Returns:
            {"status": "activated", "screenshare_url": "..."} on success.
            {"status": "skipped", "reason": "..."} when there is no active Recall session.
        """
        session = get_session_by_store(store_id)
        if not session or not session.recall_bot_id:
            log.info("[presentation] start_screenshare: no active Recall session for store=%s", store_id)
            return {"status": "skipped", "reason": "no active Recall session"}

        if not session.screenshare_url:
            log.info("[presentation] start_screenshare: no screenshare_url configured for store=%s", store_id)
            return {"status": "skipped", "reason": "screenshare_url not configured"}

        # Hide the current slide so the live portal is visible on the screenshare.
        base = Config.FRONTEND_BASE_URL.rstrip("/")
        sse_url = f"{base}/api/ai-socket/sse?session_id={store_id}&token={_TOKEN}"
        async with httpx.AsyncClient(timeout=5.0) as client_http:
            try:
                await client_http.post(sse_url, json={
                    "cmd": "hide_slide",
                    "payload": {},
                    "request_id": f"hide_slide_{store_id}",
                })
            except Exception as exc:
                log.warning("[presentation] hide_slide request failed: %s", exc)

        # Immediately log in to the portal so the ally sees the dashboard,
        # not the login page, as soon as the screenshare appears.
        await _demo_portal([])

        log.info("[presentation] start_screenshare: portal live for store=%s", store_id)
        return {"status": "activated", "screenshare_url": session.screenshare_url}

    return [
        StructuredTool.from_function(
            coroutine=_inspect_portal_screen,
            name="inspect_portal_screen",
            description=_inspect_portal_screen.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_demo_portal,
            name="demo_portal",
            description=_demo_portal.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_start_screenshare,
            name="start_screenshare",
            description=_start_screenshare.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_show_slide,
            name="show_slide",
            description=_show_slide.__doc__,
        ),
    ]
