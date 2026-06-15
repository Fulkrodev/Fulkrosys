#!/usr/bin/env bash
# FULKRO — provision one-shot entrypoint (docker-compose.prod.yml · servicio `provision`)
# ════════════════════════════════════════════════════════════════════════════
# Reproduce el ORDEN INVIOLABLE del runbook Hetzner sobre un PostgreSQL ya
# levantado (servicio `postgres` en la red de compose · host=postgres:5432).
# Idempotente: seguro relanzarlo sobre un cluster ya provisionado.
#
#   1. init-extensions.sql   (superuser)        → pgvector / AGE / pgaudit / pgcrypto / uuid-ossp
#   2. init-functions.sql    (superuser)        → funciones PL/pgSQL (audit_log hash chain R6)
#   3. init-roles.sql        (superuser)        → crea + endurece fulkro_app / _bypassrls / _migrate
#   4. alembic upgrade head  (fulkro_migrate)   → esquema (árbol con 1 head · dinámico)
#   5. grants sobre tablas creadas por migraciones (superuser)
#   6. seed_all_fulkro       (fulkro_migrate)   → catálogos + pricing + clientes
#   7. REVOKE UPDATE,DELETE ON audit_log (superuser) → append-only por privilegio (R6)
#
# NOTA: init-extensions y init-roles también se montan en
# /docker-entrypoint-initdb.d del contenedor postgres → se ejecutan AUTO en el
# PRIMER arranque con data-dir vacío. Este script los REejecuta (idempotentes)
# para cubrir el caso de volumen pre-existente y para garantizar el orden
# explícito previo a alembic/seed. Doble cobertura intencional.
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Conexión (valores inyectados por compose · ver docker-compose.prod.yml) ──
PGHOST="${PROVISION_PGHOST:-postgres}"
PGPORT="${PROVISION_PGPORT:-5432}"
PGDB="${PROVISION_PGDB:-fulkro}"
PG_SUPER_USER="${PROVISION_SUPER_USER:-fulkro}"
PG_SUPER_PW="${PROVISION_SUPER_PW:?PROVISION_SUPER_PW requerido (POSTGRES_PASSWORD)}"

# ── Passwords de los roles runtime/migrate (B3 · alineadas al .env.prod) ──────
# init-roles.sql hardcodea passwords DEV (fulkro_*_dev_password). En prod, las
# passwords reales (aleatorias) viven en .env.prod (env del contenedor). El paso
# [3.5] de abajo hace ALTER USER para que los roles coincidan con las que el
# backend (DATABASE_URL · fulkro_app) y alembic (fulkro_migrate) usan en runtime.
#
# Preferencia: var explícita PROVISION_*_PW; fallback: derivar de DATABASE_URL*.
# El nombre canónico de la var es FULKRO_{APP,MIGRATE}_DB_PASSWORD (= template +
# generate-prod-secrets.sh + compose).
_pw_from_url() {  # extrae la password de postgresql://user:PW@host/db
  printf '%s' "$1" | sed -nE 's#^[a-z+]+://[^:/@]+:([^@]*)@.*$#\1#p'
}
APP_PW="${PROVISION_APP_PW:-}"
[ -z "${APP_PW}" ] && APP_PW="$(_pw_from_url "${DATABASE_URL:-}")"
[ -z "${APP_PW}" ] && APP_PW="fulkro_app_dev_password"

MIGRATE_PW="${PROVISION_MIGRATE_PW:-}"
[ -z "${MIGRATE_PW}" ] && MIGRATE_PW="$(_pw_from_url "${DATABASE_MIGRATE_URL:-}")"
[ -z "${MIGRATE_PW}" ] && MIGRATE_PW="fulkro_migrate_dev_password"

REPO_ROOT="${PROVISION_REPO_ROOT:-/app}"
INIT_DIR="${REPO_ROOT}/infra/docker"

MIGRATE_URL="postgresql://fulkro_migrate:${MIGRATE_PW}@${PGHOST}:${PGPORT}/${PGDB}"
SEED_URL="postgresql+asyncpg://fulkro_migrate:${MIGRATE_PW}@${PGHOST}:${PGPORT}/${PGDB}"
SEED_FLAGS="${PROVISION_SEED_FLAGS:---skip-corpus --skip-age-kg}"

psql_super() {
  PGPASSWORD="${PG_SUPER_PW}" psql -v ON_ERROR_STOP=1 \
    -h "${PGHOST}" -p "${PGPORT}" -U "${PG_SUPER_USER}" "$@"
}

echo "==> [0/7] esperar a que PostgreSQL acepte conexiones (${PGHOST}:${PGPORT})"
for i in $(seq 1 60); do
  if PGPASSWORD="${PG_SUPER_PW}" pg_isready -h "${PGHOST}" -p "${PGPORT}" -U "${PG_SUPER_USER}" >/dev/null 2>&1; then
    echo "    postgres listo (intento ${i})"
    break
  fi
  if [ "${i}" -eq 60 ]; then echo "    ERROR: postgres no respondió en 60 intentos" >&2; exit 1; fi
  sleep 2
done

echo "==> [1/7] init-extensions.sql (superuser · pgvector/AGE/pgaudit)"
psql_super -d "${PGDB}" -f "${INIT_DIR}/init-extensions.sql" >/dev/null

echo "==> [2/7] init-functions.sql (superuser · funciones PL/pgSQL R6)"
psql_super -d "${PGDB}" -f "${INIT_DIR}/init-functions.sql" >/dev/null

echo "==> [3/7] init-roles.sql (superuser · endurecimiento de roles · idempotente)"
psql_super -d "${PGDB}" -f "${INIT_DIR}/init-roles.sql" >/dev/null

# ── [3.5] ALTER USER · alinear passwords de roles al .env.prod (B3 · idempotente)
# init-roles.sql deja passwords DEV. Sin esto, el backend (DATABASE_URL · pwd
# aleatoria) y alembic (fulkro_migrate · pwd aleatoria) fallan con
# "password authentication failed". Se ejecuta ANTES de alembic (paso 4), que ya
# conecta como fulkro_migrate con MIGRATE_PW.
#
# Las passwords se inyectan vía variables de psql (:'var') → quoting/escaping
# seguro aunque contengan símbolos. OJO: la interpolación :'var' SOLO ocurre en
# scripts (-f / stdin), NO en -c · por eso se alimenta por stdin (-f -) y los
# valores llegan al proceso psql como variables de entorno (ALT_APP_PW/ALT_MIG_PW).
echo "==> [3.5/7] ALTER USER fulkro_app / fulkro_migrate PASSWORD (alinear al .env.prod)"
ALT_APP_PW="${APP_PW}" ALT_MIG_PW="${MIGRATE_PW}" \
PGPASSWORD="${PG_SUPER_PW}" psql -v ON_ERROR_STOP=1 \
  -h "${PGHOST}" -p "${PGPORT}" -U "${PG_SUPER_USER}" -d "${PGDB}" -f - >/dev/null <<'PSQL'
\set app_pw `printf %s "$ALT_APP_PW"`
\set mig_pw `printf %s "$ALT_MIG_PW"`
ALTER USER fulkro_app     WITH PASSWORD :'app_pw';
ALTER USER fulkro_migrate WITH PASSWORD :'mig_pw';
PSQL

echo "==> [4/7] alembic upgrade head (como fulkro_migrate · árbol con 1 head · dinámico)"
# PYTHONPATH=REPO_ROOT: env.py hace `import backend.app.models`; al hacer
# `cd backend` el paquete `backend` debe seguir resolviéndose (el -e install lo
# cubre, pero lo forzamos explícito por robustez cross-imagen).
( cd "${REPO_ROOT}/backend" \
  && DATABASE_MIGRATE_URL="${MIGRATE_URL}" PYTHONPATH="${REPO_ROOT}" \
     python -m alembic upgrade head )

echo "==> [5/7] grants fulkro_app / _bypassrls sobre tablas creadas por las migraciones"
psql_super -d "${PGDB}" -c "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO fulkro_app, fulkro_app_bypassrls; GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO fulkro_app, fulkro_app_bypassrls; GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO fulkro_app, fulkro_app_bypassrls;" >/dev/null

echo "==> [6/7] seed_all_fulkro (como fulkro_migrate · BYPASSRLS · flags: ${SEED_FLAGS})"
# El seed usa asyncio+asyncpg. Aislado en background + wait para que el cierre del
# event loop no tumbe el script bajo `set -e` (mismo patrón que build_test_db.sh).
set +e
DATABASE_URL="${SEED_URL}" DATABASE_URL_SYNC="${MIGRATE_URL}" PYTHONPATH="${REPO_ROOT}" \
  python "${REPO_ROOT}/backend/scripts/seed_all_fulkro.py" ${SEED_FLAGS} &
wait "$!"
SEED_RC=$?
set -e
if [ "${SEED_RC}" -ne 0 ]; then echo "    ERROR: seed_all_fulkro rc=${SEED_RC}" >&2; exit 1; fi

echo "==> [7/7] REVOKE UPDATE,DELETE ON audit_log (superuser · append-only R6)"
psql_super -d "${PGDB}" -c "REVOKE UPDATE, DELETE ON audit_log FROM fulkro_app, fulkro_app_bypassrls;" >/dev/null

echo "==> PROVISION DONE · esquema + roles endurecidos + seed + audit_log append-only"
psql_super -tA -d "${PGDB}" -c "SELECT 'tablas='||count(*) FROM information_schema.tables WHERE table_schema='public';"
