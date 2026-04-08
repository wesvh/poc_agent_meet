# Scheduler automático de sesiones

## Decisión arquitectónica

La opción preferida para el scheduler de negocio es:

- Amazon EventBridge Scheduler
- Ejecutado localmente vía LocalStack

> [!INFO]
> La arquitectura de scheduling ya está definida e implementada a nivel de creación de schedules. El paso final del DAG crea schedules one-shot con la metadata de cada reunión futura válida. La limitación actual está en el emulador: LocalStack no ejecuta realmente esos schedules ni dispara sus targets al llegar la hora. Por eso, en local se valida la creación del schedule y su payload, mientras que la ejecución temporal real debe verificarse en AWS o con una simulación local complementaria.

Además, el disparo del ETL debe ser event-driven:

- S3 `PutObject`
- EventBridge rule
- Airflow DAG trigger

No se prefiere:

- un proceso `cron` ad hoc dentro de `docker-compose`
- un worker propio haciendo polling
- un DAG de Airflow consultando `meetings` periódicamente

## Separación de responsabilidades

Hay dos schedulers distintos en este stack y no deben confundirse:

- `airflow-scheduler`: scheduler interno del motor Airflow
- `EventBridge Scheduler`: scheduler de negocio para sesiones automáticas

Y además existe una tercera pieza temporal:

- `EventBridge` rule/event bus: disparo inmediato del ETL cuando llega un CSV al bucket raw

Regla de proyecto:

- Airflow se usa para ETL
- EventBridge se usa para arrancar el ETL cuando aparece un archivo nuevo en S3
- EventBridge Scheduler se usa para activar handoff sessions en el tiempo correcto

Por eso el contenedor `airflow-scheduler` debe existir, pero no es la solución para agendar sesiones con aliados.

## Motivo

EventBridge Scheduler representa mejor el modelo objetivo de producción:

- intención explícita basada en tiempo
- integración directa con AWS/LocalStack
- menor acoplamiento con Airflow
- separación clara entre orquestación ETL y automatización operativa de sesiones

Para el inicio del ETL, el patrón correcto también es event-driven:

- menor latencia
- cero polling vacío
- semántica exacta: si llega archivo, se procesa

## Estado actual del repo

Hoy el repo:

- sí carga reuniones en la tabla `meetings`
- sí usa LocalStack en Docker
- sí expone los servicios `events` y `scheduler` en LocalStack
- sí habilita `S3 -> EventBridge` en el bucket raw durante `infra-init`
- sí implementa `S3 -> EventBridge -> Airflow`
- no implementa todavía el agente AI
- no implementa todavía `handoff_sessions`
- sí implementa la creación/programación de jobs en EventBridge Scheduler
- `src/ingest/api.py` ahora sube el archivo a S3 y delega el arranque del ETL a EventBridge

Qué sí puede validarse hoy en LocalStack:

- que el ETL crea el schedule correcto
- que el schedule queda en el group esperado
- que el `Target` contiene `meeting_id`, `store_id`, `meeting_link`, `scheduled_at` y `trigger_at`
- que la expresión temporal se calcula como `scheduled_at - 5 minutos`

Qué no puede validarse hoy en LocalStack:

- que el schedule se ejecute automáticamente al llegar la hora
- que el target reciba realmente el evento disparado por Scheduler
- que `ActionAfterCompletion=DELETE` elimine el schedule tras su ejecución

## Cómo se vería la integración

Flujo recomendado:

1. Un cliente sube un CSV al bucket raw.
2. S3 emite `Object Created`.
3. EventBridge detecta el objeto nuevo y dispara Airflow con el `s3_key`.
4. El ETL normaliza y upserta `meetings`.
5. El task final `schedule_meetings` traduce cada reunión futura válida a un schedule one-shot en EventBridge Scheduler.
6. El target actual del schedule publica un evento `MeetingDue` al bus `default` con `meeting_id`, `store_id`, `meeting_link`, `scheduled_at` y `trigger_at`.
7. En una siguiente iteración, un consumer de ese evento invocará el runtime del agente.
8. Al cerrar la sesión, el sistema persistirá el resultado en `meetings` y `handoff_sessions`.

## Comportamiento esperado

1. Un proceso del dominio de scheduling detecta reuniones con estado `scheduled` y `scheduled_at` dentro de la ventana objetivo, o bien crea schedules directamente durante el ETL al persistir la reunión.
2. Cada reunión futura válida se traduce a un schedule en EventBridge Scheduler.
3. El schedule se programa para `scheduled_at - 5 minutos`.
4. Cuando llega la hora programada, EventBridge Scheduler emite un evento `MeetingDue`.
5. En la integración final, ese evento disparará la sesión del agente Handoff AI para ese `store_id`.
6. El agente carga el contexto del aliado desde PostgreSQL antes de iniciar la conversación.
7. El agente usa el `meeting_link` asociado para entrar a la sesión.
8. Al finalizar, el sistema actualiza `meetings` y registra el resultado en `handoff_sessions`.

> [!INFO]
> Si en pruebas locales el schedule permanece en estado `ENABLED` después de la hora programada, eso no implica un error del ETL ni de la integración de creación. Ese comportamiento es consistente con la limitación actual de LocalStack para EventBridge Scheduler.

Ejemplo:

- existe una reunión para el jueves 3 de abril a las 10:00 AM
- el sistema crea un schedule para las 9:58 AM
- a las 9:58 AM se emite un evento `MeetingDue`
- en la siguiente iteración, ese evento activará la sesión automática del agente con el `meeting_link` del aliado

## Comportamiento esperado cuando se implemente

1. El ETL upserta `meetings` con `status='pending'`, `scheduled_at` y `meeting_link`.
2. Un componente de scheduling crea o actualiza schedules en EventBridge Scheduler para cada reunión futura válida.
3. Cerca de `scheduled_at`, EventBridge Scheduler dispara la ejecución del agente AI.
4. El agente carga contexto del aliado desde PostgreSQL usando `store_id`.
5. El agente entra al `meeting_link` correspondiente.
6. Al terminar, el sistema actualiza `meetings.status` y registra el resultado en `handoff_sessions`.

## Contratos recomendados

### Tabla existente

- `meetings`

Campos clave ya presentes:

- `store_id`
- `scheduled_at`
- `meeting_link`
- `status`

### Tabla recomendada a agregar

- `handoff_sessions`

Campos sugeridos:

- `id`
- `meeting_id`
- `store_id`
- `started_at`
- `finished_at`
- `status`
- `agent_run_id`
- `summary`
- `artifacts`
- `error_message`

## Integración recomendada

La implementación futura debería quedar fuera del DAG principal de Airflow.

Responsabilidades recomendadas:

- Ingestión raw: subir el CSV a S3
- Event routing: traducir `Object Created` a trigger de Airflow
- ETL: normalizar y persistir datos
- Scheduler integration: crear, actualizar y cancelar schedules de EventBridge Scheduler
- Meeting due event: publicar `MeetingDue` en el bus `default`
- Agent runtime: ejecutar la sesión AI

## Justificación

Se prefiere Amazon EventBridge Scheduler porque mantiene coherencia con la arquitectura ya implementada para el ETL:

- un solo enfoque event-driven para el arranque inmediato y la programación diferida
- menor acoplamiento con Airflow
- evita polling innecesario sobre `meetings`
- encaja naturalmente con LocalStack en entorno local y con AWS en un entorno productivo

Objetivo arquitectónico de esta decisión:

- usar EventBridge para los dos tiempos del sistema:
  - disparo inmediato cuando entra un CSV a S3
  - disparo diferido cuando una reunión está próxima
- separar claramente:
  - Airflow para ETL
  - EventBridge Rules para eventos inmediatos
  - EventBridge Scheduler para eventos temporales
- dejar el agente AI como consumidor de un evento de negocio (`MeetingDue`) y no como dependencia acoplada al DAG
- asegurar que la migración a AWS real no requiera rediseñar el flujo, solo cambiar el entorno de ejecución

## Alcance de LocalStack

Para desarrollo local, LocalStack ya debe exponer:

- `s3`
- `events`
- `scheduler`

El token personal de LocalStack se define en `.env` mediante `LOCALSTACK_AUTH_TOKEN`.

## Nota importante

`airflow-scheduler` en Docker no es el scheduler de negocio.

Ese contenedor es parte normal de Apache Airflow y debe seguir existiendo para que el DAG del ETL funcione correctamente.
