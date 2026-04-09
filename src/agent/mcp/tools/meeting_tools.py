"""Meeting-related tools for the Handoff agent.

Tools 10-11: update_meeting_status, schedule_followup.
"""
from __future__ import annotations

from datetime import datetime

from langchain_core.tools import StructuredTool


def create_meeting_tools(meeting_repo) -> list[StructuredTool]:
    """Create meeting-related tools with injected repository."""

    async def _update_meeting_status(meeting_id: str, status: str) -> dict:
        """Update the status of a meeting.
        Use this to mark the current meeting as completed when the session ends,
        or as cancelled if the ally did not attend.

        Args:
            meeting_id: UUID of the meeting to update.
            status: New status. Must be one of: pending, completed, cancelled.

        Returns:
            Confirmation dict with updated meeting id and status.
        """
        valid = {"pending", "completed", "cancelled"}
        if status not in valid:
            return {"error": True, "message": f"Invalid status '{status}'. Must be one of: {', '.join(valid)}", "reason": "invalid_status"}
        try:
            await meeting_repo.update_status(meeting_id, status)
            return {"success": True, "meeting_id": meeting_id, "status": status}
        except ValueError as e:
            return {"error": True, "message": str(e), "reason": "meeting_not_found"}

    async def _schedule_followup(store_id: str, scheduled_at: str, meeting_link: str = "") -> dict:
        """Schedule a follow-up meeting for the ally.
        Use this when the ally agrees to a follow-up session during the closing block.

        Args:
            store_id: Store identifier for the follow-up.
            scheduled_at: ISO 8601 datetime for the follow-up (e.g., "2026-04-15T10:00:00-05:00").
            meeting_link: Optional video call link for the follow-up.

        Returns:
            Confirmation that the follow-up was scheduled.
        """
        try:
            dt = datetime.fromisoformat(scheduled_at)
        except ValueError:
            return {"error": True, "message": f"Invalid datetime format: {scheduled_at}. Use ISO 8601.", "reason": "invalid_datetime"}

        await meeting_repo.upsert(store_id, dt, meeting_link or None)
        return {"success": True, "store_id": store_id, "scheduled_at": scheduled_at, "meeting_link": meeting_link}

    return [
        StructuredTool.from_function(
            coroutine=_update_meeting_status,
            name="update_meeting_status",
            description=_update_meeting_status.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_schedule_followup,
            name="schedule_followup",
            description=_schedule_followup.__doc__,
        ),
    ]
