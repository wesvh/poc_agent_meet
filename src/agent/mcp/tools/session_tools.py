"""Session-related tools for the Handoff agent.

Tools 5-9: record_issue, record_commitment, mark_block_complete,
get_session_summary, save_session_transcript.

These tools primarily operate on the agent's internal state.
State mutations are returned as dicts and applied by the graph node.
"""
from __future__ import annotations

from langchain_core.tools import StructuredTool

from src.agent.skills.loader import BLOCK_ORDER


def create_session_tools() -> list[StructuredTool]:
    """Create session-related tools (state-only, no repo needed)."""

    async def _record_issue(description: str, category: str = "general") -> dict:
        """Register a problem or issue identified during the conversation.
        Use this whenever the ally reports a difficulty or you detect a discrepancy.

        Args:
            description: Clear description of the issue (e.g., "Menu not updated in 3 months").
            category: Issue category. One of: tecnico, operativo, financiero, capacitacion, general.

        Returns:
            Confirmation with the recorded issue.
        """
        return {"_state_update": "add_issue", "issue": f"[{category}] {description}"}

    async def _record_commitment(description: str, responsible: str = "rappi") -> dict:
        """Register a commitment agreed upon during the session.
        Use this for action items that either Rappi or the ally commits to.

        Args:
            description: Clear description of the commitment (e.g., "Update menu with current prices by Friday").
            responsible: Who is responsible. One of: rappi, aliado, ambos.

        Returns:
            Confirmation with the recorded commitment.
        """
        return {"_state_update": "add_commitment", "commitment": f"[{responsible}] {description}"}

    async def _mark_block_complete(block_name: str) -> dict:
        """Mark a conversation block as completed in the session checklist.
        Only mark a block when its objectives have been fully achieved.

        Args:
            block_name: Name of the block to mark as complete.
                        Must be one of: saludo, verificacion, diagnostico, configuracion,
                        capacitacion, resolucion, compromiso, cierre.

        Returns:
            Confirmation with updated checklist status and suggested next block.
        """
        if block_name not in BLOCK_ORDER:
            return {"error": True, "message": f"Unknown block '{block_name}'. Valid blocks: {', '.join(BLOCK_ORDER)}", "reason": "invalid_block"}
        return {"_state_update": "complete_block", "block": block_name}

    async def _get_session_summary() -> dict:
        """Get a summary of the current session state including completed blocks,
        issues detected, and commitments made. Use this to review progress
        before closing or when the ally asks for a recap.

        Returns:
            Dictionary with blocks_completed, issues_detected, commitments, and turn_count.
        """
        # Actual data will be injected by the node from state
        return {"_state_read": "session_summary"}

    async def _save_session_transcript() -> dict:
        """Persist the full conversation transcript to the database.
        This is normally called automatically at session end, but can be
        triggered manually if needed (e.g., before a potential disconnection).

        Returns:
            Confirmation that transcript was saved.
        """
        return {"_state_update": "save_transcript"}

    return [
        StructuredTool.from_function(
            coroutine=_record_issue,
            name="record_issue",
            description=_record_issue.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_record_commitment,
            name="record_commitment",
            description=_record_commitment.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_mark_block_complete,
            name="mark_block_complete",
            description=_mark_block_complete.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_get_session_summary,
            name="get_session_summary",
            description=_get_session_summary.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_save_session_transcript,
            name="save_session_transcript",
            description=_save_session_transcript.__doc__,
        ),
    ]
