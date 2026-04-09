"""Presentation control tools for the Handoff agent.

Tool: demo_portal — sends commands to the Portal Partners frontend screenshare.
The agent uses this to demonstrate portal features live during the meeting.
Commands are sent directly to the frontend container via the internal Docker network.
Login is always prepended automatically — the agent only needs to provide the
navigation/visual commands for the section it wants to show.
"""
from __future__ import annotations

import logging

import httpx
from langchain_core.tools import StructuredTool

from src.config import Config

log = logging.getLogger(__name__)

_TOKEN = "rappi_ai_agent_2024"

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

    async def _demo_portal(commands: list[dict]) -> dict:
        """Control the Portal Partners screenshare to demonstrate features to the ally.

        Sends commands that execute in order on the live screenshare.
        Login is handled automatically — you only need to provide the commands
        for what you want to show (navigate, show_card, highlight, etc.).

        Use this when:
        - The ally asks how a section of the portal works
        - You want to navigate to a specific section to show an example
        - You need to demonstrate a feature visually during the session

        IMPORTANT: Do NOT include login commands — they are prepended automatically.
        Start your commands directly with navigate or show_card.

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
            {"delivered": N, "total": N, "errors": [...] | null}
        """
        full_sequence = _LOGIN_PREAMBLE + commands

        base = Config.FRONTEND_BASE_URL.rstrip("/")
        url = f"{base}/api/ai-socket/sse?session_id={store_id}&token={_TOKEN}"

        delivered = 0
        errors: list[str] = []

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
                        err = f"cmd[{i}] {cmd_type}: HTTP {resp.status_code} — {resp.text[:120]}"
                        errors.append(err)
                        log.warning("[presentation] %s", err)
                except Exception as exc:
                    err = f"cmd[{i}] {cmd_type}: {exc}"
                    errors.append(err)
                    log.error("[presentation] %s", err)

        result = {"delivered": delivered, "total": len(full_sequence)}
        if errors:
            result["errors"] = errors  # type: ignore[assignment]
        log.info(
            "[presentation] demo_portal store=%s delivered=%d/%d",
            store_id, delivered, len(full_sequence),
        )
        return result

    return [
        StructuredTool.from_function(
            coroutine=_demo_portal,
            name="demo_portal",
            description=_demo_portal.__doc__,
        ),
    ]
