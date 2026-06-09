-- Role application fulkro_app (NOSUPERUSER) para ejercer RLS.
-- El superuser `fulkro` se usa solo en migraciones y seeds; la app
-- corre bajo `fulkro_app` que esta sujeto a RLS enforcement.
--
-- Ejecutar manualmente tras init-functions.sql:
--   docker exec fulkro-postgres-1 psql -U fulkro -d fulkro \
--       -f /docker-entrypoint-initdb.d/03-roles.sql
--
-- La password por defecto es `fulkro_app_dev_password` (matches .env).
-- En produccion, rotar via ALTER USER fulkro_app PASSWORD '...'.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_app') THEN
        CREATE ROLE fulkro_app WITH LOGIN PASSWORD 'fulkro_app_dev_password' NOSUPERUSER;
        RAISE NOTICE 'Created role fulkro_app';
    ELSE
        -- Asegurar la password al valor esperado por .env
        ALTER USER fulkro_app WITH PASSWORD 'fulkro_app_dev_password';
        RAISE NOTICE 'Role fulkro_app existed — password re-aligned';
    END IF;
END;
$$;

-- Grants necesarios para que fulkro_app pueda leer/escribir en public
GRANT USAGE ON SCHEMA public TO fulkro_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO fulkro_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO fulkro_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO fulkro_app;

-- Aplica a objetos creados en el futuro (migraciones futuras)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fulkro_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO fulkro_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO fulkro_app;

-- ════════════════════════════════════════════════════════════════════
-- Role fulkro_app_bypassrls · bypass RLS SIN superuser (auditoría 2026-06-07)
-- ════════════════════════════════════════════════════════════════════
-- SEGURIDAD P0: antes el runtime hacía `SET LOCAL ROLE fulkro` (superuser)
-- para queries admin cross-tenant, y `fulkro_app` era miembro de `fulkro`
-- (GRANT fulkro TO fulkro_app) → cualquier SQL-injection sobre el rol de la
-- app escalaba a SUPERUSER (RCE potencial, lectura de ficheros, CREATE ROLE,
-- RLS+inmutabilidad audit_log R6 = barreras blandas).
-- Ahora: rol dedicado NOSUPERUSER + BYPASSRLS. El runtime hace
-- `SET LOCAL ROLE fulkro_app_bypassrls` (salta RLS para agregados admin) pero
-- NO puede escalar a superuser. fulkro_app YA NO es miembro de fulkro.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_app_bypassrls') THEN
        CREATE ROLE fulkro_app_bypassrls WITH
            NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS;
        RAISE NOTICE 'Created role fulkro_app_bypassrls';
    ELSE
        RAISE NOTICE 'Role fulkro_app_bypassrls existed';
    END IF;
END;
$$;

-- Mismos privilegios DML que fulkro_app (NO ownership · solo CRUD + bypass RLS)
GRANT USAGE ON SCHEMA public TO fulkro_app_bypassrls;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO fulkro_app_bypassrls;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO fulkro_app_bypassrls;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO fulkro_app_bypassrls;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fulkro_app_bypassrls;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO fulkro_app_bypassrls;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO fulkro_app_bypassrls;
-- CLEAN-CLUSTER FIX (deploy Hetzner · TASK A smoke): en un cluster recién
-- creado, fulkro_migrate aún NO existe en este punto (su CREATE ROLE completo
-- está más abajo, ~línea 130). Las sentencias `ALTER DEFAULT PRIVILEGES FOR
-- ROLE fulkro_migrate` de abajo referencian el rol como GRANTOR → fallan con
-- `role "fulkro_migrate" does not exist`. En dev/test no se veía porque los
-- roles son globales y fulkro_migrate ya existía de una corrida previa. Se crea
-- aquí un placeholder idempotente (sin LOGIN) · el bloque completo de abajo le
-- re-alinea password + atributos LOGIN/BYPASSRLS.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_migrate') THEN
        CREATE ROLE fulkro_migrate WITH NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS;
        RAISE NOTICE 'Pre-created placeholder role fulkro_migrate (clean-cluster fix)';
    END IF;
END;
$$;

-- Cubrir tablas creadas por las migraciones (que corren como fulkro_migrate)
ALTER DEFAULT PRIVILEGES FOR ROLE fulkro_migrate IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fulkro_app, fulkro_app_bypassrls;
ALTER DEFAULT PRIVILEGES FOR ROLE fulkro_migrate IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO fulkro_app, fulkro_app_bypassrls;
ALTER DEFAULT PRIVILEGES FOR ROLE fulkro_migrate IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO fulkro_app, fulkro_app_bypassrls;

-- fulkro_app puede asumir el rol bypass (SET LOCAL ROLE fulkro_app_bypassrls)
-- pero YA NO puede asumir el superuser fulkro.
GRANT fulkro_app_bypassrls TO fulkro_app;

-- El harness de tests siembra datos con FK/triggers desactivados
-- (`SET LOCAL session_replication_role = 'replica'`), un GUC que normalmente
-- exige superuser. PostgreSQL 15+ permite delegar GUCs concretos sin dar
-- superuser. Se concede SOLO ese parámetro al rol bypass (NO al rol app).
-- R6: la inmutabilidad de audit_log NO depende solo de los triggers (que
-- replica desactivaría) sino también de PRIVILEGIO — ver build_test_db.sh /
-- deploy: REVOKE UPDATE,DELETE ON audit_log (append-only garantizado).
DO $$
BEGIN
    EXECUTE 'GRANT SET ON PARAMETER session_replication_role TO fulkro_app_bypassrls';
EXCEPTION WHEN others THEN
    RAISE NOTICE 'GRANT SET ON PARAMETER no soportado (PG<15?) · %', SQLERRM;
END;
$$;

-- CIERRE de la escalada: revoca la membresía superuser que clusters previos
-- ya tenían concedida (los roles son globales · quitar el GRANT del script no
-- revoca lo ya otorgado). Idempotente: si no existía, es un no-op con WARNING.
REVOKE fulkro FROM fulkro_app;

-- Verificacion
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_app') THEN
        RAISE NOTICE 'fulkro_app role OK';
    ELSE
        RAISE EXCEPTION 'fulkro_app role NOT created';
    END IF;
END;
$$;


-- ════════════════════════════════════════════════════════════════════
-- Role fulkro_migrate · alembic migrations · NOSUPERUSER + BYPASSRLS
-- ════════════════════════════════════════════════════════════════════
-- Marcos quiere: alembic NO debe correr como superuser (`fulkro`) en
-- producción · separación de permisos. fulkro_migrate puede crear/
-- alterar tablas, secuencias, índices, columnas, pero NO bypass roles
-- ni create role. BYPASSRLS necesario para que migrations puedan
-- modificar tablas tenant-scoped sin set_tenant_context.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_migrate') THEN
        CREATE ROLE fulkro_migrate WITH
            LOGIN PASSWORD 'fulkro_migrate_dev_password'
            NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS;
        RAISE NOTICE 'Created role fulkro_migrate';
    ELSE
        -- LOGIN explícito: el placeholder clean-cluster de arriba se crea NOLOGIN;
        -- aquí se asegura que fulkro_migrate pueda conectar (alembic/seed login).
        ALTER USER fulkro_migrate WITH LOGIN PASSWORD 'fulkro_migrate_dev_password';
        RAISE NOTICE 'Role fulkro_migrate existed — password re-aligned';
    END IF;
END;
$$;

-- Grants necesarios para alembic upgrade/downgrade en public schema
GRANT CONNECT ON DATABASE fulkro TO fulkro_migrate;
GRANT USAGE, CREATE ON SCHEMA public TO fulkro_migrate;
GRANT ALL ON ALL TABLES IN SCHEMA public TO fulkro_migrate;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO fulkro_migrate;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO fulkro_migrate;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO fulkro_migrate;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO fulkro_migrate;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO fulkro_migrate;

-- Permitir ALTER TABLE sobre tablas existentes (creadas por superuser fulkro
-- en init initial). Sin esto, alembic upgrade falla con
-- "InsufficientPrivilege: must be owner of table" para tablas pre-existentes.
-- Mismo pattern que fulkro_app (GRANT fulkro TO fulkro_app).
GRANT fulkro TO fulkro_migrate;

-- REPRO GAP 2 (cluster limpio): el seed corre como fulkro_migrate y ejecuta
-- `SET LOCAL ROLE fulkro_app_bypassrls` (m23 pricing_catalog_seed:151 · bypass RLS
-- para insertar pricing_catalog). Sin esta membresía, en un PG recién provisionado
-- el seed falla con "permission denied to set role fulkro_app_bypassrls" (rc=1).
-- Idempotente · se coloca DESPUÉS de crear fulkro_migrate (línea ~129) para que el
-- rol exista en el momento del GRANT.
GRANT fulkro_app_bypassrls TO fulkro_migrate;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_migrate') THEN
        RAISE NOTICE 'fulkro_migrate role OK';
    ELSE
        RAISE EXCEPTION 'fulkro_migrate role NOT created';
    END IF;
END;
$$;
