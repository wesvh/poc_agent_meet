"""Graph nodes — the core logic functions for each step of the Handoff agent.

System prompt strategy:
  - Set ONCE in load_context (turn 0). Persisted via checkpointer.
  - Only UPDATED when the active block changes (via a lightweight SystemMessage swap).
  - conversation_turn does NOT rebuild the prompt — it just invokes the LLM
    with the existing message history. This saves tokens and enables prompt caching.
"""
from __future__ import annotations

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agent.llm import get_cheap_llm, get_main_llm, get_router_llm
from src.agent.prompts.system import build_system_prompt, build_skill_update
from src.agent.skills.loader import get_next_block, load_skill
from src.agent.state import HandoffState
from src.agent.streaming import get_token_queue

log = logging.getLogger(__name__)


async def load_context(state: HandoffState) -> dict:
    """First node: runs on every graph invocation but only initializes ONCE.

    On first call (session_status not set): sets up system prompt, checklist, state.
    On subsequent calls: passes through without changes (state already initialized).
    """
    # Skip if already initialized (subsequent turns via checkpointer)
    if state.get("session_status") == "active" and state.get("blocks_completed"):
        log.debug("[node:load_context] Already initialized, skipping")
        return {}

    log.info("[node:load_context] Initializing context for store=%s", state["store_id"])

    blocks_completed = {
        "saludo": False,
        "verificacion": False,
        "diagnostico": False,
        "configuracion": False,
        "capacitacion": False,
        "resolucion": False,
        "compromiso": False,
        "cierre": False,
    }

    current_block = get_next_block(blocks_completed) or "saludo"
    skill = load_skill(current_block)

    system_prompt = build_system_prompt(
        store_context=state.get("store_context") or {},
        blocks_completed=blocks_completed,
        active_skill_prompt=skill.prompt,
    )

    return {
        "blocks_completed": blocks_completed,
        "current_block": current_block,
        "active_skill_prompt": skill.prompt,
        "issues_detected": [],
        "commitments": [],
        "collected_data": {},
        "session_status": "active",
        "turn_count": 0,
        "messages": [SystemMessage(content=system_prompt)],
    }


async def conversation_turn(state: HandoffState, tools: list | None = None) -> dict:
    """Main conversation node: invoke the LLM with the existing message history.

    Does NOT rebuild the system prompt. Uses the messages as-is from state
    (system prompt set in load_context, accumulated via add_messages reducer).
    This avoids sending duplicate tokens and enables provider prompt caching.
    """
    turn = state.get("turn_count", 0)
    log.info("[node:conversation_turn] turn=%d block=%s", turn, state.get("current_block"))

    # Use messages as-is — system prompt is already in messages[0]
    messages = list(state["messages"])

    # Router LLM: orchestrates tool calls and block transitions
    llm = get_router_llm()
    if tools:
        llm = llm.bind_tools(tools)

    # Stream tokens into the shared queue for real-time WebSocket delivery
    token_queue = get_token_queue()
    full_response = None

    async for chunk in llm.astream(messages):
        if full_response is None:
            full_response = chunk
        else:
            full_response = full_response + chunk

        # Push text tokens to queue (skip tool call chunks)
        if token_queue and hasattr(chunk, "content") and chunk.content:
            if isinstance(chunk.content, str) and chunk.content:
                has_tool_calls = hasattr(chunk, "tool_calls") and chunk.tool_calls
                if not has_tool_calls:
                    await token_queue.put(("token", chunk.content))

    # Signal end of this LLM response
    if token_queue:
        has_tools = full_response and hasattr(full_response, "tool_calls") and full_response.tool_calls
        if not has_tools:
            await token_queue.put(("message_end", None))
        else:
            for tc in full_response.tool_calls:
                tool_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                await token_queue.put(("thinking", tool_name))

    if full_response is None:
        full_response = AIMessage(content="")

    return {
        "messages": [full_response],
        "turn_count": turn + 1,
    }


async def process_tool_results(state: HandoffState) -> dict:
    """Process tool call results and apply state mutations.

    When a block is completed, injects a lightweight SystemMessage
    with the new skill instructions — NOT a full prompt rebuild.
    """
    updates: dict = {}
    messages = state.get("messages", [])

    for msg in reversed(messages[-10:]):
        if not hasattr(msg, "content"):
            continue
        try:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if "_state_update" not in content and "_deferred" not in content:
                continue
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue

        if data.get("_state_update") == "add_issue":
            issues = list(state.get("issues_detected", []))
            issues.append(data["issue"])
            updates["issues_detected"] = issues

        elif data.get("_state_update") == "add_commitment":
            commitments = list(state.get("commitments", []))
            commitments.append(data["commitment"])
            updates["commitments"] = commitments

        elif data.get("_state_update") == "complete_block":
            blocks = dict(state.get("blocks_completed", {}))
            blocks[data["block"]] = True
            updates["blocks_completed"] = blocks

            next_block = get_next_block(blocks)
            if next_block:
                updates["current_block"] = next_block
                skill = load_skill(next_block)
                updates["active_skill_prompt"] = skill.prompt
                # Inject a lightweight skill transition message (NOT a full system prompt rebuild)
                skill_msg = SystemMessage(content=build_skill_update(next_block, skill.prompt, blocks))
                updates["messages"] = [skill_msg]
                log.info("[node:process_results] Block '%s' done → advancing to '%s'", data["block"], next_block)

    return updates


async def end_session(state: HandoffState) -> dict:
    """Final node: generate summary, mark session as completed.

    Uses the cheap LLM to minimize costs on this non-critical task.
    """
    log.info("[node:end_session] Ending session %s for store %s", state["session_id"], state["store_id"])

    summary_prompt = f"""Resume esta sesion de Handoff en maximo 150 palabras. Texto plano, sin markdown.

Aliado: {state.get('store_context', {}).get('store_name', 'N/A')} ({state['store_id']})
Bloques completados: {json.dumps(state.get('blocks_completed', {}), ensure_ascii=False)}
Problemas: {json.dumps(state.get('issues_detected', []), ensure_ascii=False)}
Compromisos: {json.dumps(state.get('commitments', []), ensure_ascii=False)}
Turnos: {state.get('turn_count', 0)}"""

    cheap_llm = get_cheap_llm()
    summary_response = await cheap_llm.ainvoke([HumanMessage(content=summary_prompt)])

    farewell = AIMessage(content="Listo, quedo todo registrado. Que tenga un excelente dia.")

    return {
        "session_status": "completed",
        "messages": [farewell],
    }
