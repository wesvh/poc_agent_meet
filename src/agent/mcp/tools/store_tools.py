"""Store-related tools for the Handoff agent.

Tools 1-4: get_store_context, get_meeting_info, update_onboarding_status, update_store_info.
All tools receive repos via closure (factory pattern) — zero infrastructure imports.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool


def create_store_tools(store_repo, meeting_repo, session_repo) -> list[StructuredTool]:
    """Create store-related tools with injected repositories."""

    async def _get_store_context(store_id: str) -> dict:
        """Retrieve complete ally context from PostgreSQL including store details,
        payment methods, schedule days, and previous session summaries.

        Args:
            store_id: Unique store identifier (e.g., "STORE-001").

        Returns:
            Dictionary with keys: store_name, owner_name, city, category, phone, email,
            onboarding_status, support_channel, payment_methods, schedule_days,
            previous_sessions. Returns error dict if store not found.
        """
        data = await store_repo.get_by_id(store_id)
        if data is None:
            return {"error": True, "message": f"Store not found with id {store_id}", "reason": "store_not_found"}
        # Attach previous sessions for long-term memory
        prev_sessions = await session_repo.get_by_store(store_id, limit=3)
        data["previous_sessions"] = prev_sessions
        return data

    async def _get_meeting_info(store_id: str) -> dict:
        """Retrieve information about the next pending meeting for a store.

        Args:
            store_id: Unique store identifier.

        Returns:
            Dictionary with meeting id, scheduled_at, meeting_link, status.
            Returns error dict if no pending meeting exists.
        """
        meeting = await meeting_repo.get_pending_by_store_id(store_id)
        if meeting is None:
            return {"error": True, "message": f"No pending meeting found for store {store_id}", "reason": "no_pending_meeting"}
        return meeting

    async def _update_onboarding_status(new_status: str) -> dict:
        """Update the onboarding status of the current ally's store.
        Only use after identity verification is complete.

        Args:
            new_status: New status value. Must be one of: pendiente, en_proceso, completado.

        Returns:
            Confirmation dict with updated status.
        """
        valid = {"pendiente", "en_proceso", "completado"}
        if new_status not in valid:
            return {"error": True, "message": f"Invalid status '{new_status}'. Must be one of: {', '.join(valid)}", "reason": "invalid_status"}
        # store_id will be injected by the node from session state
        return {"_deferred": True, "field": "onboarding_status", "value": new_status}

    async def _update_store_info(field: str, value: Any) -> dict:
        """Update a specific field on the current ally's store record.
        Use this to correct data identified during verification or configuration.

        Args:
            field: Column name to update (e.g., "city", "phone", "email", "category").
                   Cannot update store_id.
            value: New value for the field.

        Returns:
            Confirmation dict with updated field and value.
        """
        protected = {"store_id", "data_quality_status", "validation_errors"}
        if field in protected:
            return {"error": True, "message": f"Cannot update protected field '{field}'", "reason": "protected_field"}
        return {"_deferred": True, "field": field, "value": value}

    return [
        StructuredTool.from_function(
            coroutine=_get_store_context,
            name="get_store_context",
            description=_get_store_context.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_get_meeting_info,
            name="get_meeting_info",
            description=_get_meeting_info.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_update_onboarding_status,
            name="update_onboarding_status",
            description=_update_onboarding_status.__doc__,
        ),
        StructuredTool.from_function(
            coroutine=_update_store_info,
            name="update_store_info",
            description=_update_store_info.__doc__,
        ),
    ]
