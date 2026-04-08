# Rappi Onboarding ETL

Infraestructura local para ingestar un CSV de aliados, archivarlo en S3 sobre LocalStack, transformarlo y cargarlo en PostgreSQL vía Airflow.

Arquitectura objetivo:

- `S3 PutObject -> EventBridge -> Airflow DAG`
- `ETL -> EventBridge Scheduler -> agent session`

## Requisitos

- Docker Desktop
- `make`
- Un token personal válido de LocalStack

## Clone and Run

1. Clona el repo.
2. Crea tu archivo de entorno:

```bash
make init-env
```

3. Edita `.env` y reemplaza:

```bash
LOCALSTACK_AUTH_TOKEN=your_localstack_token
```

por tu token real.

4. Levanta el stack:

```bash
make up
```

Si quieres un arranque completamente limpio de LocalStack:

```bash
make reset-localstack
make up
```

Servicios esperados:

- Airflow: `http://localhost:8080`
- Ingest API: `http://localhost:8001`
- PostgreSQL: `localhost:5432`
- Adminer: `http://localhost:8081` usando el profile `debug`

## Servicios del stack

- `airflow-scheduler` es solo el scheduler interno de Apache Airflow.
- Ese contenedor no define ni debe definir la automatización de sesiones con aliados.
- Se mantiene porque Airflow lo necesita para ejecutar el DAG ETL.
- El scheduler de negocio para sesiones automáticas no está implementado todavía en este repo.
- La opción preferida para ese scheduler de negocio es Amazon EventBridge Scheduler sobre LocalStack, no un proceso propio, no un polling worker y no un DAG sensor.

## Flujo objetivo

1. Un operador o sistema externo sube un CSV al bucket raw.
2. S3 emite `Object Created`.
3. EventBridge detecta el nuevo objeto y dispara Airflow.
4. Airflow ejecuta el ETL usando el objeto recién subido.
5. Durante el load, el ETL persiste `meetings`.
6. Como último paso del DAG, `schedule_meetings` programa en EventBridge Scheduler cada reunión futura válida.
7. Cada schedule dispara un evento `MeetingDue` en el bus `default` 5 minutos antes de `scheduled_at`.

En este diseño, EventBridge cumple dos papeles distintos:

- EventBridge rules: arranque inmediato del ETL cuando entra un CSV al bucket
- EventBridge Scheduler: programación temporal de las sesiones futuras del agente

## Ejecutar el ETL

Sube el dataset de prueba al bucket raw. El trigger del DAG ocurre por `S3 -> EventBridge -> Airflow`:

```bash
make trigger-etl
```

Para revisar las últimas ejecuciones del DAG:

```bash
make etl-status
```

Para apagar todo:

```bash
make down
```

## Entorno local Python

Si quieres trabajar fuera de Docker:

```bash
make install-local
source .venv/bin/activate
```

La `venv` está preparada para Python 3.14 con las versiones pinneadas del proyecto.

## Scheduler automático de sesiones

Esta funcionalidad es opcional pero diferenciadora. La dirección preferida del proyecto es usar Amazon EventBridge Scheduler vía LocalStack para disparar automáticamente la sesión del agente AI cuando exista una reunión próxima en `meetings`.

> [!INFO]
> El agendamiento de reuniones ya está implementado en la arquitectura y en el código del ETL: el DAG crea schedules one-shot en EventBridge Scheduler 5 minutos antes de `scheduled_at`. Lo que no puede validarse end-to-end en entorno local no es el diseño ni la creación del schedule, sino su ejecución automática, porque LocalStack actualmente no soporta disparar realmente los targets de EventBridge Scheduler. En otras palabras: en local sí se valida que el schedule se crea con la metadata correcta; la invocación temporal real debe probarse en AWS o mediante una simulación local separada.

Separación intencional:

- Airflow: orquestación ETL
- EventBridge rules: arranque inmediato del ETL cuando entra un CSV al bucket raw
- EventBridge Scheduler: automatización temporal de sesiones

Comportamiento esperado:

1. El ETL persiste `meetings` en PostgreSQL.
2. Si una fila contiene `scheduled_at`, la capa de scheduling crea o actualiza un schedule en EventBridge Scheduler.
3. Minutos antes de la reunión, EventBridge Scheduler dispara la sesión del agente para ese `store_id`.
4. El agente carga contexto del aliado desde PostgreSQL.
5. Al finalizar, el sistema actualiza `meetings` y registra el resultado en `handoff_sessions`.

Ejemplo:

- Si existe una reunión para el jueves 3 de abril a las 10:00 AM, el sistema puede programar un disparo a las 9:58 AM para iniciar automáticamente la sesión del agente usando el `meeting_link` del aliado.

Estado actual:

- El ETL ya carga `meetings` en PostgreSQL.
- El DAG ya incluye el paso final `schedule_meetings`.
- LocalStack ya expone `events` y `scheduler` en Docker.
- `infra-init` ya habilita `S3 -> EventBridge` en el bucket raw.
- El trigger `S3 -> EventBridge -> Airflow` ya está implementado y validado.
- El scheduling de reuniones ya crea schedules one-shot en EventBridge Scheduler para `meetings.status='pending'`.
- El target actual de esos schedules es un evento en EventBridge con `source='rappi.handoff.meeting'` y `detail-type='MeetingDue'`.
- La automatización de sesiones aún no está implementada en código.
- `handoff_sessions` aún no existe en el esquema actual.

> [!INFO]
> La ausencia de ejecución automática local no debe interpretarse como un fallo de la solución. El comportamiento observado corresponde a una limitación conocida de LocalStack: permite `create_schedule`, `list_schedules` y `get_schedule`, pero no emula la ejecución real del schedule ni la invocación del target cuando llega la hora programada. La decisión arquitectónica sigue siendo válida porque:
> 1. mantiene una separación limpia entre ETL y automatización operativa,
> 2. usa un servicio nativo y correcto para disparos temporales,
> 3. evita polling sobre `meetings`,
> 4. alinea el entorno local con la arquitectura objetivo de AWS.

Diseño recomendado:

- Fuente de verdad: tabla `meetings` en `rappi_handoff.public`
- Entrada ETL: evento de S3 sobre el bucket raw
- Scheduler de negocio: EventBridge Scheduler
- Llave de contexto: `store_id`
- Momento de ejecución: calculado a partir de `scheduled_at`
- Trigger actual: emitir un evento `MeetingDue` en EventBridge 5 minutos antes
- Acción esperada futura: invocar al agente con `meeting_id`, `store_id` y `meeting_link`
- Persistencia esperada: actualizar `meetings.status` y registrar resultados en `handoff_sessions`

Objetivo de esta decisión arquitectónica:

- Mantener el ETL enfocado en normalización y persistencia, no en esperar ni vigilar reuniones.
- Representar la intención temporal de negocio con un scheduler nativo en vez de polling.
- Dejar el runtime del agente desacoplado del pipeline de carga.
- Hacer que la transición a AWS real sea directa, porque el contrato temporal ya queda modelado desde ahora.

Más detalle en [docs/scheduler.md](/Users/cripto/code/rappi/docs/scheduler.md).
