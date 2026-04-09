"""LLM abstraction layer via LiteLLM.

Three model tiers:
- Router LLM:  orchestrator that decides tool calls and block transitions (gpt-4.1-mini).
- Main LLM:    final responder for direct user-facing text (gpt-4.1-nano).
- Cheap LLM:   atomic background tasks — summaries, classification (gpt-4.1-nano).

All use LiteLLM so the provider can be swapped via env vars.
drop_params is enabled to silently discard unsupported params across providers.
"""
from __future__ import annotations

import litellm
from langchain_litellm import ChatLiteLLM

from src.config import Config

litellm.drop_params = True


def get_router_llm() -> ChatLiteLLM:
    """Orchestrator LLM — decides tool calls, block transitions, and flow routing."""
    return ChatLiteLLM(
        model=Config.AGENT_ROUTER_MODEL,
        temperature=Config.AGENT_TEMPERATURE,
        max_tokens=Config.AGENT_MAX_TOKENS,
    )


def get_main_llm() -> ChatLiteLLM:
    """Final responder LLM — direct user-facing text generation."""
    return ChatLiteLLM(
        model=Config.AGENT_MODEL,
        temperature=Config.AGENT_TEMPERATURE,
        max_tokens=Config.AGENT_MAX_TOKENS,
    )


def get_cheap_llm() -> ChatLiteLLM:
    """Lightweight LLM for summaries, classification, and low-stakes tasks."""
    return ChatLiteLLM(
        model=Config.AGENT_CHEAP_MODEL,
        temperature=0.3,
        max_tokens=1000,
    )
