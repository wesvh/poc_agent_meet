# Plan: Implementacion del Agente Handoff AI con LangGraph (Prioridad 1)

> **Estado**: Implementado — pendiente verificacion end-to-end
> **Ultima actualizacion**: 2026-04-08

## Progreso por paso

| Paso | Descripcion | Estado |
|------|-------------|--------|
| 1 | Modelo de datos y repos | Completado |
| 2 | Config y dependencias | Completado |
| 3 | LLM y observabilidad | Completado |
| 4 | Skills y prompts | Completado |
| 5 | MCP Server y tools | Completado |
| 6 | Grafo y nodos | Completado |
| 7 | Entry point y Docker | Completado |
| 8 | Verificacion | Pendiente (make up + test WebSocket) |

---

## Context

La reestructuracion hexagonal esta completada. El ETL pipeline funciona end-to-end. Ahora necesitamos implementar el agente conversacional voice-first que conduce las sesiones de Handoff con aliados de Rappi.

**Alineacion con AI Agentic Platform de Rappi**: Este agente sigue las practicas recomendadas del documento de arquitectura de plataforma — MCP para tools, LiteLLM como proxy LLM, Langfuse para observabilidad, skills pattern para instrucciones dinamicas, guardrails en multiples capas, y estructura preparada para A2A futuro.

Criterios de evaluacion:
- **Orquestacion del agente** (LangGraph StateGraph)
- **Uso de tools y conexion a PostgreSQL** (via MCP server local + ports/adapters)
- **Manejo de memoria** (corto y largo plazo)
- **Calidad de prompting** (persona, reglas, anti-alucinacion, skills dinamicos)
- **Eficiencia y optimizacion de costos**
- **Seguridad** (user_id injection programatica, guardrails)
- **Observabilidad** (Langfuse tracing end-to-end)

---

## Arquitectura del Grafo

### Diseno: Loop unico con checklist

En lugar de un nodo por bloque (rigido), usamos un **loop conversacional unico** donde el LLM decide que bloque cubrir segun un checklist en el estado. Esto permite conversaciones naturales donde el aliado puede saltar entre temas.

```
[START] → load_context → conversation_loop ⟲ → should_continue? → end_session → [END]
                              ↕
                          (tool calls via MCP)
```

- **load_context**: Carga datos del aliado desde PostgreSQL, inyecta al estado, carga skill del bloque activo
- **conversation_loop**: Nodo principal — el LLM conversa, usa tools MCP, marca bloques completados
- **should_continue**: Condicional — si todos los bloques estan completos O el aliado quiere terminar → end
- **end_session**: Genera resumen (LLM barato via LiteLLM), guarda transcript, actualiza estado

### HandoffState (TypedDict)

```python
class HandoffState(TypedDict):
    # Identificacion
    session_id: str
    store_id: str                # inyectado programaticamente, NUNCA del LLM
    meeting_id: str

    # Mensajes (LangGraph nativo)
    messages: Annotated[list[BaseMessage], add_messages]

    # Contexto del aliado (pre-cargado)
    store_context: dict          # nombre, ciudad, categoria, estado onboarding, etc.
    meeting_context: dict        # scheduled_at, meeting_link

    # Checklist de bloques (el LLM marca como completados)
    blocks_completed: dict       # {"saludo": bool, "verificacion": bool, ...}
    current_block: str           # bloque activo sugerido
    active_skill: str | None     # skill cargado dinamicamente para el bloque actual

    # Datos recopilados durante la sesion
    collected_data: dict         # info nueva del aliado capturada en conversacion
    issues_detected: list[str]   # problemas identificados
    commitments: list[str]       # compromisos acordados

    # Control
    session_status: str          # "active", "completed", "abandoned"
    turn_count: int
    last_tool_result: str | None
```

---

## Tools via MCP (alineado con Rappi Platform)

### Por que MCP

El documento de plataforma de Rappi establece **MCP como protocolo obligatorio** para tools. Aunque el agente es local (single-agent), estructurar los tools como MCP server permite:
- Reutilizacion por otros agentes futuros
- Consistencia con el ecosistema Rappi
- Tool definitions de alta calidad (schemas explicitos, descripciones claras)
- Preparacion para MCP Registry Gateway

### Implementacion: MCP Server local in-process

Usamos un MCP server local (in-process, STDIO transport) que expone los tools del Handoff. LangGraph consume los tools via `langchain-mcp-adapters` que convierte tools MCP en tools LangChain.

```python
# src/agent/mcp/server.py — MCP Server con tools del Handoff
from mcp.server import Server
from mcp.types import Tool

server = Server("handoff-tools")

@server.tool()
async def get_store_context(store_id: str) -> dict:
    """Retrieve complete ally context from PostgreSQL including store details,
    payment methods, schedule, and previous session summaries.

    Args:
        store_id: Unique store identifier (e.g., "STORE-001")

    Returns:
        dict with keys: name, city, category, onboarding_status, phone, email,
        payment_methods, schedule_days, previous_sessions
    """
    ...
```

### Factory pattern para inyeccion de repos

```python
# src/agent/mcp/factory.py
def create_mcp_server(store_repo, meeting_repo, session_repo) -> Server:
    """Crea el MCP server con repos inyectados (composition root pattern)."""
    server = Server("handoff-tools")
    # Registra tools con closures que capturan repos
    ...
    return server
```

### Lista de tools (schemas MCP de alta calidad)

Siguiendo las best practices del documento: nombres explicitos, descripciones claras, parametros tipados.

| # | Tool | Proposito | Repo/Dependencia |
|---|------|-----------|-----------------|
| 1 | `get_store_context` | Cargar datos completos del aliado | StoreRepository.get_by_id |
| 2 | `get_meeting_info` | Info de la reunion actual | MeetingRepository.get_pending_by_store_id |
| 3 | `update_onboarding_status` | Cambiar estado onboarding | StoreRepository.update_field |
| 4 | `update_store_info` | Actualizar datos del aliado | StoreRepository.update_field |
| 5 | `record_issue` | Registrar problema detectado | Estado interno (collected_data) |
| 6 | `record_commitment` | Registrar compromiso acordado | Estado interno |
| 7 | `mark_block_complete` | Marcar bloque del checklist | Estado interno (blocks_completed) |
| 8 | `get_session_summary` | Resumen parcial de la sesion | Estado interno |
| 9 | `save_session_transcript` | Persistir transcript completo | HandoffSessionRepository.save |
| 10 | `update_meeting_status` | Marcar reunion como completada | MeetingRepository.update_status |
| 11 | `schedule_followup` | Programar seguimiento | EventBridge Scheduler |
| 12 | `load_skill` | Cargar instrucciones de un bloque/skill | Skills storage (Langfuse o local) |

### Error handling en tools (MCP best practice)

Los tools retornan errores semanticos y accionables, NO errores HTTP crudos:

```python
# Mal:  {"error": "404"}
# Bien: {"error": true, "message": "Store not found with id STORE-999", "reason": "store_not_found"}
```

**Archivos**:
- `src/agent/mcp/__init__.py`
- `src/agent/mcp/server.py` — MCP server definition
- `src/agent/mcp/factory.py` — crea server con repos inyectados
- `src/agent/mcp/tools/store_tools.py` — tools 1-4
- `src/agent/mcp/tools/session_tools.py` — tools 5-9
- `src/agent/mcp/tools/meeting_tools.py` — tools 10-11
- `src/agent/mcp/tools/skill_tools.py` — tool 12

---

## Skills Pattern (alineado con Rappi Platform)

El documento recomienda **Skills** para instrucciones dinamicas por workflow, en lugar de un system prompt monolitico. Cada bloque del Handoff es un skill.

### Implementacion

Los skills se almacenan como archivos YAML/JSON locales (primera iteracion) con path para migrar a Langfuse Prompt Management:

```yaml
# src/agent/skills/verificacion.yaml
name: verificacion
description: "Verify ally identity and basic store information"
prompt: |
  BLOQUE: VERIFICACION DE IDENTIDAD
  Objetivo: Confirmar que estas hablando con el titular de la tienda.

  Pasos:
  1. Pregunta el nombre del contacto y validalo contra store_context.owner_name
  2. Confirma el nombre de la tienda
  3. Confirma la ciudad

  Cuando los 3 datos coincidan, usa mark_block_complete("verificacion").
  Si hay discrepancia, registrala con record_issue().
required_tools:
  - get_store_context
  - mark_block_complete
  - record_issue
```

El tool `load_skill` inyecta el prompt del skill activo en la conversacion. Esto mantiene el system prompt base pequeno y estable.

**Archivos**:
- `src/agent/skills/` — directorio con skills YAML
- `src/agent/skills/loader.py` — carga y parsea skills

### Los 8 bloques/skills del Handoff

1. **saludo** — Presentarse, confirmar identidad del aliado
2. **verificacion** — Confirmar datos basicos (nombre tienda, ciudad, categoria)
3. **diagnostico** — Identificar problemas actuales del aliado
4. **configuracion** — Revisar/ajustar configuracion de la tienda en plataforma
5. **capacitacion** — Explicar funcionalidades clave de Rappi
6. **resolucion** — Resolver problemas identificados en diagnostico
7. **compromiso** — Acordar compromisos y proximos pasos
8. **cierre** — Resumir sesion, despedirse, programar seguimiento si aplica

---

## Prompting

### Estructura del system prompt (base estable + skill dinamico)

```
[PERSONA] Eres Alia, agente de Handoff de Rappi para aliados...
[REGLAS] Reglas de conversacion (idioma, tono, limites)
[ANTI-ALUCINACION] Solo usa datos de tools, nunca inventes datos del aliado
[GUARDRAILS] Restricciones de seguridad (no modificar datos sin confirmacion, etc.)
[CONTEXTO ALIADO] {store_context} — inyectado dinamicamente desde load_context
[CHECKLIST] Estado actual: {blocks_completed}
[SKILL ACTIVO] {active_skill.prompt} — instrucciones del bloque actual (cargado dinamicamente)
```

El system prompt base es **pequeno y estable**. Las instrucciones por bloque se cargan via skills.

**Archivos**:
- `src/agent/prompts/__init__.py`
- `src/agent/prompts/system.py` — build_system_prompt(store_context, blocks_completed, active_skill)
- `src/agent/prompts/persona.py` — PERSONA_PROMPT constante
- `src/agent/prompts/guardrails.py` — GUARDRAILS_PROMPT constante

---

## Guardrails (3 capas — alineado con Rappi Platform)

El documento recomienda guardrails en 3 niveles:

### Capa 1: System prompt (no deterministico)
- Anti-alucinacion: "Solo usa datos obtenidos via tools"
- Limites de scope: "No des consejos financieros ni legales"
- Tono: "Siempre amable, profesional, en espanol colombiano"

### Capa 2: Runtime del agente (deterministico)
```python
# src/agent/guardrails.py
def validate_tool_call(tool_name: str, args: dict, state: HandoffState) -> str | None:
    """Retorna error message si el tool call viola una regla, None si OK."""
    # Regla: no permitir update_onboarding_status sin verificacion completada
    if tool_name == "update_onboarding_status" and not state["blocks_completed"].get("verificacion"):
        return "Cannot update onboarding status before identity verification is complete"
    # Regla: store_id debe coincidir con el de la sesion (prevenir injection)
    if "store_id" in args and args["store_id"] != state["store_id"]:
        return "store_id mismatch — tool call blocked for security"
    return None
```

### Capa 3: LLM Proxy (LiteLLM)
- Rate limiting por sesion
- Filtro de PII en responses (configurar en LiteLLM guardrails)
- Max tokens por request

**Archivos**:
- `src/agent/guardrails.py` — validacion runtime de tool calls

---

## Seguridad (alineado con Rappi Platform)

### Principio: user_id/store_id injection programatica

El documento es explicito: **el LLM NUNCA debe resolver identidad**. El store_id se inyecta programaticamente en el entry point.

```python
# src/agent/server.py
@app.websocket("/ws/handoff/{store_id}")
async def handoff_session(websocket: WebSocket, store_id: str):
    # store_id viene de la URL (autenticado por el dispatcher/gateway)
    # Se inyecta en el estado — el LLM no puede modificarlo
    state = {"store_id": store_id, ...}
    # Los tools reciben store_id del estado, NO del LLM
```

### Tool parameter hiding

Los tools que operan sobre el aliado actual reciben `store_id` del estado de la sesion, NO como parametro que el LLM pueda manipular:

```python
@server.tool()
async def update_onboarding_status(new_status: str) -> dict:
    # store_id se inyecta desde el estado, no es parametro visible al LLM
    store_id = _get_session_store_id()  # del contexto de ejecucion
    ...
```

---

## LiteLLM: Capa de abstraccion multi-modelo

El agente usa **LiteLLM** via `langchain-litellm` como proxy LLM. Alineado con la recomendacion de plataforma de centralizar acceso a modelos.

```python
# src/agent/llm.py
from langchain_litellm import ChatLiteLLM
from src.config import Config

def get_main_llm() -> ChatLiteLLM:
    """LLM principal para conversacion (modelo potente)."""
    return ChatLiteLLM(
        model=Config.AGENT_MODEL,           # e.g. "anthropic/claude-sonnet-4-20250514"
        temperature=Config.AGENT_TEMPERATURE,
        max_tokens=Config.AGENT_MAX_TOKENS,
    )

def get_cheap_llm() -> ChatLiteLLM:
    """LLM barato para resumenes y clasificacion."""
    return ChatLiteLLM(
        model=Config.AGENT_CHEAP_MODEL,     # e.g. "anthropic/claude-haiku-4-5-20251001"
        temperature=0.2,
        max_tokens=1000,
    )
```

### Variables de entorno nuevas en Config

```python
AGENT_MODEL: str = os.getenv("AGENT_MODEL", "anthropic/claude-sonnet-4-20250514")
AGENT_CHEAP_MODEL: str = os.getenv("AGENT_CHEAP_MODEL", "anthropic/claude-haiku-4-5-20251001")
AGENT_TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.7"))
AGENT_MAX_TOKENS: int = _int_env("AGENT_MAX_TOKENS", 2048)
LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
```

---

## Langfuse: Observabilidad (alineado con Rappi Platform)

El documento establece Langfuse como **plataforma default de tracing**. Integramos como callback de LangChain para tracing automatico:

- Cada invocacion del LLM (tokens, latencia, costo)
- Tool calls y sus resultados
- Sesiones completas (agrupadas por session_id y store_id)
- Prompt versions (para prompt management futuro)

```python
# src/agent/observability.py
from langfuse.callback import CallbackHandler as LangfuseHandler
from src.config import Config

def get_langfuse_handler(session_id: str, store_id: str) -> LangfuseHandler | None:
    if not Config.LANGFUSE_PUBLIC_KEY:
        return None
    return LangfuseHandler(
        public_key=Config.LANGFUSE_PUBLIC_KEY,
        secret_key=Config.LANGFUSE_SECRET_KEY,
        host=Config.LANGFUSE_HOST,
        session_id=session_id,
        metadata={"store_id": store_id},
    )
```

Se pasa como callback al invocar el grafo: `graph.ainvoke(state, config={"callbacks": [langfuse_handler]})`

---

## Memoria

### Corto plazo (dentro de la sesion)
- **messages**: Lista nativa de LangGraph con `add_messages` reducer
- **Message trimming**: Mantener ultimos N mensajes + system prompt. `trim_messages(max_tokens=4000, strategy="last", include_system=True)`
- **Checkpointer**: `AsyncPostgresSaver` de `langgraph-checkpoint-postgres` — persiste estado completo entre turns, permite reconectar sesiones interrumpidas

### Largo plazo (entre sesiones)
- **handoff_sessions** table: Almacena transcript, resumen, issues, commitments por sesion
- **Consulta de historial**: Tool `get_store_context` incluye resumen de sesiones anteriores del aliado
- **Resumen al cerrar**: Al finalizar sesion, se genera un resumen estructurado (LLM barato via LiteLLM) y se guarda en `handoff_sessions.summary`

### Configuracion de checkpointer

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def get_checkpointer():
    return AsyncPostgresSaver.from_conn_string(Config.DATABASE_URL)
```

---

## Nuevos Ports y Repositories

### Extender StoreRepository (src/core/ports/repositories.py)

```python
class StoreRepository(Protocol):
    # ... metodos existentes del ETL ...
    async def get_by_id(self, store_id: str) -> dict | None: ...
    async def update_field(self, store_id: str, field: str, value: Any) -> None: ...
```

### Nuevo: HandoffSessionRepository

```python
class HandoffSessionRepository(Protocol):
    async def create(self, session_id: str, store_id: str, meeting_id: str) -> None: ...
    async def save_transcript(self, session_id: str, messages: list[dict]) -> None: ...
    async def save_summary(self, session_id: str, summary: dict) -> None: ...
    async def update_status(self, session_id: str, status: str) -> None: ...
    async def get_by_store(self, store_id: str, limit: int = 5) -> list[dict]: ...
```

### Extender MeetingRepository

```python
class MeetingRepository(Protocol):
    # ... metodos existentes ...
    async def get_pending_by_store_id(self, store_id: str) -> dict | None: ...
    async def update_status(self, meeting_id: str, status: str) -> None: ...
```

---

## Modelo de datos nuevo

### Tabla handoff_sessions (DDL)

```sql
CREATE TABLE handoff_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id TEXT NOT NULL REFERENCES stores(store_id),
    meeting_id UUID REFERENCES meetings(id),
    status TEXT NOT NULL DEFAULT 'active',  -- active, completed, abandoned
    blocks_completed JSONB NOT NULL DEFAULT '{}',
    collected_data JSONB NOT NULL DEFAULT '{}',
    issues_detected JSONB NOT NULL DEFAULT '[]',
    commitments JSONB NOT NULL DEFAULT '[]',
    transcript JSONB,           -- mensajes completos
    summary TEXT,               -- resumen generado por LLM
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    turn_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_sessions_store ON handoff_sessions(store_id);
CREATE INDEX idx_sessions_status ON handoff_sessions(status);
```

### ORM: HandoffSession (src/infrastructure/db/orm.py)

Agregar modelo SQLAlchemy correspondiente a la tabla.

---

## Entry Point: FastAPI WebSocket

```python
# src/agent/server.py — COMPOSITION ROOT del agente
from fastapi import FastAPI, WebSocket

app = FastAPI(title="Handoff Agent")

@app.websocket("/ws/handoff/{store_id}")
async def handoff_session(websocket: WebSocket, store_id: str):
    # 1. Accept connection
    # 2. store_id se toma de URL (autenticado upstream) — NUNCA del LLM
    # 3. Inject repos (composition root): SqlAlchemy*Repo()
    # 4. Create MCP server con repos inyectados
    # 5. Create Langfuse handler para tracing
    # 6. Run graph loop: receive message → invoke graph → send response
    # 7. On disconnect: save state via checkpointer
```

**Archivo**: `src/agent/server.py`

---

## Optimizacion de costos

1. **Pre-carga de contexto**: Cargar datos del aliado UNA vez en `load_context`, no en cada turn
2. **Message trimming**: Limitar ventana de mensajes a ~4000 tokens
3. **Prompt caching**: System prompt base estable → proveedor lo cachea automaticamente
4. **Skills dinamicos**: Solo el skill del bloque activo esta en contexto, no los 8 bloques
5. **Dual-model via LiteLLM**: Modelo principal para conversacion, modelo barato para resumenes
6. **Tool results concisos**: Tools retornan solo datos necesarios, no dumps completos
7. **Observabilidad con Langfuse**: Monitorear costos por sesion y optimizar iterativamente

---

## Estructura de archivos nuevos

```
src/agent/
  __init__.py
  server.py              # FastAPI app + WebSocket endpoint (composition root)
  graph.py               # build_graph() → StateGraph compilado
  state.py               # HandoffState TypedDict
  nodes.py               # load_context, conversation_turn, end_session
  routing.py             # should_continue (condicional del grafo)
  llm.py                 # get_main_llm(), get_cheap_llm() via LiteLLM
  observability.py       # get_langfuse_handler() para tracing
  guardrails.py          # validate_tool_call() — runtime guardrails
  mcp/
    __init__.py
    server.py            # MCP Server definition
    factory.py           # create_mcp_server(repos...) → Server
    tools/
      __init__.py
      store_tools.py     # get_store_context, update_store_info, update_onboarding_status
      session_tools.py   # record_issue, record_commitment, mark_block_complete, etc.
      meeting_tools.py   # update_meeting_status, schedule_followup
      skill_tools.py     # load_skill
  skills/
    loader.py            # carga skills desde YAML
    saludo.yaml
    verificacion.yaml
    diagnostico.yaml
    configuracion.yaml
    capacitacion.yaml
    resolucion.yaml
    compromiso.yaml
    cierre.yaml
  prompts/
    __init__.py
    system.py            # build_system_prompt()
    persona.py           # PERSONA_PROMPT
    guardrails.py        # GUARDRAILS_PROMPT (capa 1 — prompt-level)
  memory/
    __init__.py
    checkpointer.py      # get_checkpointer() → AsyncPostgresSaver
    trimmer.py           # configuracion de message trimming
```

## Archivos modificados

- `src/core/ports/repositories.py` — agregar get_by_id, update_field, HandoffSessionRepository
- `src/infrastructure/db/orm.py` — agregar HandoffSession model
- `src/infrastructure/db/repositories.py` — agregar SqlAlchemyHandoffSessionRepo + metodos nuevos
- `docker/postgres/init/02_schema.sql` — agregar tabla handoff_sessions
- `docker-compose.yml` — agregar servicio handoff-agent
- `src/config.py` — agregar variables AGENT_MODEL, LANGFUSE_*, etc.
- `.env.example` — agregar nuevas variables

## Archivos de infraestructura Docker

- `docker/agent/Dockerfile` — imagen del agente
- `requirements-agent.txt` — dependencias del agente:

```
litellm>=1.82.3
langchain>=1.2.13
langchain-core>=1.2.22
langchain-community>=0.4.1
langchain-litellm>=0.6.2
langgraph>=1.1.3
langgraph-checkpoint-postgres>=2.0.0
mcp>=1.0.0
langchain-mcp-adapters>=0.1.0
# observabilidad
langfuse>=4.0.1
```

---

## Pasos de implementacion

### Paso 1: Modelo de datos y repos
1. Agregar DDL `handoff_sessions` a `02_schema.sql`
2. Agregar `HandoffSession` ORM model a `orm.py`
3. Extender ports en `repositories.py` (get_by_id, update_field, HandoffSessionRepository)
4. Implementar `SqlAlchemyHandoffSessionRepo` + metodos nuevos en repos existentes

### Paso 2: Config y dependencias
1. Crear `requirements-agent.txt`
2. Agregar variables de entorno a `src/config.py` y `.env.example`
3. Crear `docker/agent/Dockerfile`

### Paso 3: LLM y observabilidad
1. Crear `src/agent/llm.py` — LiteLLM wrappers
2. Crear `src/agent/observability.py` — Langfuse handler

### Paso 4: Skills y prompts
1. Crear `src/agent/skills/*.yaml` — 8 skills del Handoff
2. Crear `src/agent/skills/loader.py`
3. Crear `src/agent/prompts/persona.py`, `guardrails.py`, `system.py`

### Paso 5: MCP Server y tools
1. Crear `src/agent/mcp/tools/store_tools.py`
2. Crear `src/agent/mcp/tools/session_tools.py`
3. Crear `src/agent/mcp/tools/meeting_tools.py`
4. Crear `src/agent/mcp/tools/skill_tools.py`
5. Crear `src/agent/mcp/server.py` y `factory.py`

### Paso 6: Grafo y nodos
1. Crear `src/agent/state.py` — HandoffState
2. Crear `src/agent/guardrails.py` — runtime validation
3. Crear `src/agent/nodes.py` — load_context, conversation_turn, end_session
4. Crear `src/agent/routing.py` — should_continue
5. Crear `src/agent/memory/checkpointer.py` y `trimmer.py`
6. Crear `src/agent/graph.py` — build_graph()

### Paso 7: Entry point y Docker
1. Crear `src/agent/server.py` — FastAPI + WebSocket (composition root)
2. Agregar servicio a `docker-compose.yml`

### Paso 8: Verificacion
1. `python -c "from src.agent.graph import build_graph; print('OK')"` — grafo compila
2. `python -c "from src.agent.mcp.factory import create_mcp_server; print('OK')"` — MCP OK
3. `make up` — todos los servicios levantan
4. Conectar via WebSocket a `ws://localhost:8002/ws/handoff/{store_id}` y verificar:
   - El agente saluda y conoce datos del aliado (pre-carga via tool)
   - Los tools MCP funcionan (consulta/actualiza PostgreSQL)
   - Skills se cargan dinamicamente al cambiar de bloque
   - Guardrails bloquean tool calls no autorizados
   - La sesion se persiste (reconectar mantiene contexto)
   - Langfuse muestra traces de la sesion
   - Al completar todos los bloques, la sesion cierra y genera resumen

---

## Verificacion (criterios de evaluacion)

| Criterio | Como se cumple |
|----------|---------------|
| Orquestacion del agente | StateGraph con loop unico + checklist routing, reconexion via checkpointer |
| Uso de tools y conexion a PostgreSQL | 12 tools via MCP server + factory pattern, repos inyectados, zero imports de infra |
| Manejo de memoria | Corto plazo: messages + trimming + checkpointer. Largo plazo: handoff_sessions |
| Calidad de prompting | Persona + guardrails + anti-alucinacion + skills dinamicos por bloque |
| Eficiencia | Pre-carga contexto, skills dinamicos, message trimming, dual-model via LiteLLM |
| Multi-modelo | LiteLLM como abstraccion — cambiar proveedor sin tocar codigo |
| Observabilidad | Langfuse tracing: tokens, latencia, costo por sesion, agrupacion por store_id |
| Seguridad | store_id injection programatica, runtime guardrails, tool parameter hiding |
| MCP compliance | Tools expuestos via MCP server, schemas de alta calidad, errores semanticos |
| Skills pattern | Instrucciones por bloque cargadas dinamicamente, system prompt base estable |
| Preparacion A2A | Estructura modular lista para exponer agent via A2A en futuro |
