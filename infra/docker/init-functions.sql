-- Funciones helper RLS para tenant isolation.
-- Se crean en schema `public` (no en ag_catalog, que es read-only bajo AGE).
--
-- Ejecutar manualmente tras init-extensions.sql:
--   docker exec fulkro-postgres-1 psql -U fulkro -d fulkro \
--       -f /docker-entrypoint-initdb.d/02-functions.sql
--
-- Estas funciones son usadas por las policies RLS de todas las tablas que
-- llevan columna project_id o client_id.

SET search_path = public;

CREATE OR REPLACE FUNCTION current_client_id() RETURNS uuid AS
'SELECT NULLIF(current_setting(''app.current_client_id'', true), '''')::uuid;'
LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION current_project_id() RETURNS uuid AS
'SELECT NULLIF(current_setting(''app.current_project_id'', true), '''')::uuid;'
LANGUAGE sql STABLE;

-- Smoke test: ambas deben devolver NULL si no hay session config
DO $$
BEGIN
    PERFORM current_client_id();
    PERFORM current_project_id();
    RAISE NOTICE 'RLS helpers OK';
END;
$$;
