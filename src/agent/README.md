# Agent — Handoff AI

Módulo del agente conversacional voice-first para sesiones de Handoff con aliados.

## Estructura prevista

```
agent/
  graph.py           # LangGraph StateGraph — define el flujo de la conversación
  state.py           # TypedDict con el estado del agente (HandoffState)
  prompts/
    system.py        # System prompt base
    handoff_flow.py  # Prompts por bloque del flujo (inicio, diagnóstico, cierre…)
  tools/
    __init__.py
    store_tools.py   # Tools: get_store_context, update_onboarding_status
    meeting_tools.py # Tools: get_meeting_info, update_meeting_status
    session_tools.py # Tools: save_session_transcript, record_outcome
  voice/
    stt.py           # Adaptador STT (Speech-to-Text)
    tts.py           # Adaptador TTS (Text-to-Speech)
```

## Reglas de arquitectura

- `graph.py` y `tools/` solo importan de `src.core.ports` — nunca de `src.infrastructure` directamente.
- La inyección de repos concretos se hace en el entry point (`agent/server.py` o similar).
- El estado (`HandoffState`) es un TypedDict puro, sin dependencias externas.

## Dependencias a agregar (requirements)

```
langgraph>=0.2
langchain-core>=0.3
langchain-anthropic>=0.3   # o langchain-openai según el LLM elegido
```

## Ejemplo de tool usando el port de repositorio

```python
# agent/tools/store_tools.py
from src.core.ports.repositories import StoreRepository

async def get_store_context(store_id: str, repo: StoreRepository) -> dict:
    \"\"\"Carga el contexto del aliado desde PostgreSQL para inyectar al agente.\"\"\"
    # repo es inyectado al iniciar la sesión — el tool no conoce SQLAlchemy
    ...
```
