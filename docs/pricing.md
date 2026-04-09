# Análisis de Costos — Handoff Agent

> Versión: Abril 2026 | Stack: Recall.ai + OpenAI GPT-5.4 + Whisper + Kokoro TTS
>
> Este documento cubre el desglose de costos por sesión, proyecciones de escala,
> optimizaciones implementadas y trade-offs de calidad vs costo.

---

## Tabla de Contenidos

1. [Mapa de Servicios con Costo](#1-mapa-de-servicios-con-costo)
2. [Tabla de Precios de Referencia](#2-tabla-de-precios-de-referencia)
3. [Modelo de Costo por Sesión](#3-modelo-de-costo-por-sesión)
4. [Proyecciones de Escala Mensual](#4-proyecciones-de-escala-mensual)
5. [Impacto del Prompt Caching](#5-impacto-del-prompt-caching)
6. [Optimizaciones Implementadas](#6-optimizaciones-implementadas)
7. [Configuraciones Alternativas — Trade-offs](#7-configuraciones-alternativas--trade-offs)
8. [Comparativa de Modelos LLM](#8-comparativa-de-modelos-llm)
9. [Recomendaciones por Etapa](#9-recomendaciones-por-etapa)
10. [Monitoreo de Costos](#10-monitoreo-de-costos)

---

## 1. Mapa de Servicios con Costo

```
┌─────────────────────────────────────────────────────────────────┐
│                    SESIÓN HANDOFF (30 min)                       │
│                                                                   │
│  Participante                                                     │
│  Google Meet ──► Recall.ai Bot ──► Agent WebSocket               │
│                  │  $0.50/hr       │                              │
│                  │                 ▼                              │
│                  │         ParticipantAudioBuffer                 │
│                  │         (VAD, PCM frames)                      │
│                  │                 │                              │
│                  │                 ▼                              │
│                  │          Whisper STT                           │
│                  │          $0.006/min ◄── COSTO #2               │
│                  │                 │                              │
│                  │                 ▼                              │
│                  │       LangGraph + Router LLM                   │
│                  │       GPT-5.4-mini $0.75/1M in ◄── COSTO #3   │
│                  │       GPT-5.4-nano $0.20/1M in (cheap tasks)  │
│                  │                 │                              │
│                  │        ┌────────┴────────┐                     │
│                  │        ▼                 ▼                     │
│                  │  Tool Calls         TTS Kokoro                 │
│                  │  (11 tools)         LOCAL = $0.00 ◄── FREE     │
│                  │  PostgreSQL         (o OpenAI TTS-1)           │
│                  │                          │                     │
│                  ◄──────────────────────────┘                     │
│               Audio Output (bot habla en Meet)                    │
│                                                                   │
│  DOMINANTE: Recall.ai = ~67% del costo total por sesión          │
└─────────────────────────────────────────────────────────────────┘
```

### Servicios activos y su rol

| Servicio | Rol | Tipo de costo | Controlable |
|---|---|---|---|
| **Recall.ai** | Bot Google Meet, audio separado por participante | Por hora de sesión | Reducible con sesiones más cortas |
| **OpenAI Whisper-1** | STT (audio usuario → texto) | Por minuto de audio | Reducible con VAD agresivo |
| **OpenAI GPT-5.4-mini** | Router LLM (todas las conversaciones + tool calls) | Por token | Reducible con caching y contexto corto |
| **OpenAI GPT-5.4-nano** | Resumen de sesión (cheap tasks) | Por token | Negligible |
| **Kokoro ONNX** | TTS local (texto → audio del agente) | $0.00 — local CPU | Ya optimizado |
| **LangFuse** | Observabilidad y tracing | Plan Free / $59 mes Pro | Opcional |
| **LocalStack Pro** | S3 + EventBridge en desarrollo | ~$35/mes plan Starter | Solo dev |
| **PostgreSQL** | Checkpointer + datos de sesión | Infraestructura propia | Costo fijo |

---

## 2. Tabla de Precios de Referencia

> Fuente: openai.com/api/pricing y recall.ai/pricing — Verificado Abril 2026

### OpenAI — Familia GPT-5.4 (modelos en uso)

| Modelo | Input | Input Cacheado | Output | Ventana | Lanzamiento |
|---|---|---|---|---|---|
| **gpt-5.4-nano** ⬅ cheap/main | $0.20 | $0.020 (-90%) | $1.25 | 400K tokens | 17 mar 2026 |
| **gpt-5.4-mini** ⬅ router | $0.75 | $0.075 (-90%) | $4.50 | 400K tokens | 17 mar 2026 |
| gpt-5.4 (completo) | $2.50 | $0.250 (-90%) | $15.00 | 1M tokens | 5 mar 2026 |
| gpt-5.4-pro | $30.00 | — | $180.00 | — | — |

> El prompt caching es **automático** para prefijos ≥ 1,024 tokens. **GPT-5.4 ofrece 90% de
> descuento en tokens cacheados** — la mejor tasa de toda la familia OpenAI.

### OpenAI — Referencia generaciones anteriores

| Modelo | Input | Input Cacheado | Output | Ventana |
|---|---|---|---|---|
| GPT-4.1-mini | $0.40 | $0.10 (-75%) | $1.60 | 1M tokens |
| GPT-4.1-nano | $0.10 | $0.025 (-75%) | $0.40 | 1M tokens |
| GPT-4o-mini | $0.15 | $0.075 (-50%) | $0.60 | 128K tokens |

### OpenAI — Audio (STT y TTS)

| Servicio | Modelo | Precio |
|---|---|---|
| **STT estándar** | whisper-1 | $0.006 / minuto ($0.36 / hora) |
| STT mejorado | gpt-4o-transcribe | $0.006 / minuto |
| STT económico | gpt-4o-mini-transcribe | **$0.003 / minuto** (50% más barato) |
| **TTS estándar** | tts-1 | $15.00 / 1M caracteres |
| TTS alta calidad | tts-1-hd | $30.00 / 1M caracteres |

### Recall.ai (por hora de sesión)

| Concepto | Precio | Notas |
|---|---|---|
| **Recording bot** | **$0.50 / hora** | Meeting Bot API (Pay-As-You-Go) |
| Transcripción propia | $0.15 / hora | No usada — se usa Whisper propio |
| Storage | Gratis 7 días | +$0.05/hora por cada 30 días adicionales |
| Free tier | 5 horas gratis | Límite 500h/mes, 2h/sesión |
| Output media / Screenshare | Sin cargo adicional publicado | Incluido en precio base |
| audio_separate_raw | Sin cargo adicional publicado | Feature incluida en precio base |

> **Nota sobre Recall.ai:** El plan Pay-As-You-Go es el más flexible para validación.
> Contactar sales para precios de volumen (>500 horas/mes).

---

## 3. Modelo de Costo por Sesión

### Parámetros base (sesión estándar 30 minutos)

| Parámetro | Valor | Fundamento |
|---|---|---|
| Duración | 30 min | Sesión típica de onboarding Handoff |
| Turnos de conversación | 25 | 8 bloques × ~3 turnos promedio |
| Audio del usuario | 12 min | ~40% del tiempo hablando |
| Tokens input por turno | ~1,000 | Sistema prompt (~600 tokens) + historial trimado (~400 tokens) |
| Tokens output por turno | ~300 | Respuesta del agente |
| Caracteres TTS del agente | ~9,000 chars | ~12 min de habla × 750 chars/min |
| Tool calls por sesión | ~20 | `mark_block_complete` × 8 + updates + get_context |

### Desglose de costos — Configuración actual (producción)

```
Stack: GPT-5.4-mini (Router) + GPT-5.4-nano (Cheap) + Kokoro TTS + Whisper-1
```

| Componente | Volumen | Tarifa | Costo | % del Total |
|---|---|---|---|---|
| Recall.ai Recording | 0.5 hr | $0.50/hr | **$0.250** | 66.5% |
| OpenAI Whisper-1 STT | 12 min | $0.006/min | **$0.072** | 19.1% |
| GPT-5.4-mini Router (input) | 25,000 tokens | $0.75/1M | $0.019 | 5.0% |
| GPT-5.4-mini Router (output) | 7,500 tokens | $4.50/1M | $0.034 | 9.0% |
| GPT-5.4-nano Cheap (resumen) | ~700 tokens total | $0.20-$1.25/1M | <$0.001 | ~0% |
| Kokoro TTS | 9,000 chars | **$0.00 (local)** | $0.000 | 0% |
| **TOTAL por sesión** | | | **$0.375** | 100% |

> **Nota:** Con GPT-5.4-mini el componente LLM sube a ~14% del total (vs ~6% con GPT-4.1-mini),
> pero Recall.ai sigue siendo el dominante con 66.5%.

### Escenarios de sesión

| Escenario | Duración | Turnos | Audio STT | Recall | STT | LLM | Total |
|---|---|---|---|---|---|---|---|
| **Corta** | 15 min | 12 | 6 min | $0.125 | $0.036 | $0.026 | **$0.187** |
| **Estándar** | 30 min | 25 | 12 min | $0.250 | $0.072 | $0.053 | **$0.375** |
| **Extendida** | 45 min | 35 | 18 min | $0.375 | $0.108 | $0.074 | **$0.557** |
| **Larga** | 60 min | 50 | 24 min | $0.500 | $0.144 | $0.106 | **$0.750** |

> **Insight clave:** Recall.ai domina el costo (~67%) y es lineal con la duración.
> Sesiones más cortas y enfocadas son el principal lever de optimización.

---

### Costo unitario por aliado incorporado

Asumiendo 2 sesiones por aliado (1 handoff principal + 1 seguimiento):

| Métrica | Valor |
|---|---|
| Costo por aliado incorporado (2 sesiones) | **$0.75** |
| Costo equivalente humano (2 sesiones × 30 min) | **~$3.50–$4.00** |
| Ahorro por aliado vs agente humano | **~$2.75–$3.25 (78–82%)** |
| Punto de equilibrio | Desde la primera sesión |

### Costo por sesión vs agente de ventas humano (Colombia)

Un agente de ventas/onboarding en Colombia tiene un costo empleador aproximado de:

| Concepto | Valor mensual (COP) | Valor mensual (USD) |
|---|---|---|
| Salario base promedio | ~$1,700,000 COP | ~$405 |
| Prestaciones sociales (46.5%) | ~$790,000 COP | ~$188 |
| **Costo total empleador** | **~$2,490,000 COP** | **~$593/mes** |

> *Tipo de cambio referencia: COP 4,200 / USD. Incluye salud (8.5%), pensión (12%),
> ARL (0.52-6.96%), caja de compensación (4%), SENA (2%), ICBF (3%), cesantías e intereses,
> prima de servicios y vacaciones proporcionales.*

Distribuyendo ese costo sobre una jornada efectiva de trabajo:

| Métrica | Humano | Agente IA (Stack A) | Diferencia |
|---|---|---|---|
| Costo mensual | **$593 fijo** | $375 variable (1,000 sesiones) | −37% a escala |
| Horas efectivas/mes | 154 hrs (22 días × 7 h) | Ilimitadas (24/7) | — |
| Costo por hora operativa | **$3.85/hora** | **$0.75/hora** (Stack A) | −80.5% |
| Costo por sesión 30 min | **$1.92/sesión** | **$0.375/sesión** | **−80.5%** |
| Sesiones simultáneas | **1** | **N (ilimitadas)** | — |
| Disponibilidad | Lun-Vie 8am–6pm | 24/7/365 | — |

---

## 5. Impacto del Prompt Caching

### Cómo funciona en este sistema

El sistema implementa una estrategia de 2 niveles para maximizar el hit rate de caching:

**Nivel 1 — Sistema Prompt (construido UNA sola vez, `src/agent/nodes.py:25-68`)**
```
[SystemMessage: Persona + Guardrails + StoreContext + Checklist + SkillPrompt]
  ~600-1,000 tokens — NUNCA se reconstruye en turnos posteriores
  → Candidato ideal para prompt caching de OpenAI (prefijo estable)
```

**Nivel 2 — Transiciones de bloque (`src/agent/prompts/system.py:45-56`)**
```
[SystemMessage ligero: Checklist actualizado + Nuevas instrucciones de skill]
  ~300-500 tokens — Solo se inyecta al completar un bloque (8 veces max)
  → Costo incremental por transición, no por turno
```

### Condición para que aplique el caching

OpenAI cachea automáticamente prefijos ≥ **1,024 tokens**. Con el sistema prompt actual:

| Componente | Tokens aprox. | Cumple ≥ 1024? |
|---|---|---|
| Persona (`persona.py`) | ~150 | — |
| Guardrails (`guardrails.py`) | ~100 | — |
| Store context (varía) | ~300-500 | — |
| Skill prompt (YAML) | ~300-500 | — |
| **Total sistema** | **~850-1,250 tokens** | ✅ Cuando store es rico en datos |

> **Recomendación:** Asegurar que el store context incluya suficiente información descriptiva
> para superar el umbral de 1,024 tokens y activar caching desde el turno #2.

### Ahorro por caching con GPT-5.4-mini en una sesión estándar

```
Sin caching (25 turnos × 600 tokens sistema × $0.75/1M):   $0.01125/sesión
Con caching (23 turnos × 600 tokens × $0.075/1M):           $0.00104/sesión
                                                            ──────────────────
Ahorro en tokens de sistema:                                ~$0.010 (90%)
Ahorro total sobre costo LLM/sesión:                        ~$0.010 / $0.053 = 19%
Ahorro mensual (1,000 sesiones):                            ~$10.00
```

> GPT-5.4 ofrece el **mejor descuento de caching de OpenAI (90%)**, superior al 75% de GPT-4.1
> y al 50% de GPT-4o. Esto hace que el impacto del caching sea mayor en el stack actual
> que en generaciones anteriores.

---

## 6. Optimizaciones Implementadas

### 6.1 TTS Local con Kokoro ONNX (`src/agent/voice/tts_kokoro.py`)

| Aspecto | Detalle |
|---|---|
| Costo | **$0.00** vs $0.000135 por sesión con OpenAI TTS-1 |
| Modelo | Kokoro-82M ONNX — español nativo, voz `ef_dora` |
| Hardware | CPU-only (ONNX Runtime, sin GPU requerida) |
| Calidad | Alta — comparable a TTS-1 en español colombiano |
| Warmup al startup | Evita cold-start de 2-5 s en la primera síntesis |
| Ahorro mensual (1,000 sesiones) | ~$0.14/mes — impacto monetario bajo, pero latencia 0 |

> **Decisión correcta:** TTS es tan barato en OpenAI ($15/1M chars ≈ $0.000135/sesión)
> que el ahorro real de Kokoro es la **latencia eliminada**, no el dinero.

### 6.2 Message Trimmer — Control del contexto (`src/agent/memory/trimmer.py`)

```python
TRIMMER = trim_messages(max_tokens=4000, strategy="last", token_counter=len)
```

| Aspecto | Detalle |
|---|---|
| Límite | 4,000 caracteres de historial (≈ 1,000 tokens reales) |
| Estrategia | `"last"` — mantiene los mensajes más recientes |
| Sistema | Siempre incluido (`include_system=True`) |
| Efecto en costo | Limita input tokens a ~1,000 por turno en sesiones largas |
| Riesgo | Pérdida de contexto temprano en sesiones > 45 min |

> **Advertencia técnica:** `token_counter=len` cuenta **caracteres**, no tokens reales.
> Para tiktoken (4 chars ≈ 1 token), el límite real es ~1,000 tokens OpenAI.
> Considera reemplazar con `tiktoken.encoding_for_model("gpt-4o")` para control preciso.
> Con GPT-5.4-mini a $0.75/1M, cada 1,000 tokens adicionales de contexto cuestan $0.00075 —
> relevante a escala alta.

### 6.3 Modelo económico para tareas no críticas (`src/agent/llm.py`)

| Rol | Modelo config.py | Temperatura | Max Tokens | Uso | Costo relativo |
|---|---|---|---|---|---|
| Router | `gpt-5.4-mini` | 0.7 | 2,048 | Todas las conversaciones, tool routing | baseline |
| Main | `gpt-5.4-nano` | 0.7 | 2,048 | Disponible para expansión futura | −73% |
| Cheap | `gpt-5.4-nano` | 0.3 | 1,000 | Solo resumen final de sesión | −73% |

El resumen con nano cuesta ~$0.00009 vs ~$0.00034 con mini → **ahorro del 73%** en esa tarea específica.

### 6.4 Sistema prompt construido UNA sola vez (`src/agent/nodes.py:25-68`)

```python
# load_context() — solo se ejecuta en el primer turno
if state.get("session_status") == "active" and state.get("blocks_completed"):
    return {}  # Skip — already initialized
```

- El sistema prompt completo (Persona + Guardrails + Store + Skill) se construye **una sola vez**
- Persiste vía checkpointer en PostgreSQL entre reconexiones
- **Con GPT-5.4-mini, eliminar 25 reconstrucciones a $0.75/1M ahorra ~$0.011/sesión** vs una implementación naive

### 6.5 Skill transitions ligeras vs rebuild completo

En vez de reconstruir el prompt completo al cambiar de bloque (8 veces/sesión):

```python
# Solo inyecta checklist actualizado + nuevo skill (~300 tokens vs ~600 del sistema completo)
skill_msg = SystemMessage(content=build_skill_update(next_block, skill.prompt, blocks))
```

**Ahorro por sesión:** 8 transiciones × 300 tokens × $0.75/1M = $0.0018 — pequeño pero indicativo de la filosofía de diseño.

### 6.6 Checkpointer PostgreSQL — Sin retokenización en reconexiones

El estado completo de la conversación persiste entre reconexiones WebSocket. Un usuario que pierde conexión y reconecta **no genera tokens adicionales** — el grafo retoma desde el checkpoint.

---

## 7. Configuraciones Alternativas — Trade-offs

### Stack A — Producción actual (balanceado)

```
Router: GPT-5.4-mini | TTS: Kokoro (local) | STT: Whisper-1
```

| | Costo/sesión | Calidad LLM | Latencia TTS | Costo infra |
|---|---|---|---|---|
| Costo | **$0.375** | ★★★★☆ | 0 ms (local) | $0 TTS |
| Ideal para | Producción inicial, calidad garantizada con modelo moderno | | | |

### Stack B — Máximo ahorro STT

```
Router: GPT-5.4-mini | TTS: Kokoro | STT: gpt-4o-mini-transcribe
```

| | Costo/sesión | Ahorro vs A | Trade-off |
|---|---|---|---|
| Recall.ai | $0.250 | — | — |
| STT | $0.036 | -$0.036 (-50%) | Menor precisión en acento colombiano |
| LLM | $0.053 | — | — |
| **Total** | **$0.339** | **-$0.036 (-9.6%)** | Riesgo de errores STT con terminología técnica |

> **Recomendación:** Probar `gpt-4o-mini-transcribe` con un batch de grabaciones reales.
> Si Word Error Rate < 5% en español colombiano, el ahorro de 9.6% vale la pena.

### Stack C — Calidad máxima (demo ejecutivo / cuentas VIP)

```
Router: GPT-5.4 (completo) | TTS: Kokoro | STT: Whisper-1
```

| | Costo/sesión | Ahorro vs A | Trade-off |
|---|---|---|---|
| Recall.ai | $0.250 | — | — |
| STT | $0.072 | — | — |
| LLM Router | $0.175 | +$0.122 (+230%) | Razonamiento superior, ventana 1M tokens |
| **Total** | **$0.497** | **+$0.122 (+33%)** | 3.3× más caro en LLM, calidad notablemente superior |

> **Uso:** Exclusivo para cuentas enterprise o cuando el agente maneja disputas y objeciones complejas.

### Stack D — Costo mínimo absoluto (volumen muy alto, aliados simples)

```
Router: GPT-5.4-nano | TTS: Kokoro | STT: gpt-4o-mini-transcribe
```

| | Costo/sesión | Ahorro vs A | Trade-off |
|---|---|---|---|
| Recall.ai | $0.250 | — | — |
| STT | $0.036 | -$0.036 | — |
| LLM | $0.014 | -$0.039 | Nano puede fallar en razonamiento de tool routing |
| **Total** | **$0.300** | **-$0.075 (-20%)** | Riesgo de loops, tool calls incorrectos |

> **Solo recomendado** si el flujo de 8 bloques está completamente validado y
> los tool calls son predecibles. Nano es capaz para respuestas textuales
> pero puede tener dificultades con el routing de tool calls complejos.

### Stack E — Sin Recall.ai (solo WebSocket directo)

```
Sin Recall.ai | Audio WebSocket directo desde cliente | Kokoro | Whisper-1
```

| | Costo/sesión | Ahorro vs A | Limitación |
|---|---|---|---|
| Recall.ai | $0.000 | -$0.250 (-67%) | Sin integración nativa Google Meet/Zoom |
| STT | $0.072 | — | El cliente debe capturar y enviar audio |
| LLM | $0.053 | — | — |
| **Total** | **$0.125** | **-$0.250 (-67%)** | Requiere app nativa o extensión Chrome |

> **Insight crítico:** Recall.ai representa el **67% del costo**. Si se puede reemplazar
> con una solución propia a largo plazo, el costo por sesión cae de $0.375 a $0.125.

### Comparativa de todos los stacks

```
Stack              Costo/sesión   100/mes    500/mes    1,000/mes
──────────────────────────────────────────────────────────────────
A (producción)       $0.375        $37.50    $187.50     $375.00
B (STT mini)         $0.339        $33.90    $169.50     $339.00
C (GPT-5.4 full)     $0.497        $49.70    $248.50     $497.00
D (costo mínimo)     $0.300        $30.00    $150.00     $300.00
E (sin Recall)       $0.125        $12.50     $62.50     $125.00
```

---

## 8. Comparativa de Modelos LLM

### Para el rol de Router (el más importante)

| Modelo | Input | Output | Context | Cache off | Cache on | Calidad | Recomendación |
|---|---|---|---|---|---|---|---|
| **gpt-5.4-nano** | $0.20 | $1.25 | 400K | $0.020 (-90%) | ★★★☆☆ | Stack D / cheap | |
| **gpt-5.4-mini** ✅ | $0.75 | $4.50 | 400K | $0.075 (-90%) | ★★★★☆ | **Producción actual** | |
| **gpt-5.4** | $2.50 | $15.00 | 1M | $0.250 (-90%) | ★★★★★ | VIP / disputas | |
| GPT-4.1-mini | $0.40 | $1.60 | 1M | $0.10 (-75%) | ★★★★☆ | Alternativa más barata | |
| GPT-4.1-nano | $0.10 | $0.40 | 1M | $0.025 (-75%) | ★★★☆☆ | Alternativa nano | |

### Costo LLM por sesión estándar (25 turnos, 25K input / 7.5K output tokens)

| Modelo | Input | Output | **Total/sesión** | vs. gpt-5.4-mini |
|---|---|---|---|---|
| GPT-4.1-nano | $0.0025 | $0.003 | **$0.006** | −89% |
| GPT-4.1-mini | $0.010 | $0.012 | **$0.022** | −58% |
| **gpt-5.4-nano** | $0.005 | $0.009 | **$0.014** | −74% |
| **gpt-5.4-mini** | $0.019 | $0.034 | **$0.053** | baseline |
| **gpt-5.4** | $0.063 | $0.113 | **$0.175** | +230% |

> **Contexto importante:** El LLM representa solo el **14% del costo total** con el stack actual.
> Cambiar de gpt-5.4-mini a gpt-5.4-nano ahorra $0.039/sesión = $39/1,000 sesiones.
> El beneficio de calidad del mini para tool routing complejos justifica el gasto adicional.

---

### Variables de entorno para cambiar stack sin rebuild

```bash
# Stack A — producción actual (defaults en config.py)
AGENT_ROUTER_MODEL=openai/gpt-5.4-mini
AGENT_MODEL=openai/gpt-5.4-nano
AGENT_CHEAP_MODEL=openai/gpt-5.4-nano
STT_MODEL=whisper-1

# Stack B — ahorro STT
STT_MODEL=openai/gpt-4o-mini-transcribe

# Stack D — costo mínimo
AGENT_ROUTER_MODEL=openai/gpt-5.4-nano
STT_MODEL=openai/gpt-4o-mini-transcribe

# Stack C — calidad VIP
AGENT_ROUTER_MODEL=openai/gpt-5.4

# Proveedor alternativo (Anthropic, sin cambio de código)
AGENT_ROUTER_MODEL=anthropic/claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-...
```

> LiteLLM + `drop_params=True` permite cambiar proveedor sin tocar código.

### Costo IA vs costo operativo humano equivalente

Comparativa directa: ¿cuánto costaría que un agente humano hiciera las mismas sesiones?

| Sesiones/mes | Costo IA (Stack A) | Costo humano equivalente | Ahorro operativo | Ahorro % |
|---|---|---|---|---|
| 100 | $37.50 | $192 (0.5 agentes) | $154.50 | 80.5% |
| 500 | $187.50 | $960 (2.5 agentes) | $772.50 | 80.5% |
| 1,000 | $375.00 | $1,920 (5 agentes) | $1,545 | 80.5% |
| 2,000 | $750.00 | $3,840 (10 agentes) | $3,090 | 80.5% |
| 5,000 | $1,875.00 | $9,600 (25 agentes) | $7,725 | 80.5% |

> *Costo humano calculado a $1.92/sesión (agente colombiano $593/mes, 154 h efectivas/mes).*
> *No incluye costos de gestión, capacitación, rotación ni errores humanos.*
> *El agente IA no tiene costo fijo — escala a cero con cero sesiones.*

---

## Resumen Ejecutivo

| Pregunta | Respuesta |
|---|---|
| Costo por sesión de 30 min | **~$0.375** |
| Componente dominante (67%) | Recall.ai ($0.250/sesión) |
| Segundo componente (19%) | Whisper STT ($0.072/sesión) |
| Tercer componente (14%) | GPT-5.4-mini LLM ($0.053/sesión) |
| Mayor oportunidad de ahorro | Reemplazar Recall.ai a largo plazo (-67%) |
| Ahorro a corto plazo más fácil | STT mini-transcribe (-9.6%) |
| TTS costo | **$0.00** — Kokoro local ya implementado |
| Ventaja de GPT-5.4 vs GPT-4.1 | 90% descuento en caching (vs 75%) |
| El LLM importa para el costo | Moderadamente — 14% del total |
| El LLM importa para la calidad | Sí — gpt-5.4-mini es el punto óptimo |
| Costo IA vs costo humano equivalente | **−80.5%** ($0.375 vs $1.92 por sesión) |
| Cuándo escalar a LLM premium | Solo para cuentas VIP o flujos de disputas |
| Próxima optimización recomendada | Medir WER con STT mini-transcribe en producción |

---
