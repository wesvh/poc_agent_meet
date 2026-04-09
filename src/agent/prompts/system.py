"""System prompt builder.

Strategy:
  - build_system_prompt() is called ONCE at session start (load_context).
    It contains persona + guardrails + store context + initial skill.
    This is the "heavy" system message that gets prompt-cached by the provider.

  - build_skill_update() is called only when a block changes.
    It injects a lightweight SystemMessage with the new skill instructions.
    This avoids rebuilding the full prompt and saves tokens.
"""
from __future__ import annotations

from src.agent.prompts.guardrails import GUARDRAILS_PROMPT
from src.agent.prompts.persona import PERSONA_PROMPT
from src.agent.skills.loader import BLOCK_ORDER


def build_system_prompt(
    store_context: dict,
    blocks_completed: dict[str, bool],
    active_skill_prompt: str | None = None,
) -> str:
    """Build the FULL system prompt. Called ONCE at session start."""
    parts: list[str] = []

    parts.append(PERSONA_PROMPT)
    parts.append(GUARDRAILS_PROMPT)

    # Store context as reference
    context_summary = _format_store_context(store_context)
    parts.append(f"## Datos del Aliado (referencia interna, no recites todo)\n\n{context_summary}")

    # Initial checklist
    checklist = _format_checklist(blocks_completed)
    parts.append(f"## Checklist (guia interna)\n\n{checklist}")

    # First skill
    if active_skill_prompt:
        parts.append(active_skill_prompt)

    return "\n\n---\n\n".join(parts)


def build_skill_update(
    new_block: str,
    skill_prompt: str,
    blocks_completed: dict[str, bool],
) -> str:
    """Build a lightweight skill transition message.

    Injected as a SystemMessage when the active block changes.
    Much smaller than the full system prompt — only the new instructions.
    """
    checklist = _format_checklist(blocks_completed)
    return f"[Transicion de bloque] Progreso actualizado:\n{checklist}\n\n{skill_prompt}"


def _format_store_context(ctx: dict) -> str:
    if not ctx:
        return "Sin contexto cargado."

    lines = [
        f"Tienda: {ctx.get('store_name', 'N/A')} ({ctx.get('store_id', 'N/A')})",
        f"Propietario: {ctx.get('owner_name', 'N/A')}",
        f"Ciudad: {ctx.get('city', 'N/A')}",
        f"Categoria: {ctx.get('category', 'N/A')}",
        f"Telefono: {ctx.get('phone', 'N/A')}",
        f"Email: {ctx.get('email', 'N/A')}",
        f"Onboarding: {ctx.get('onboarding_status', 'N/A')}",
        f"Soporte: {ctx.get('support_channel', 'N/A')}",
        f"Acceso RappiAliados: {'Si' if ctx.get('has_rappialiados_access') else 'No'}",
        f"Acceso Portal Partners: {'Si' if ctx.get('has_portal_partners_access') else 'No'}",
    ]

    if ctx.get("years_operating") is not None:
        lines.append(f"Anos operando: {ctx['years_operating']}")
    if ctx.get("schedule_open") and ctx.get("schedule_close"):
        lines.append(f"Horario: {ctx['schedule_open']} - {ctx['schedule_close']}")
    if ctx.get("payment_methods"):
        lines.append(f"Metodos pago: {', '.join(ctx['payment_methods'])}")
    if ctx.get("schedule_days"):
        lines.append(f"Dias operacion: {', '.join(ctx['schedule_days'])}")
    if ctx.get("commission_rate_pct") is not None:
        lines.append(f"Comision: {ctx['commission_rate_pct']}%")

    prev_sessions = ctx.get("previous_sessions", [])
    if prev_sessions:
        lines.append(f"Sesiones anteriores: {len(prev_sessions)}")
        for s in prev_sessions[:2]:
            lines.append(f"  - {s.get('started_at', '?')}: {s.get('summary', 'Sin resumen')[:80]}")

    return "\n".join(lines)


def _format_checklist(blocks_completed: dict[str, bool]) -> str:
    lines = []
    for block in BLOCK_ORDER:
        done = blocks_completed.get(block, False)
        marker = "[x]" if done else "[ ]"
        lines.append(f"{marker} {block}")

    completed = sum(1 for b in BLOCK_ORDER if blocks_completed.get(b, False))
    lines.append(f"Progreso: {completed}/{len(BLOCK_ORDER)}")
    return "\n".join(lines)
