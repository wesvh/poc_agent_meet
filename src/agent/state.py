"""Handoff agent state definition.

Pure TypedDict — no external dependencies. This is the single source of truth
for what data flows through the LangGraph StateGraph.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class HandoffState(TypedDict):
    """Full state for a Handoff conversation session."""

    # --- Identification (injected programmatically, NEVER by the LLM) ---
    session_id: str
    store_id: str
    meeting_id: str | None

    # --- Messages (LangGraph native with add_messages reducer) ---
    messages: Annotated[list[BaseMessage], add_messages]

    # --- Ally context (pre-loaded once in load_context) ---
    store_context: dict
    meeting_context: dict

    # --- Block checklist (LLM marks via mark_block_complete tool) ---
    blocks_completed: dict  # {"saludo": True, "verificacion": False, ...}
    current_block: str | None
    active_skill_prompt: str | None

    # --- Data collected during the session ---
    collected_data: dict
    issues_detected: list[str]
    commitments: list[str]

    # --- Control ---
    session_status: str  # "active", "completed", "abandoned"
    turn_count: int
