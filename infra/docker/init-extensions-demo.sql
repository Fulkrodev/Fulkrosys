-- ════════════════════════════════════════════════════════════════════════════
-- FULKRO — extensiones PostgreSQL del PERFIL DEMO (docker-compose.demo.yml)
-- ════════════════════════════════════════════════════════════════════════════
-- Gemelo de init-extensions.sql SIN `age` ni `pgaudit`, para poder correr el
-- demo sobre la imagen oficial `pgvector/pgvector:pg16` (que no trae ninguna de
-- las dos) en lugar de sobre la imagen propia `fulkro/postgres:pg16`, que las
-- compila. Ver docs/adr/ADR-001-postgres-demo-sin-age.md.
--
-- Por qué un fichero aparte y no relajar el original:
--   provision-entrypoint.sh ejecuta init-extensions.sql con `psql -v
--   ON_ERROR_STOP=1`, así que un `CREATE EXTENSION "age"` sobre una imagen que
--   no la tiene aborta el paso [1/7] y, con él, todo el arranque. El compose del
--   demo monta ESTE fichero ENCIMA de la ruta del original dentro del
--   contenedor, así que el script no cambia y producción no se toca.
--
-- Las dos funciones helper de RLS son copia literal de init-extensions.sql
-- (líneas 16-22). Se repiten aquí porque init-extensions.sql no se ejecuta en el
-- demo; init-functions.sql (paso [2/7]) las vuelve a crear con CREATE OR REPLACE,
-- de modo que la duplicación es idempotente y sin efecto de orden.
-- ════════════════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- NO se crean aquí (no existen en pgvector/pgvector:pg16):
--   CREATE EXTENSION "age"      → grafo de conocimiento · 0 consumidores en
--                                 backend/app y en las migraciones (ver ADR-001)
--   CREATE EXTENSION "pgaudit"  → auditoría a nivel de servidor · el audit_log
--                                 aplicativo (R6, cadena de hash SHA-256 en
--                                 init-functions.sql + migración d4f8b2a90001)
--                                 es independiente y sí funciona en el demo

-- Funciones helper de RLS (sintaxis con comillas simples para evitar el escapado
-- de $$). Las usan las policies de toda tabla con project_id o client_id.
CREATE OR REPLACE FUNCTION current_client_id() RETURNS uuid AS
'SELECT NULLIF(current_setting(''app.current_client_id'', true), '''')::uuid;'
LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION current_project_id() RETURNS uuid AS
'SELECT NULLIF(current_setting(''app.current_project_id'', true), '''')::uuid;'
LANGUAGE sql STABLE;
