"""Graph routing — conditional edges for the Handoff conversation flow.

After each agent turn, decides:
- "tools": LLM wants to call tools → route to ToolNode
- "end": session should end → route to end_session
- "respond": LLM produced a text response → END graph (return to user)
"""
from __future__ import annotations

import logging

from src.agent.skills.loader import BLOCK_ORDER
from src.agent.state import HandoffState

log = logging.getLogger(__name__)

MAX_TURNS = 100


def should_continue(state: HandoffState) -> str:
    """Decide the next step after an agent turn."""
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None

    # Check if LLM wants to call tools
    if last_msg and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"

    # Check if all blocks are complete
    blocks = state.get("blocks_completed", {})
    all_done = all(blocks.get(b, False) for b in BLOCK_ORDER)
    if all_done:
        log.info("[routing] All blocks completed — ending session")
        return "end"

    # Check session status
    if state.get("session_status") in ("completed", "abandoned"):
        log.info("[routing] Session status=%s — ending", state["session_status"])
        return "end"

    # Safety: max turns
    if state.get("turn_count", 0) >= MAX_TURNS:
        log.warning("[routing] Max turns (%d) reached — forcing end", MAX_TURNS)
        return "end"

    # LLM responded with text (no tool calls) → return to user
    return "respond"
