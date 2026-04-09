"""LangGraph StateGraph — the Handoff conversation flow.

Architecture: The graph runs one "turn" at a time:
    load_context → agent (LLM + tools) → process_results → END

Each invocation processes one user message and returns.
The checkpointer preserves state between invocations so the next
user message resumes where the conversation left off.

Tool calls are handled via LangGraph's prebuilt ToolNode.
"""
from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.agent.nodes import conversation_turn, end_session, load_context, process_tool_results
from src.agent.routing import should_continue
from src.agent.state import HandoffState

log = logging.getLogger(__name__)


def build_graph(tools: list) -> StateGraph:
    """Build the Handoff conversation graph.

    Args:
        tools: List of LangChain StructuredTool instances (from factory).

    Returns:
        StateGraph (not yet compiled — caller must compile with checkpointer).
    """
    # Bind tools to the conversation_turn node via closure
    async def agent_node(state: HandoffState) -> dict:
        return await conversation_turn(state, tools=tools)

    graph = StateGraph(HandoffState)

    # --- Nodes ---
    graph.add_node("load_context", load_context)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("process_results", process_tool_results)
    graph.add_node("end_session", end_session)

    # --- Edges ---
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "agent")

    # After agent: check if it wants to call tools, end, or return to user
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",        # LLM wants to call a tool
            "end": "end_session",     # All blocks done or session over
            "respond": END,           # AI responded with text → return to user
        },
    )

    # After tool execution: process state updates, then back to agent
    graph.add_edge("tools", "process_results")
    graph.add_edge("process_results", "agent")

    # End session terminates
    graph.add_edge("end_session", END)

    log.info("[graph] Handoff graph built with %d tools", len(tools))
    return graph
