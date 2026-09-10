#!/usr/bin/env bash
# Ejecutable 8 Pasada 16 · build_test_db.sh
# Construye la BD de test `fulkro_test` DESDE alembic upgrade head (NO reusa la BD live).
# Mata la deuda conftest-reusa-BD-live (raíz de drift + data-pollution timesheet/llm).
# Reproducible: drop → create → extensions/functions/roles → upgrade head → grants → seed.
# Idempotente (drop+recreate). Uso: bash scripts/build_test_db.sh   (desde cualquier cwd)
set -euo pipefail

# Raíz del repo derivada de la ubicación del script (scripts/ → ..), NO del cwd
# ni de una ruta absoluta cableada. Todos los paths de abajo son relativos a ella.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

DB="${FULKRO_TEST_DB_NAME:-fulkro_test}"
PGHOST="${FULKRO_TEST_PGHOST:-localhost}"
PGPORT="${FULKRO_TEST_PGPORT:-5433}"
SUPER_PW="${FULKRO_PG_SUPER_PW:-changeme}"

# Nombre del contenedor de PostgreSQL. Docker Compose lo compone como
# "<proyecto>-<servicio>-<índice>" y el proyecto por defecto es el nombre del
# directorio raíz normalizado (minúsculas, sin caracteres raros). El default
# anterior estaba cableado a "fulkro-postgres-1", que sólo existe si el clon se
# llama exactamente "fulkro"; en un clon de github.com/Fulkrodev/Fulkrosys el
# directorio es "Fulkrosys" y el contenedor "fulkrosys-postgres-1", con lo que
# el paso [1/6] moría con "No such container".
# Orden: FULKRO_PG_CONTAINER > COMPOSE_PROJECT_NAME > nombre del directorio.
# Si el candidato no existe se ABORTA con la lista de candidatos: NO se elige
# automáticamente otro Postgres de la máquina, porque este script hace DROP
# DATABASE y equivocarse de contenedor destruiría la base de otro proyecto.
_compose_project="${COMPOSE_PROJECT_NAME:-$(basename "${REPO_ROOT}" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')}"
CONTAINER="${FULKRO_PG_CONTAINER:-${_compose_project}-postgres-1}"
if ! docker inspect "${CONTAINER}" >/dev/null 2>&1; then
  echo "    ERROR: no existe el contenedor de PostgreSQL '${CONTAINER}'." >&2
  echo "    Contenedores con servicio compose 'postgres' en marcha:" >&2
  docker ps --filter "label=com.docker.compose.service=postgres" --format '      {{.Names}}' >&2 || true
  echo "    Arranca la base (docker compose up -d postgres) o, si el tuyo se llama" >&2
  echo "    de otra forma, pasa FULKRO_PG_CONTAINER=<nombre> (este script hace DROP" >&2
  echo "    DATABASE: no se elige contenedor por ti)." >&2
  exit 1
fi
APP_URL="postgresql+asyncpg://fulkro_app:fulkro_app_dev_password@${PGHOST}:${PGPORT}/${DB}"
APP_URL_SYNC="postgresql://fulkro_app:fulkro_app_dev_password@${PGHOST}:${PGPORT}/${DB}"
MIGRATE_URL="postgresql://fulkro_migrate:fulkro_migrate_dev_password@${PGHOST}:${PGPORT}/${DB}"
# Intérprete Python. Default: el venv del propio repo. El fallback anterior
# apuntaba, con ruta absoluta, al venv de OTRO checkout de una única máquina:
# fuera de ella el script cogía un intérprete inexistente en vez de avisar.
# Ahora sólo hay dos candidatos dentro del repo y, si no, error claro.
VENV_PY="${FULKRO_VENV_PY:-}"
if [ -z "${VENV_PY}" ]; then
  for _cand in "${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/backend/.venv/bin/python"; do
    if [ -x "${_cand}" ]; then VENV_PY="${_cand}"; break; fi
  done
fi
VENV_PY="${VENV_PY:-${REPO_ROOT}/.venv/bin/python}"
# Path absoluto canónico del intérprete: el paso [4/6] hace `cd backend`, así que
# un path relativo se rompería dentro de ese subshell.
case "${VENV_PY}" in
  /*) VENV_PY_ABS="${VENV_PY}" ;;
  *)  VENV_PY_ABS="${REPO_ROOT}/${VENV_PY}" ;;
esac
if [ ! -x "${VENV_PY_ABS}" ]; then
  echo "    ERROR: intérprete Python del venv no ejecutable: ${VENV_PY_ABS}" >&2
  echo "    Crea el venv en la raíz del repo (python3.12 -m venv .venv &&" >&2
  echo "    .venv/bin/pip install -e backend[dev]) o pasa FULKRO_VENV_PY=/ruta/a/python" >&2
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
