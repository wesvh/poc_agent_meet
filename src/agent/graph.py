"""LangGraph StateGraph — the Handoff conversation flow.

Architecture: The graph runs one "turn" at a time:
    load_context → agent (LLM + tools) → process_results → END

Each invocation processes one user message and returns.
The checkpointer preserves state between invocations so the next
user message resumes where the conversation left off.

Tool calls are handled by _make_guarded_tool_node, which:
  - Runs Layer 2 guardrails (validate_tool_call) before each execution.
  - Intercepts get_session_summary to return real state data directly.
"""
from __future__ import annotations

import json
import logging

from langchain_core.messages import ToolMessage
from langgraph.graph import END, StateGraph

from src.agent.guardrails import validate_tool_call
from src.agent.nodes import conversation_turn, end_session, load_context, process_tool_results
from src.agent.routing import should_continue
from src.agent.state import HandoffState

log = logging.getLogger(__name__)


def _make_guarded_tool_node(tools: list):
    """Build a tool executor node with Layer 2 guardrails and state injection.

    Replaces the prebuilt ToolNode with three behaviours:
      1. Runs validate_tool_call() before each tool — blocks calls that
         violate business rules and returns an error ToolMessage instead.
      2. Handles get_session_summary by reading live state directly —
         the tool itself returns a placeholder; we replace it here with
         real data so the LLM always gets an accurate session summary.
      3. Executes all other tools normally via tool.ainvoke().
    """
    tool_map = {t.name: t for t in tools}

    async def _guarded_tools(state: HandoffState) -> dict:
        messages = state.get("messages", [])
        last_msg = messages[-1] if messages else None

        if not last_msg or not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
            return {}

        tool_messages: list[ToolMessage] = []

        for tc in last_msg.tool_calls:
            # Normalise: tool_calls may be dicts or objects depending on provider
            if isinstance(tc, dict):
                tool_name = tc["name"]
                tool_args = tc.get("args") or {}
                tool_id   = tc["id"]
            else:
                tool_name = tc.name
                tool_args = getattr(tc, "args", None) or {}
                tool_id   = tc.id

            # ── Layer 2 guardrails ──────────────────────────────────────────
            block_reason = validate_tool_call(tool_name, tool_args, state)
            if block_reason:
                log.warning("[tools] BLOCKED %s: %s", tool_name, block_reason)
                content = json.dumps(
                    {"error": True, "message": block_reason, "reason": "guardrail_blocked"},
                    ensure_ascii=False,
                )
                tool_messages.append(ToolMessage(content=content, tool_call_id=tool_id, name=tool_name))
                continue

            # ── get_session_summary: inject live state ──────────────────────
            if tool_name == "get_session_summary":
                summary = {
                    "blocks_completed": state.get("blocks_completed", {}),
                    "issues_detected":  state.get("issues_detected", []),
                    "commitments":      state.get("commitments", []),
                    "turn_count":       state.get("turn_count", 0),
                    "session_status":   state.get("session_status", "active"),
                    "current_block":    state.get("current_block"),
                }
                tool_messages.append(ToolMessage(
                    content=json.dumps(summary, ensure_ascii=False),
                    tool_call_id=tool_id,
                    name=tool_name,
                ))
                continue

            # ── Normal tool execution ───────────────────────────────────────
            tool = tool_map.get(tool_name)
            if tool is None:
                content = json.dumps({"error": True, "message": f"Tool '{tool_name}' not found"})
                tool_messages.append(ToolMessage(content=content, tool_call_id=tool_id, name=tool_name))
                continue

            try:
                result = await tool.ainvoke(tool_args)
                content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
            except Exception as exc:
                log.exception("[tools] Exception in tool '%s'", tool_name)
                content = json.dumps({"error": True, "message": str(exc)})

            tool_messages.append(ToolMessage(content=content, tool_call_id=tool_id, name=tool_name))

        return {"messages": tool_messages}

    return _guarded_tools


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
    graph.add_node("tools", _make_guarded_tool_node(tools))
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
