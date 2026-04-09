"""Runtime guardrails — deterministic validation of tool calls (Layer 2).

These checks run BEFORE a tool is executed. They enforce business rules
that cannot be reliably handled by prompt-level instructions alone.

Layer 1 (prompt) is in src/agent/prompts/guardrails.py
Layer 3 (LLM proxy) is configured in LiteLLM
"""
from __future__ import annotations

import logging

from src.agent.state import HandoffState

log = logging.getLogger(__name__)

# Fields that tools should never update
PROTECTED_FIELDS = {"store_id", "data_quality_status", "validation_errors"}


def validate_tool_call(tool_name: str, args: dict, state: HandoffState) -> str | None:
    """Validate a tool call against business rules.

    Returns:
        None if the call is allowed, or an error message string if blocked.
    """
    # Rule: cannot update onboarding status before identity verification
    if tool_name == "update_onboarding_status":
        if not state.get("blocks_completed", {}).get("verificacion"):
            msg = "Cannot update onboarding status before identity verification is complete."
            log.warning("[guardrails] BLOCKED %s: %s", tool_name, msg)
            return msg

    # Rule: store_id in tool args must match session store_id (prevent injection)
    if "store_id" in args:
        session_store = state.get("store_id")
        if session_store and args["store_id"] != session_store:
            msg = f"store_id mismatch: tool arg '{args['store_id']}' != session '{session_store}'. Blocked for security."
            log.warning("[guardrails] BLOCKED %s: %s", tool_name, msg)
            return msg

    # Rule: protected fields cannot be updated via update_store_info
    if tool_name == "update_store_info":
        field = args.get("field", "")
        if field in PROTECTED_FIELDS:
            msg = f"Cannot update protected field '{field}'."
            log.warning("[guardrails] BLOCKED %s: %s", tool_name, msg)
            return msg

    # Rule: mark_block_complete("cierre") should only happen when all other blocks are done
    if tool_name == "mark_block_complete" and args.get("block_name") == "cierre":
        blocks = state.get("blocks_completed", {})
        missing = [b for b in ["saludo", "verificacion", "diagnostico", "configuracion", "capacitacion", "resolucion", "compromiso"] if not blocks.get(b)]
        if missing:
            msg = f"Cannot close session — incomplete blocks: {', '.join(missing)}."
            log.warning("[guardrails] BLOCKED %s: %s", tool_name, msg)
            return msg

    return None
