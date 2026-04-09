"""Message trimming configuration for context window management.

Limits the conversation history to prevent token overflow while
preserving the system prompt and most recent exchanges.
"""
from __future__ import annotations

from langchain_core.messages import trim_messages

# Trim configuration
TRIMMER = trim_messages(
    max_tokens=4000,
    strategy="last",
    token_counter=len,  # Approximation; replace with tiktoken for accuracy
    include_system=True,
    start_on="human",
)


def trim_state_messages(messages: list) -> list:
    """Apply message trimming to keep context within limits.

    Preserves: system message + last N messages that fit in 4000 tokens.
    """
    return TRIMMER.invoke(messages)
