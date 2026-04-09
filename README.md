# Rappi Handoff — Plataforma de Onboarding con Agente de IA

Sistema completo de onboarding para aliados de Rappi. Ingesta un CSV de aliados, normaliza y persiste los datos, programa reuniones automáticas en Google Meet y ejecuta sesiones de acompañamiento conducidas por un agente conversacional de IA con voz, visión compartida y razonamiento estructurado.

---

## Tabla de contenidos

1. [Arquitectura general](#1-arquitectura-general)
2. [Pipeline ETL](#2-pipeline-etl)
3. [Base de datos](#3-base-de-datos)
4. [Programación automática de reuniones](#4-programación-automática-de-reuniones)
5. [Agente de IA](#5-agente-de-ia)
6. [Voz: STT y TTS](#6-voz-stt-y-tts)
7. [Integración Recall.ai](#7-integración-recallai)
8. [Frontend de screenshare](#8-frontend-de-screenshare)
9. [Túneles Cloudflare](#9-túneles-cloudflare)
10. [Servicios externos y API keys](#10-servicios-externos-y-api-keys)
11. [Requisitos de la máquina](#11-requisitos-de-la-máquina)
12. [Configuración inicial](#12-configuración-inicial)
13. [Comandos de referencia](#13-comandos-de-referencia)
14. [Puertos locales](#14-puertos-locales)

---

## 1. Arquitectura general

```
CSV upload
    │
    ▼
Ingest API (FastAPI :8001)
    │  POST /upload → S3 raw bucket (LocalStack)
    ▼
EventBridge Rule (S3 ObjectCreated → Airflow REST)
    │
    ▼
Airflow DAG: etl_stores_csv
    ├─ archive_raw_to_s3      → copia a bucket archive, calcula hash
    ├─ load_staging           → filas raw como JSONB en stg_stores_raw
    ├─ transform_and_load     → normaliza, valida, upsert en stores / meetings
    └─ schedule_meetings      → crea schedules one-shot en EventBridge Scheduler
                                 (5 min antes de scheduled_at por cada meeting)
                                          │
                                          ▼
                              EventBridge Scheduler dispara MeetingDue
                                          │
                                          ▼
                              Agent API (FastAPI :8002)
                                  │  carga contexto del aliado desde PostgreSQL
                                  │  crea bot de Recall.ai en la reunión de Meet
                                  ▼
                              Agente conversacional (LangGraph)
                                  ├─ LLM: GPT-5.4-mini (orquestador)
                                  ├─ LLM: GPT-5.4-nano  (respuesta final / tareas)
                                  ├─ TTS: Kokoro-82M ONNX (voz española local)
                                  ├─ STT: Whisper-1 vía OpenAI API
                                  └─ Skills: saludo → verificacion → diagnostico →
                                             configuracion → capacitacion →
                                             resolucion → compromiso → cierre
                                          │
                    ┌─────────────────────┴──────────────────────┐
                    ▼                                            ▼
          Recall.ai bot en Meet                     Frontend SPA (screenshare)
          ├─ audio → aliado (TTS)                  controlado por WebSocket
          ├─ escucha al aliado (STT)               desde el agente
          └─ screenshare → Frontend SPA
```

---

## 2. Pipeline ETL

### Trigger

El ETL se dispara de dos formas:

| Método | Descripción |
|--------|-------------|
| **Automático** | `POST /upload` en Ingest API sube el CSV a S3. EventBridge detecta el `ObjectCreated` y llama a la API REST de Airflow para iniciar el DAG. |
| **Manual** | `make trigger-etl` sube `data/aliados_dataset.csv` directamente. |

### Pasos del DAG (`etl_stores_csv`)

```
archive_raw_to_s3
    │  Lee el objeto S3 raw, calcula SHA-256, lo copia al bucket archive.
    │  Registra la ejecución en etl_runs (estado, hash, ruta).
    ▼
load_staging
    │  Inserta cada fila del CSV como JSONB en stg_stores_raw.
    │  FK a etl_runs para trazabilidad.
    ▼
transform_and_load
    │  Normaliza campo por campo (teléfono E.164, años operando, horarios,
    │  métodos de pago, ciudad, estado de onboarding).
    │  Valida reglas de negocio y persiste errores en etl_errors.
    │  Upsert en stores y meetings por store_id.
    ▼
schedule_meetings
    │  Para cada meeting con scheduled_at y status=pending,
    │  crea un schedule one-shot en EventBridge Scheduler.
    │  El schedule dispara un evento MeetingDue 5 min antes de la reunión.
```

### Normalización clave

| Campo | Transformación |
|-------|----------------|
| `phone` | E.164 Colombia (`+57XXXXXXXXXX`), descartado si no coincide |
| `years_operating` | texto libre → float ("6 meses" → 0.5, "4 años y medio" → 4.5) |
| `schedule_days` | split por `;`, normaliza acentos, ordena lunes→domingo |
| `payment_methods` | catálogo cerrado: efectivo, tarjeta, nequi, daviplata, pse |
| `city` | catálogo cerrado normalizado sin acentos |
| `scheduled_at` | `meeting_date` + `meeting_time` con timezone `America/Bogota` |

### EventBridge: dos roles distintos

```
EventBridge Rules     → disparo inmediato del ETL cuando llega un CSV al bucket raw
EventBridge Scheduler → programación temporal de sesiones del agente (one-shot por meeting)
```

> **Limitación local:** LocalStack emula la creación de schedules (`create_schedule`) pero no ejecuta automáticamente el target cuando llega la hora. En AWS real el disparo funciona end-to-end.

---

## 3. Base de datos

**Motor:** PostgreSQL 16
**Base de datos de la app:** `rappi_handoff`
**Usuario:** `app / app123`

### Tablas

| Tabla | Descripción |
|-------|-------------|
| `etl_runs` | Registro de cada ejecución ETL (estado, conteos, hash SHA-256 del archivo) |
| `etl_errors` | Errores de validación por fila/campo, FK a `etl_runs` |
| `stg_stores_raw` | Filas crudas del CSV como JSONB, FK a `etl_runs` |
| `stores` | Tabla curada. PK `store_id` (text). Upsert por conflicto. |
| `store_payment_methods` | Tabla N:M normalizada de métodos de pago por tienda |
| `store_schedule_days` | Días de operación normalizados (lunes…domingo) |
| `meetings` | Reuniones programadas por tienda, FK a `stores` |

### Credenciales locales

| Servicio | URL | Usuario | Password |
|----------|-----|---------|---------|
| PostgreSQL (app) | `localhost:5432` | `app` | `app123` |
| PostgreSQL (airflow) | `localhost:5432` | `airflow` | `airflow123` |
| Adminer UI | `http://localhost:8081` | `postgres` | `postgres123` |

> Adminer solo disponible con `docker compose --profile debug up -d adminer`

---

## 4. Programación automática de reuniones

El ETL persiste en `meetings` la fecha, hora y link de Google Meet de cada aliado. El último paso del DAG (`schedule_meetings`) crea un schedule one-shot en EventBridge Scheduler para cada meeting con `status = 'pending'` y `scheduled_at` válido.

```
meetings.scheduled_at = "2026-04-10T10:00:00-05:00"
    │
    ▼
EventBridge Scheduler: dispara a las 09:55 (MEETING_LEAD_MINUTES = 5)
    │  Evento: source="rappi.handoff.meeting", detail-type="MeetingDue"
    │  Payload: { store_id, meeting_id, meeting_link }
    ▼
Agent API → inicia sesión Handoff para ese store_id
```

---

## 5. Agente de IA

### Motor

El agente usa **LangGraph** como orquestador de flujo conversacional con memoria persistente vía checkpointer en PostgreSQL.

### Modelos LLM

| Rol | Modelo | Función |
|-----|--------|---------|
| **Router** | `gpt-5.4-mini` | Decide qué tools invocar y qué bloque activar. Mayor capacidad de razonamiento. |
| **Main / Workers** | `gpt-5.4-nano` | Genera respuestas de texto al aliado y ejecuta tareas atómicas (resúmenes, clasificación). |

Todos los modelos se sirven vía **LiteLLM**, lo que permite cambiar de proveedor editando solo las variables de entorno.

### Razonamiento por bloques (Skills)

El agente sigue un flujo de 8 bloques en orden. Cada bloque tiene un prompt especializado (`.yaml`) con instrucciones, firmas de tools y condición de salida:

```
saludo → verificacion → diagnostico → configuracion →
capacitacion → resolucion → compromiso → cierre
```

El agente transiciona entre bloques llamando `mark_block_complete(block_name)`. El siguiente bloque se inyecta como un `SystemMessage` ligero, sin reconstruir el prompt completo (optimización de tokens y prompt caching).

### Tools disponibles

| Grupo | Tools |
|-------|-------|
| `store_tools` | `get_store_context`, `get_meeting_info`, `update_store_info`, `update_onboarding_status` |
| `session_tools` | `record_issue`, `record_commitment`, `mark_block_complete`, `get_session_summary`, `save_session_transcript` |
| `meeting_tools` | `update_meeting_status`, `schedule_followup` |

### Observabilidad

Las trazas de LLM se envían a **Langfuse** (cloud) para monitoreo de latencia, tokens y flujos de conversación.

---

## 6. Voz: STT y TTS

### STT — Speech to Text

El audio del aliado llega desde Recall.ai como chunks PCM separados por participante (`audio_separate_raw`). Esos chunks se acumulan con VAD (Voice Activity Detection) y se transcriben con **Whisper-1** vía OpenAI API.

```
Recall.ai → WebSocket /recall/ws/{session_id} → VAD buffer → Whisper-1 → texto → LangGraph
```

### TTS — Text to Speech

El texto generado por el LLM se sintetiza con uno de estos backends (configurable por env):

| Backend | Variable | Descripción |
|---------|----------|-------------|
| **Kokoro** (default) | `TTS_BACKEND=kokoro` | Modelo ONNX local `kokoro-82M`. Voz `ef_dora` (español, femenino). Sin latencia de red, ~310 MB de modelo en disco. Se descarga automáticamente al construir el contenedor. |
| **OpenAI TTS** | `TTS_BACKEND=openai` | `tts-1` vía LiteLLM. Requiere `OPENAI_API_KEY`. |
| **Edge TTS** | `TTS_BACKEND=edge` | Microsoft Edge TTS, gratuito. Voz configurable (`es-CO-SalomeNeural`). |

El audio sintetizado se envía en streaming de vuelta a la página de output de Recall.ai:

```
LLM tokens → SentenceBuffer → TTS.synthesize_stream() → WebSocket /recall/output-ws/ → Web Audio API
```

---

## 7. Integración Recall.ai

**Recall.ai** es el servicio que crea un bot de IA capaz de unirse a videollamadas de Google Meet, Zoom y Teams. El bot recibe y envía audio, y puede compartir pantalla.

### Flujo de creación del bot

```
POST /recall/bots  { meeting_url, store_id }
    │
    ▼
Recall.ai API → bot creado → se une a la reunión de Meet
    │
    ├─ audio del aliado → wss://<PUBLIC_BASE_URL>/recall/ws/{session_id}
    │    (chunks PCM por participante, separados)
    │
    ├─ output audio (TTS) ← wss://<PUBLIC_BASE_URL>/recall/output-ws/{session_id}
    │    (la página de output carga esta URL y reproduce el audio)
    │
    └─ screenshare ← POST /output_media/ { kind: webpage, url: <FRONTEND_URL> }
         (Recall renderiza el frontend en Chromium y lo comparte como pantalla)
```

### Por qué Recall necesita una URL pública

Recall.ai es un servicio externo en la nube. Para que pueda alcanzar los WebSockets del agente (que corre localmente o en un servidor), la máquina debe exponer sus endpoints en una URL HTTPS públicamente accesible.

**Sin URL pública → el bot se une a la reunión pero no hay audio ni screenshare.**

Esta URL pública se configura en `PUBLIC_BASE_URL`.

### Avatar del bot

Al unirse a la llamada, el bot muestra una imagen JPEG/PNG como su cámara. Se configura en `src/agent/recall/assets.py` como `ALIA_AVATAR_B64` (base64, sin prefijo `data:`). Se envía vía `POST /api/v1/bot/{id}/output_video/` una vez que el bot entra a la llamada.

---

## 8. Frontend de screenshare

El frontend es una SPA (Single Page Application) que Recall.ai carga en un Chromium headless y comparte como screenshare dentro de la reunión de Meet.

### Control remoto vía WebSocket

Recall.ai no expone CDP ni acceso a Playwright sobre su Chromium. El control de la página se hace desde adentro: la SPA mantiene una conexión WebSocket al agente y reacciona a comandos JSON:

```
Agente (Python) → send_ui_command({ cmd, payload })
    │
    ▼
WebSocket /recall/output-ws/{session_id}
    │   (mismo WebSocket que recibe audio, diferenciado por tipo: binary=audio, string=comando)
    ▼
Frontend SPA (Chromium de Recall)
    └─ actualiza DOM → Recall captura el frame → aparece en la reunión
```

### Por qué el frontend también necesita túnel

El frontend corre como un servicio HTTP independiente. Recall.ai debe poder cargar su URL para renderizarlo en su Chromium. Si el frontend corre localmente, debe tener una URL pública — de la misma manera que el agente.

```
SCREENSHARE_DEFAULT_URL = https://<tunnel-frontend>.trycloudflare.com
```

---

## 9. Túneles Cloudflare

### Por qué son necesarios

Dos servicios requieren ser alcanzables públicamente desde internet:

| Servicio | Puerto | Motivo |
|----------|--------|--------|
| **Agent API** | `8002` | Recall.ai envía audio por WebSocket y carga la página de output |
| **Frontend** | `(configurable)` | Recall.ai carga el frontend en su Chromium para el screenshare |

**Cloudflared** crea túneles HTTPS efímeros gratuitos sin necesidad de abrir puertos en el router ni tener IP pública fija.

### Uso

```bash
# Túnel para el agente (actualiza PUBLIC_BASE_URL en .env y reinicia el contenedor)
make tunnel

# Túnel para el frontend (actualiza SCREENSHARE_DEFAULT_URL en .env)
make tunnel-frontend
```

El script `scripts/tunnel.sh`:
1. Lanza `cloudflared tunnel --url http://localhost:<PORT>`
2. Espera hasta 60 s hasta obtener la URL `https://*.trycloudflare.com`
3. Escribe la URL en `.env`
4. Reinicia el contenedor afectado para que tome la nueva URL

> **Cada vez que relanzas el túnel obtienes una URL diferente.** Debes reiniciar los contenedores para que usen la nueva URL. `make tunnel` lo hace automáticamente para el agente.

### Instalación de cloudflared

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# Linux
curl -L https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared
```

---

## 10. Servicios externos y API keys

### Obligatorias para el agente

| Variable | Servicio | Dónde obtenerla |
|----------|----------|-----------------|
| `OPENAI_API_KEY` | OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) — LLM (GPT-5.4-mini/nano) + STT (Whisper-1) |
| `RECALL_API_KEY` | Recall.ai | [app.recall.ai](https://app.recall.ai) → Settings → API Keys |
| `LOCALSTACK_AUTH_TOKEN` | LocalStack | [app.localstack.cloud](https://app.localstack.cloud) → Auth Token (plan gratuito disponible) |

### Opcionales / con default

| Variable | Servicio | Default | Descripción |
|----------|----------|---------|-------------|
| `LANGFUSE_PUBLIC_KEY` | Langfuse | — | Observabilidad de LLM (trazas, tokens, latencia) |
| `LANGFUSE_SECRET_KEY` | Langfuse | — | Par del public key |
| `LANGFUSE_HOST` | Langfuse | `https://cloud.langfuse.com` | Self-hosted o cloud |

### Solo necesarias si cambias el backend TTS

| Variable | Cuándo es necesaria |
|----------|---------------------|
| `OPENAI_API_KEY` | También requerida si `TTS_BACKEND=openai` |
| — | Edge TTS es gratuito y no requiere key |

### URLs dinámicas (se actualizan con los túneles)

| Variable | Descripción |
|----------|-------------|
| `PUBLIC_BASE_URL` | URL pública del agente. Recall.ai la usa para WebSockets y página de output. |
| `SCREENSHARE_DEFAULT_URL` | URL pública del frontend. Recall.ai la carga como screenshare. |

---

## 11. Requisitos de la máquina

### Software obligatorio

| Herramienta | Versión mínima | Instalación |
|-------------|----------------|-------------|
| **Docker Desktop** | 24+ | [docker.com/get-started](https://www.docker.com/get-started) |
| **Docker Compose** | v2 (incluido en Docker Desktop) | — |
| **cloudflared** | cualquiera | `brew install cloudflare/cloudflare/cloudflared` |
| **make** | cualquiera | Incluido en macOS/Linux |
| **curl** | cualquiera | Incluido en macOS/Linux |

### Recursos mínimos recomendados

| Recurso | Mínimo | Nota |
|---------|--------|------|
| **RAM** | 8 GB | Airflow + PostgreSQL + LocalStack + Agent consumen ~4-5 GB en conjunto |
| **Disco** | 15 GB libres | Modelos Kokoro (~340 MB) + imágenes Docker (~8 GB) + datos |
| **CPU** | 4 cores | TTS Kokoro y Whisper son intensivos en CPU |

### Python (solo para desarrollo local fuera de Docker)

```bash
Python 3.11+   # el contenedor usa python:3.11-slim
```

### Modelos descargados automáticamente al construir el contenedor

| Archivo | Tamaño | Fuente |
|---------|--------|--------|
| `kokoro-v1.0.onnx` | ~310 MB | GitHub Releases (thewh1teagle/kokoro-onnx) |
| `voices-v1.0.bin` | ~26 MB | GitHub Releases (thewh1teagle/kokoro-onnx) |

> Los modelos se descargan durante `docker compose build agent`. No necesitas descargarlos manualmente.

---

## 12. Configuración inicial

### 1. Clonar el repositorio

```bash
git clone <repo-url>
cd rappi
```

### 2. Crear el archivo de entorno

```bash
make init-env
```

### 3. Editar `.env` con los valores reales

```bash
# Obligatorio
LOCALSTACK_AUTH_TOKEN=<tu-token-de-localstack>
OPENAI_API_KEY=<tu-openai-api-key>
RECALL_API_KEY=<tu-recall-api-key>

# Opcional — observabilidad
LANGFUSE_PUBLIC_KEY=<pk-lf-...>
LANGFUSE_SECRET_KEY=<sk-lf-...>
```

### 4. Construir imágenes

```bash
docker compose build
```

> El build del agente descarga ~340 MB de modelos Kokoro. Solo ocurre la primera vez.

### 5. Levantar el stack

```bash
make up
```

### 6. Verificar que todo está corriendo

```bash
docker compose ps
```

Servicios esperados: `postgres`, `localstack`, `airflow-init` (termina solo), `airflow-webserver`, `airflow-scheduler`, `airflow-triggerer`, `infra-init` (termina solo), `ingest`, `agent`.

### 7. Exponer el agente con túnel (requerido para Recall.ai)

```bash
make tunnel
```

Esto actualiza `PUBLIC_BASE_URL` en `.env` y reinicia el contenedor del agente.

### 8. Ejecutar el ETL con los datos de prueba

```bash
make trigger-etl
```

### 9. Crear un bot en una reunión de Meet

```bash
curl -X POST http://localhost:8002/recall/bots \
  -H 'Content-Type: application/json' \
  -d '{"meeting_url": "https://meet.google.com/xxx-yyyy-zzz", "store_id": "STR001"}'
```

---

## 13. Comandos de referencia

### Stack

```bash
make up              # Levanta todos los servicios
make down            # Detiene y elimina contenedores
make build           # Reconstruye imágenes
make logs            # Sigue logs de todos los servicios
make restart         # Reinicia servicios
make reset-localstack # Destruye y vuelve a crear el volumen de LocalStack
make reset-all       # Destruye todo (volúmenes incluidos) — datos se pierden
```

### ETL

```bash
make trigger-etl     # Sube data/aliados_dataset.csv al ingest y dispara el DAG
make etl-status      # Muestra los últimos 5 runs del DAG etl_stores_csv
```

### Túneles

```bash
make tunnel          # Abre túnel para el agente (:8002) y actualiza .env
make tunnel-frontend # Abre túnel para el frontend y actualiza SCREENSHARE_DEFAULT_URL en .env
```

### Debug

```bash
make check-db        # Lista tablas en rappi_handoff
docker compose --profile debug up -d adminer  # Levanta Adminer en :8081
```

### Desarrollo local (fuera de Docker)

```bash
make install-local   # Crea .venv e instala dependencias
source .venv/bin/activate
```

---

## 14. Puertos locales

| Puerto | Servicio | URL |
|--------|----------|-----|
| `5432` | PostgreSQL | `localhost:5432` |
| `4566` | LocalStack (S3, EventBridge, etc.) | `http://localhost:4566` |
| `8001` | Ingest API | `http://localhost:8001` |
| `8002` | Agent API | `http://localhost:8002` |
| `8003` | Frontend SPA | `http://localhost:8003` |
| `8080` | Airflow UI | `http://localhost:8080` |
| `8081` | Adminer (profile `debug`) | `http://localhost:8081` |

---

## Diagrama de dependencias entre servicios externos

```
                    ┌─────────────────────────────────┐
                    │         MÁQUINA LOCAL            │
                    │                                  │
                    │  Agent API (:8002) ◄─────────────┼── cloudflared tunnel ◄── Recall.ai
                    │                                  │         ▲
                    │  Frontend  (:8003) ◄─────────────┼── cloudflared tunnel ◄── Recall.ai
                    │                                  │         (screenshare)
                    │  PostgreSQL (:5432)               │
                    │  LocalStack (:4566)               │
                    │  Airflow    (:8080)               │
                    └─────────────────────────────────┘
                              │           │
                    ┌─────────┘           └──────────┐
                    ▼                                ▼
             OpenAI API                        Recall.ai API
         (LLM + STT + TTS)              (bot en Meet / audio / screenshare)
                    │
                    ▼
              Langfuse Cloud
            (trazas y métricas)
```

> **Regla de oro:** cualquier servicio que Recall.ai deba alcanzar necesita un túnel activo. Hoy son dos: el agente y el frontend.
