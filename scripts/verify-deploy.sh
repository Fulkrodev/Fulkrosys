#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# FULKRO · verify-deploy.sh · gate post-deploy (on-server)
# ════════════════════════════════════════════════════════════════════════════
# Comprueba que el despliegue cumple TODO el gate de producción. Salida clara
# PASS/FAIL por check. exit 0 sólo si TODOS los checks bloqueantes pasan.
#
# Checks:
#   DB-1  fulkro_app NOSUPERUSER (rolsuper=f)
#   DB-2  fulkro_app_bypassrls existe + NOSUPERUSER + BYPASSRLS
#   DB-3  fulkro_migrate NOSUPERUSER + BYPASSRLS
#   DB-4  fulkro_app NO es miembro de fulkro (sin escalada a superuser)
#   AL-1  exactamente 1 head Alembic = client_mfa_email_code_001
#   ENS-1 medidas por nivel = 52 / 68 / 73 (BÁSICA / MEDIA / ALTA)
#   ENS-2 op.exp.10 = "Protección de claves criptográficas"
#   R6-1  fn_audit_log_verify_chain().ok = TRUE
#   R6-2  fulkro_app SIN privilegio UPDATE/DELETE sobre audit_log
#   MIO-1 bucket fulkro-evidence-worm existe con Object Lock / WORM activo
#   SVC-1 todos los servicios compose healthy (o running sin healthcheck)
#   API-1 /api/v1/health → 200
#   FE-1  frontend (raíz) → 200
#
# Frontera honesta: API-1/FE-1/MIO-1/SVC-1 requieren el stack prod arriba
# (Hetzner). DB/AL/ENS/R6 se validan contra cualquier PostgreSQL provisionado
# (incl. fulkro_test en dev, para probar la LÓGICA del gate). Lo Hetzner-only
# se marca y se omite con SKIP si la dependencia no está.
#
# Uso (en el servidor, tras deploy-hetzner.sh):
#   bash scripts/verify-deploy.sh
#
# Modo dev (probar la lógica SQL del gate contra fulkro_test):
#   FULKRO_VERIFY_MODE=dev bash scripts/verify-deploy.sh
#
# Variables:
#   FULKRO_VERIFY_MODE   prod (default) | dev
#   FULKRO_DB_NAME       DB a verificar (prod=fulkro · dev=fulkro_test)
#   FULKRO_PG_CONTAINER  contenedor postgres (dev=fulkro-postgres-1)
#   FULKRO_PG_SUPER_PW   password superuser (default changeme)
#   FULKRO_API_URL       URL health (default http://localhost:8000/api/v1/health)
#   FULKRO_FE_URL        URL frontend (default http://localhost:3000/)
#   FULKRO_COMPOSE_FILE  compose prod (default docker-compose.prod.yml)
#   FULKRO_ENV_FILE      env prod (default .env.prod)
#   FULKRO_MINIO_ALIAS   alias mc ya configurado (default local)
# ════════════════════════════════════════════════════════════════════════════
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

MODE="${FULKRO_VERIFY_MODE:-prod}"
if [ "${MODE}" = "dev" ]; then
  DB_NAME="${FULKRO_DB_NAME:-fulkro_test}"
  PG_CONTAINER="${FULKRO_PG_CONTAINER:-fulkro-postgres-1}"
else
  DB_NAME="${FULKRO_DB_NAME:-fulkro}"
  PG_CONTAINER="${FULKRO_PG_CONTAINER:-}"   # en prod usamos compose exec
fi
SUPER_PW="${FULKRO_PG_SUPER_PW:-changeme}"
API_URL="${FULKRO_API_URL:-http://localhost:8000/api/v1/health}"
FE_URL="${FULKRO_FE_URL:-http://localhost:3000/}"
COMPOSE_FILE="${FULKRO_COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${FULKRO_ENV_FILE:-.env.prod}"
PG_SERVICE="${FULKRO_PG_SERVICE:-postgres}"
MINIO_ALIAS="${FULKRO_MINIO_ALIAS:-local}"
ALEMBIC_EXPECTED_HEAD="unify_pricing_fiscal_rls_001"

PASS=0; FAIL=0; SKIP=0
pass() { printf '  \033[32mPASS\033[0m  %-7s %s\n' "$1" "$2"; PASS=$((PASS+1)); }
fail() { printf '  \033[31mFAIL\033[0m  %-7s %s\n' "$1" "$2"; FAIL=$((FAIL+1)); }
skip() { printf '  \033[33mSKIP\033[0m  %-7s %s\n' "$1" "$2"; SKIP=$((SKIP+1)); }
hdr()  { printf '\n\033[1m── %s ──\033[0m\n' "$1"; }

# psql helper: en dev usa docker exec al contenedor; en prod usa compose exec.
psql_q() {
  local sql="$1"
  if [ "${MODE}" = "dev" ]; then
    docker exec -i -e PGPASSWORD="${SUPER_PW}" "${PG_CONTAINER}" \
      psql -tA -U fulkro -d "${DB_NAME}" -c "${sql}" 2>/dev/null
  else
    if [ -f "${COMPOSE_FILE}" ]; then
      docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T \
        -e PGPASSWORD="${SUPER_PW}" "${PG_SERVICE}" \
        psql -tA -U fulkro -d "${DB_NAME}" -c "${sql}" 2>/dev/null
    else
      # último recurso: psql local
      PGPASSWORD="${SUPER_PW}" psql -tA -U fulkro -d "${DB_NAME}" -c "${sql}" 2>/dev/null
    fi
  fi
}

echo "════════════════════════════════════════════════════════════════"
echo " FULKRO verify-deploy · modo=${MODE} · db=${DB_NAME}"
echo " $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "════════════════════════════════════════════════════════════════"

# ── Roles ─────────────────────────────────────────────────────────────────────
hdr "Roles (separación de privilegios · auditoría 2026-06-07)"

APP_SUPER="$(psql_q "SELECT rolsuper FROM pg_roles WHERE rolname='fulkro_app';")"
case "${APP_SUPER}" in
  f) pass "DB-1" "fulkro_app NOSUPERUSER (rolsuper=f)" ;;
  "") fail "DB-1" "fulkro_app no existe o DB inaccesible" ;;
  *) fail "DB-1" "fulkro_app ES superuser (rolsuper=${APP_SUPER}) · BLOQUEANTE" ;;
esac

BYP="$(psql_q "SELECT coalesce((SELECT (NOT rolsuper) AND rolbypassrls FROM pg_roles WHERE rolname='fulkro_app_bypassrls'), false);")"
if [ "${BYP}" = "t" ]; then
  pass "DB-2" "fulkro_app_bypassrls existe · NOSUPERUSER + BYPASSRLS"
else
  fail "DB-2" "fulkro_app_bypassrls ausente o mal configurado"
fi

MIG="$(psql_q "SELECT coalesce((SELECT (NOT rolsuper) AND rolbypassrls FROM pg_roles WHERE rolname='fulkro_migrate'), false);")"
if [ "${MIG}" = "t" ]; then
  pass "DB-3" "fulkro_migrate NOSUPERUSER + BYPASSRLS"
else
  fail "DB-3" "fulkro_migrate ausente o mal configurado"
fi

# fulkro_app NO debe ser miembro de fulkro (cierre de escalada a superuser)
APP_IS_SU_MEMBER="$(psql_q "SELECT EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON m.roleid=r.oid JOIN pg_roles g ON m.member=g.oid WHERE r.rolname='fulkro' AND g.rolname='fulkro_app');")"
if [ "${APP_IS_SU_MEMBER}" = "f" ]; then
  pass "DB-4" "fulkro_app NO es miembro de fulkro (sin escalada a superuser)"
else
  fail "DB-4" "fulkro_app ES miembro de fulkro · escalada superuser abierta · BLOQUEANTE"
fi

# ── Alembic head ──────────────────────────────────────────────────────────────
hdr "Esquema · Alembic"
# version_num de la tabla alembic_version (en prod ya migrado).
HEADS="$(psql_q "SELECT string_agg(version_num, ',') FROM alembic_version;")"
N_HEADS="$(psql_q "SELECT count(*) FROM alembic_version;")"
if [ "${N_HEADS}" = "1" ] && [ "${HEADS}" = "${ALEMBIC_EXPECTED_HEAD}" ]; then
  pass "AL-1" "1 head Alembic = ${HEADS}"
elif [ "${N_HEADS}" = "1" ]; then
  fail "AL-1" "head inesperado: ${HEADS} (esperado ${ALEMBIC_EXPECTED_HEAD})"
else
  fail "AL-1" "${N_HEADS} heads en alembic_version (${HEADS}) · esperado 1 · BLOQUEANTE"
fi

# ── ENS por nivel ─────────────────────────────────────────────────────────────
hdr "Catálogo ENS (RD 311/2022)"
ENS="$(psql_q "SELECT count(*) FILTER (WHERE aplica_basica)||'/'||count(*) FILTER (WHERE aplica_media)||'/'||count(*) FILTER (WHERE aplica_alta) FROM ens_measures;")"
if [ "${ENS}" = "52/68/73" ]; then
  pass "ENS-1" "medidas por nivel = 52/68/73 (BÁSICA/MEDIA/ALTA)"
else
  fail "ENS-1" "medidas por nivel = '${ENS}' (esperado 52/68/73) · BLOQUEANTE"
fi

OPEXP10="$(psql_q "SELECT nombre FROM ens_measures WHERE codigo='op.exp.10';")"
if [ "${OPEXP10}" = "Protección de claves criptográficas" ]; then
  pass "ENS-2" "op.exp.10 = 'Protección de claves criptográficas'"
else
  fail "ENS-2" "op.exp.10 = '${OPEXP10}' (esperado 'Protección de claves criptográficas')"
fi

# ── R6 audit_log ──────────────────────────────────────────────────────────────
hdr "Inmutabilidad audit_log (R6)"
CHAIN="$(psql_q "SELECT ok FROM fn_audit_log_verify_chain();")"
case "${CHAIN}" in
  t) pass "R6-1" "fn_audit_log_verify_chain().ok = TRUE (cadena hash intacta)" ;;
  "") fail "R6-1" "fn_audit_log_verify_chain() no disponible (¿migración d4f8b2a90001?)" ;;
  *) fail "R6-1" "cadena hash audit_log ROTA · ok=${CHAIN} · BLOQUEANTE" ;;
esac

# fulkro_app NO debe poseer UPDATE/DELETE sobre audit_log
APP_CAN_MUT="$(psql_q "SELECT (has_table_privilege('fulkro_app','audit_log','UPDATE') OR has_table_privilege('fulkro_app','audit_log','DELETE'));")"
if [ "${APP_CAN_MUT}" = "f" ]; then
  pass "R6-2" "fulkro_app SIN UPDATE/DELETE sobre audit_log (append-only por privilegio)"
elif [ "${APP_CAN_MUT}" = "t" ]; then
  fail "R6-2" "fulkro_app PUEDE UPDATE/DELETE audit_log · falta REVOKE · BLOQUEANTE"
else
  skip "R6-2" "no se pudo evaluar privilegio audit_log"
fi

# ── MinIO WORM ────────────────────────────────────────────────────────────────
hdr "MinIO · bucket evidencias WORM (Object Lock)"
# mc_run: ejecuta el cliente mc donde esté disponible. Devuelve 127 si NINGÚN
# canal mc existe (entonces el check se omite como Hetzner-only).
MC_CHANNEL=""
if command -v mc >/dev/null 2>&1; then
  MC_CHANNEL="host"
elif [ "${MODE}" = "prod" ] && [ -f "${COMPOSE_FILE}" ] \
     && docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps minio >/dev/null 2>&1; then
  MC_CHANNEL="compose"
fi
mc_run() {
  case "${MC_CHANNEL}" in
    host)    mc "$@" ;;
    compose) docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T minio mc "$@" ;;
    *)       return 127 ;;
  esac
}
if [ "${MODE}" = "dev" ]; then
  skip "MIO-1" "Hetzner-only · el bucket WORM se provisiona en prod (mc mb --with-lock)"
elif [ -z "${MC_CHANNEL}" ]; then
  skip "MIO-1" "mc no disponible aquí (Hetzner-only) · verificar EN servidor: mc retention info ${MINIO_ALIAS}/fulkro-evidence-worm"
else
  LOCK_JSON="$(mc_run retention info "${MINIO_ALIAS}/fulkro-evidence-worm" 2>/dev/null || true)"
  if echo "${LOCK_JSON}" | grep -qiE "compliance|governance|mode"; then
    pass "MIO-1" "fulkro-evidence-worm con Object Lock/retención activa"
  elif mc_run ls "${MINIO_ALIAS}/fulkro-evidence-worm" >/dev/null 2>&1; then
    fail "MIO-1" "bucket existe pero SIN retención WORM detectada · re-crear con mc mb --with-lock"
  else
    fail "MIO-1" "bucket fulkro-evidence-worm ausente o inaccesible"
  fi
fi

# ── Servicios healthy ─────────────────────────────────────────────────────────
hdr "Servicios (docker compose healthy)"
if [ "${MODE}" = "prod" ] && [ -f "${COMPOSE_FILE}" ]; then
  BAD="$(docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps -a --format '{{.Name}} {{.State}} {{.Health}}' 2>/dev/null | awk '$3=="unhealthy" || $2=="exited" || $2=="dead" {print $1}' | tr '\n' ' ')"
  if [ -z "${BAD}" ]; then
    pass "SVC-1" "todos los servicios running/healthy"
  else
    fail "SVC-1" "servicios no-healthy: ${BAD}"
  fi
else
  skip "SVC-1" "modo dev o sin compose prod · no se evalúan servicios prod"
fi

# ── API health ────────────────────────────────────────────────────────────────
hdr "Endpoints HTTP"
# Captura el http_code sin -f (que descartaría el código en errores) y sin
# doble-echo. curl en fallo de conexión emite "000" vía -w; añadimos un
# fallback "000" sólo si curl no escribió nada (timeout duro).
http_code() {
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$1" 2>/dev/null)"
  [ -z "${code}" ] && code="000"
  printf '%s' "${code}"
}
# En modo dev los servidores de aplicación son intermitentes → estos checks son
# Hetzner-only: SKIP en dev, FAIL real en prod.
if ! command -v curl >/dev/null 2>&1; then
  skip "API-1" "curl no disponible"
  skip "FE-1" "curl no disponible"
elif [ "${MODE}" = "dev" ]; then
  skip "API-1" "Hetzner-only · en dev los servers son intermitentes (re-correr en prod)"
  skip "FE-1" "Hetzner-only · en dev los servers son intermitentes (re-correr en prod)"
else
  CODE="$(http_code "${API_URL}")"
  if [ "${CODE}" = "200" ]; then
    pass "API-1" "${API_URL} → 200"
  elif [ "${CODE}" = "000" ]; then
    fail "API-1" "${API_URL} inaccesible (000) · ¿backend arriba?"
  else
    fail "API-1" "${API_URL} → ${CODE} (esperado 200)"
  fi

  FECODE="$(http_code "${FE_URL}")"
  # El frontend puede 200 directo o 3xx→login; aceptamos 2xx/3xx como "responde".
  if [ "${FECODE}" = "200" ]; then
    pass "FE-1" "${FE_URL} → 200"
  elif [ "${FECODE#3}" != "${FECODE}" ]; then
    pass "FE-1" "${FE_URL} → ${FECODE} (redirect · frontend responde)"
  elif [ "${FECODE}" = "000" ]; then
    fail "FE-1" "${FE_URL} inaccesible (000) · ¿frontend arriba?"
  else
    fail "FE-1" "${FE_URL} → ${FECODE} (esperado 200/3xx)"
  fi
fi

# ── Resumen ───────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
echo " RESULTADO · PASS=${PASS} FAIL=${FAIL} SKIP=${SKIP}"
echo "════════════════════════════════════════════════════════════════"
if [ "${FAIL}" -eq 0 ]; then
  echo " ✓ GATE SUPERADO"
  [ "${SKIP}" -gt 0 ] && echo " (nota: ${SKIP} checks Hetzner-only omitidos · re-correr EN el servidor)"
  exit 0
else
  echo " ✗ GATE FALLIDO · ${FAIL} check(s) bloqueante(s)"
  exit 1
fi
