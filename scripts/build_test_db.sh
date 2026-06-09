#!/usr/bin/env bash
# Ejecutable 8 Pasada 16 · build_test_db.sh
# Construye la BD de test `fulkro_test` DESDE alembic upgrade head (NO reusa la BD live).
# Mata la deuda conftest-reusa-BD-live (raíz de drift + data-pollution timesheet/llm).
# Reproducible: drop → create → extensions/functions/roles → upgrade head → grants → seed.
# Idempotente (drop+recreate). Uso: bash scripts/build_test_db.sh   (desde raíz repo, en WSL)
set -euo pipefail

DB="${FULKRO_TEST_DB_NAME:-fulkro_test}"
PGHOST="${FULKRO_TEST_PGHOST:-localhost}"
PGPORT="${FULKRO_TEST_PGPORT:-5433}"
CONTAINER="${FULKRO_PG_CONTAINER:-fulkro-postgres-1}"
SUPER_PW="${FULKRO_PG_SUPER_PW:-changeme}"
APP_URL="postgresql+asyncpg://fulkro_app:fulkro_app_dev_password@${PGHOST}:${PGPORT}/${DB}"
APP_URL_SYNC="postgresql://fulkro_app:fulkro_app_dev_password@${PGHOST}:${PGPORT}/${DB}"
MIGRATE_URL="postgresql://fulkro_migrate:fulkro_migrate_dev_password@${PGHOST}:${PGPORT}/${DB}"
VENV_PY="${FULKRO_VENV_PY:-.venv/bin/python}"
# REPRO GAP 3: en este worktree (fulkro-portales) NO existe ./.venv; el venv real
# es compartido en /home/usuario/fulkro/.venv. Si la var no se pasó y el default
# relativo no existe, caer al venv compartido conocido. NO sobrescribe FULKRO_VENV_PY
# si el caller lo fijó explícitamente.
if [ ! -x "${VENV_PY}" ] && [ -z "${FULKRO_VENV_PY:-}" ]; then
  VENV_PY="/home/usuario/fulkro/.venv/bin/python"
fi
# Path absoluto canónico del intérprete: el paso [4/6] hace `cd backend` y antes
# anteponía "../" al VENV_PY relativo. Con el fallback a un venv compartido fuera
# del repo ese "../" rompe (daría ../home/...). Resolver a absoluto aquí y usar
# VENV_PY_ABS en cualquier subshell que cambie de directorio.
case "${VENV_PY}" in
  /*) VENV_PY_ABS="${VENV_PY}" ;;
  *)  VENV_PY_ABS="$(pwd)/${VENV_PY}" ;;
esac
if [ ! -x "${VENV_PY_ABS}" ]; then
  echo "    ERROR: intérprete Python del venv no ejecutable: ${VENV_PY_ABS}" >&2
  echo "    Pasa FULKRO_VENV_PY=/ruta/a/.venv/bin/python o crea ./.venv" >&2
  exit 1
fi

psql_super() { docker exec -i -e PGPASSWORD="${SUPER_PW}" "${CONTAINER}" psql -v ON_ERROR_STOP=1 -U fulkro "$@"; }

echo "==> [1/6] drop+create ${DB}"
psql_super -d postgres -c "DROP DATABASE IF EXISTS ${DB};"
psql_super -d postgres -c "CREATE DATABASE ${DB} OWNER fulkro;"

echo "==> [2/6] extensions + functions"
psql_super -d "${DB}" < infra/docker/init-extensions.sql >/dev/null
psql_super -d "${DB}" < infra/docker/init-functions.sql >/dev/null

echo "==> [3/6] roles + default privileges (init-roles · idempotente)"
psql_super -d "${DB}" < infra/docker/init-roles.sql >/dev/null

echo "==> [4/6] alembic upgrade head"
( cd backend && DATABASE_MIGRATE_URL="${MIGRATE_URL}" "${VENV_PY_ABS}" -m alembic upgrade head )

echo "==> [5/6] grants fulkro_app sobre tablas creadas por las migraciones"
psql_super -d "${DB}" -c "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO fulkro_app, fulkro_app_bypassrls; GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO fulkro_app, fulkro_app_bypassrls; GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO fulkro_app, fulkro_app_bypassrls;" >/dev/null
# R6 audit_log append-only POR PRIVILEGIO (no solo por trigger): ni el rol app ni
# el bypass pueden UPDATE/DELETE la cadena hash, ni aunque session_replication_role
# desactive los triggers. INSERT+SELECT se mantienen.
psql_super -d "${DB}" -c "REVOKE UPDATE, DELETE ON audit_log FROM fulkro_app, fulkro_app_bypassrls;" >/dev/null
# Materialized views: el rol bypass debe poder REFRESH (owner-only en PG). El runtime
# NO refresca MVs hoy, pero el job M28 (y los tests) lo hacen vía el rol app/bypass.
psql_super -d "${DB}" -c "ALTER MATERIALIZED VIEW IF EXISTS mv_drift_summary_10x4 OWNER TO fulkro_app_bypassrls;" >/dev/null 2>&1 || true

echo "==> [6/7] seed (seed_all_fulkro · --skip-corpus: el corpus se carga desde fixture)"
# Seed corre como SUPERUSER (fulkro_migrate) para bypassar RLS al insertar projects/clients
# (seed_fake_clients usa psycopg2 sin escalar rol → como fulkro_app violaba RLS de projects).
# Los TESTS sí corren como fulkro_app (RLS enforced) vía conftest · solo el SEED escala.
# --skip-corpus: la ingesta RAG real necesita fastembed (:8080) + PDFs CCN/EUR-Lex que NO
# están en el repo. En su lugar cargamos el corpus desde un fixture data-only (paso 7).
# --skip-age-kg: el grafo Apache AGE (KG demo) requiere superuser real para LOAD
# 'age', no disponible sobre TCP con fulkro_migrate · 0 tests dependen de fulkro_kg.
SEED_FLAGS="${FULKRO_TEST_SEED_FLAGS:---skip-corpus --skip-age-kg}"
SEED_URL="postgresql+asyncpg://fulkro_migrate:fulkro_migrate_dev_password@${PGHOST}:${PGPORT}/${DB}"
# El seed corre como fulkro_migrate (BYPASSRLS → insert projects/clients sin que
# RLS lo bloquee). Los TESTS sí corren como fulkro_app (RLS enforced) vía conftest.
# seed_all_fulkro usa asyncio+asyncpg; al cerrar el event loop tumba la shell
# en primer plano bajo `set -e` (los handlers de señal del loop alcanzan el grupo
# de procesos foreground). Lo lanzamos en background + wait para aislarlo: así el
# script continúa al paso 7 (corpus). Sin esto, [7/7] no se ejecutaba (salía rc=0).
set +e
DATABASE_URL="${SEED_URL}" DATABASE_URL_SYNC="${MIGRATE_URL}" PYTHONPATH=. "${VENV_PY_ABS}" backend/scripts/seed_all_fulkro.py ${SEED_FLAGS} &
wait "$!"
SEED_RC=$?
set -e
if [ "${SEED_RC}" -ne 0 ]; then echo "    ERROR: seed_all_fulkro rc=${SEED_RC}"; exit 1; fi

echo "==> [7/7] corpus RAG fixture (knowledge_* + ens_measure_refuerzos/dimensiones + mappings)"
# Datos de referencia normativos (RD 311/2022 + CCN-STIC + UE) ya ingeridos y embebidos.
# Esquema = migraciones (drift-proof); el corpus es contenido de referencia público,
# determinista, sin dependencia de fastembed ni descargas externas en build/CI.
# session_replication_role=replica → bypassa FK (pg_dump emite tablas en orden alfabético,
# refuerzos referencia knowledge_chunks que va después). Regenerar fixture:
#   docker exec ... pg_dump --data-only -t knowledge_documents -t knowledge_chunks \
#     -t knowledge_measure_mappings -t ens_measure_refuerzos -t ens_measure_dimensiones \
#     fulkro | gzip > backend/tests/fixtures/corpus_seed.sql.gz
CORPUS_FIXTURE="backend/tests/fixtures/corpus_seed.sql.gz"
if [ -f "${CORPUS_FIXTURE}" ]; then
  {
    echo "SET session_replication_role = replica;"
    echo "TRUNCATE knowledge_measure_mappings, ens_measure_refuerzos, ens_measure_dimensiones, knowledge_chunks, knowledge_documents, knowledge_sources CASCADE;"
    gzip -dc "${CORPUS_FIXTURE}"
  } | psql_super -q -d "${DB}" >/dev/null
  docker exec -e PGPASSWORD="${SUPER_PW}" "${CONTAINER}" psql -U fulkro -tA -d "${DB}" -c "SELECT 'corpus chunks='||count(*) FROM knowledge_chunks;"
else
  echo "    WARNING: ${CORPUS_FIXTURE} no existe · tests corpus/* fallarán (seed-parity)"
fi

echo "==> DONE · ${DB} reproducido desde migraciones + seed + corpus fixture"
docker exec -e PGPASSWORD="${SUPER_PW}" "${CONTAINER}" psql -U fulkro -tA -d "${DB}" -c "SELECT 'tablas='||count(*) FROM information_schema.tables WHERE table_schema='public';"
