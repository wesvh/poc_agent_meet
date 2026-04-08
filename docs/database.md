# Database Layout

El sistema usa estas bases dentro del contenedor PostgreSQL:

- `airflow`: metadata interna de Airflow
- `rappi_handoff`: base canónica de la aplicación ETL
- `postgres`: base administrativa del servidor PostgreSQL

## Regla operativa

Las tablas del ETL deben existir solo en:

- base: `rappi_handoff`
- schema: `public`

No deben existir tablas del ETL en la base `postgres`.

## Verificación

```bash
make check-db
```

## Limpieza de duplicados antiguos

Si vienes de un volumen viejo y ves las tablas del ETL también en `postgres.public`, elimina solo esa copia administrativa con:

```bash
make dedupe-admin-db
```

Ese comando no toca la base canónica `rappi_handoff`.
