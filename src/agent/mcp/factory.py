"""Tool factory — creates all agent tools with injected repositories.

This is the composition root for tools. The agent server.py calls this
once per session, passing concrete repo instances. The tools never import
infrastructure directly — they receive repos via closures.

MCP compliance: all tools follow MCP-quality schemas (explicit names,
clear descriptions, typed parameters, semantic error responses).
"""
from __future__ import annotations

from langchain_core.tools import StructuredTool

from src.agent.mcp.tools.meeting_tools import create_meeting_tools
from src.agent.mcp.tools.presentation_tools import create_presentation_tools
from src.agent.mcp.tools.session_tools import create_session_tools
from src.agent.mcp.tools.store_tools import create_store_tools


def create_all_tools(
    store_repo,
    meeting_repo,
    session_repo,
    store_id: str = "",
) -> list[StructuredTool]:
    """Create the full set of Handoff agent tools.

    Args:
        store_repo: StoreRepository implementation
        meeting_repo: MeetingRepository implementation
        session_repo: HandoffSessionRepository implementation

    Returns:
        List of LangChain StructuredTool instances ready for LangGraph binding.
    """
    tools: list[StructuredTool] = []
    tools.extend(create_store_tools(store_repo, meeting_repo, session_repo))
    tools.extend(create_session_tools())
    tools.extend(create_meeting_tools(meeting_repo))
    tools.extend(create_presentation_tools(store_id))
    return tools
