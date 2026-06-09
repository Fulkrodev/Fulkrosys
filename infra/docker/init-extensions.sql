-- PostgreSQL extensions for FULKRO
-- Executed on first container startup (empty data dir only).
-- When upgrading an existing volume, run these manually:
--   docker exec fulkro-postgres-1 psql -U fulkro -d fulkro -f /docker-entrypoint-initdb.d/01-extensions.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "age";
CREATE EXTENSION IF NOT EXISTS "pgaudit";

LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- RLS helper functions (single-quote syntax avoids $$ escaping issues)
CREATE OR REPLACE FUNCTION current_client_id() RETURNS uuid AS
'SELECT NULLIF(current_setting(''app.current_client_id'', true), '''')::uuid;'
LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION current_project_id() RETURNS uuid AS
'SELECT NULLIF(current_setting(''app.current_project_id'', true), '''')::uuid;'
LANGUAGE sql STABLE;
