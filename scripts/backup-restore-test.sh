#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# FULKRO · backup-restore-test.sh · R8 "Backup probado mensualmente"
# ════════════════════════════════════════════════════════════════════════════
# Prueba un RESTORE a una BD throwaway y VERIFICA integridad. Mide RTO. NUNCA
# toca la BD live `fulkro` (restaura a una DB con sufijo `_restoretest`).
#
# Dos modos:
#   (default, LÓGICO)   pg_dump de la DB origen → restore a throwaway → verifica.
#                       Validable también en dev/WSL (smoke ejecutable).
#   (--pgbackrest)      Restaura un backup FÍSICO pgBackRest a un cluster
#                       sandbox. HETZNER-ONLY (requiere pgbackrest + cluster).
#
# Verificaciones de integridad post-restore:
#   1. La DB throwaway abre y responde.
#   2. Nº de tablas > umbral (esquema completo restaurado).
#   3. ENS por nivel 52/68/73 (datos de referencia presentes).
#   4. fn_audit_log_verify_chain().ok = TRUE (cadena hash R6 intacta).
#
# Salida: PASS/FAIL por check + RTO en segundos. exit 0 sólo si TODO PASS.
#
# Uso (desde raíz del repo):
#   bash scripts/backup-restore-test.sh                 # modo lógico, origen=fulkro_test
#   FULKRO_SRC_DB=fulkro bash scripts/backup-restore-test.sh   # origen=live (sólo lectura via dump)
#   bash scripts/backup-restore-test.sh --pgbackrest    # Hetzner-only
#
# Variables (overrides):
#   FULKRO_SRC_DB        DB origen a respaldar/probar (default fulkro_test)
#   FULKRO_PG_CONTAINER  contenedor postgres (default fulkro-postgres-1)
#   FULKRO_PG_SUPER_PW   password superuser fulkro (default changeme)
#   FULKRO_MIN_TABLES    umbral mínimo de tablas (default 200)
# ════════════════════════════════════════════════════════════════════════════
set -uo pipefail

MODE="logical"
[ "${1:-}" = "--pgbackrest" ] && MODE="pgbackrest"

SRC_DB="${FULKRO_SRC_DB:-fulkro_test}"
RESTORE_DB="${SRC_DB}_restoretest"
CONTAINER="${FULKRO_PG_CONTAINER:-fulkro-postgres-1}"
SUPER_PW="${FULKRO_PG_SUPER_PW:-changeme}"
MIN_TABLES="${FULKRO_MIN_TABLES:-200}"
STANZA="${PGBACKREST_STANZA:-fulkro}"

PASS=0; FAIL=0
green() { printf '  \033[32mPASS\033[0m · %s\n' "$1"; PASS=$((PASS+1)); }
red()   { printf '  \033[31mFAIL\033[0m · %s\n' "$1"; FAIL=$((FAIL+1)); }
info()  { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

# Guard absoluto: jamás restaurar sobre la DB live `fulkro`.
if [ "${RESTORE_DB}" = "fulkro" ]; then
  echo "FATAL: RESTORE_DB resolvió a 'fulkro' (DB live). Abortado." >&2
  exit 2
fi

psql_super() { docker exec -i -e PGPASSWORD="${SUPER_PW}" "${CONTAINER}" psql -v ON_ERROR_STOP=1 -U fulkro "$@"; }
psql_super_q() { docker exec -i -e PGPASSWORD="${SUPER_PW}" "${CONTAINER}" psql -tA -U fulkro "$@"; }

echo "════════════════════════════════════════════════════════════════"
echo " FULKRO backup-restore-test · modo=${MODE} · origen=${SRC_DB} → ${RESTORE_DB}"
echo " $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "════════════════════════════════════════════════════════════════"

START_TS=$(date +%s)

if [ "${MODE}" = "pgbackrest" ]; then
  # ── MODO pgBackRest (HETZNER-ONLY) ─────────────────────────────────────────
  info "Restore físico pgBackRest a sandbox (HETZNER-ONLY)"
  if ! command -v pgbackrest >/dev/null 2>&1; then
    red "pgbackrest no instalado · este modo SOLO corre en el servidor Hetzner"
    echo ""
    echo "FRONTERA HONESTA: el restore físico pgBackRest requiere el binario +"
    echo "un cluster con stanza '${STANZA}'. Ejecutar EN EL SERVIDOR Hetzner:"
    echo "  sudo -u postgres pgbackrest --stanza=${STANZA} --delta restore"
    echo "  (ver infra/pgbackrest/README.md §5)"
    exit 1
  fi
  SANDBOX="${PGBACKREST_SANDBOX_PGDATA:-/var/lib/postgresql/restore-sandbox}"
  echo "Restaurando a ${SANDBOX} ..."
  sudo -u postgres pgbackrest --stanza="${STANZA}" --pg1-path="${SANDBOX}" --delta restore \
    || { red "pgbackrest restore falló"; exit 1; }
  green "pgbackrest restore completado a ${SANDBOX}"
  echo "Arrancar el cluster sandbox en un puerto libre y re-correr este script"
  echo "en modo lógico apuntando a esa instancia para las verificaciones de datos."
  RTO=$(( $(date +%s) - START_TS ))
  echo ""
  echo "RTO (restore físico): ${RTO}s"
  exit 0
fi

# ── MODO LÓGICO (default · validable en dev) ──────────────────────────────────
info "1/5 · dump del origen (${SRC_DB}) — sólo lectura, no toca origen"
DUMP_FILE="/tmp/fulkro_restoretest_$(date +%Y%m%d_%H%M%S).dump"
if ! docker exec -e PGPASSWORD="${SUPER_PW}" "${CONTAINER}" \
       pg_dump -U fulkro -Fc -f "${DUMP_FILE}" "${SRC_DB}" 2>/tmp/restoretest_dump.err; then
  red "pg_dump del origen falló (¿existe ${SRC_DB}?)"
  sed 's/^/    /' /tmp/restoretest_dump.err 2>/dev/null
  exit 1
fi
DUMP_SIZE=$(docker exec "${CONTAINER}" stat -c %s "${DUMP_FILE}" 2>/dev/null || echo 0)
green "dump creado (${DUMP_SIZE} bytes) en contenedor"

info "2/5 · recrear DB throwaway ${RESTORE_DB}"
psql_super -d postgres -c "DROP DATABASE IF EXISTS ${RESTORE_DB};" >/dev/null 2>&1
psql_super -d postgres -c "CREATE DATABASE ${RESTORE_DB} OWNER fulkro;" >/dev/null 2>&1 \
  && green "DB throwaway creada" || { red "no se pudo crear ${RESTORE_DB}"; exit 1; }

info "3/5 · restore del dump a ${RESTORE_DB}"
# pg_restore puede emitir warnings no-fatales (extensiones ya presentes); evaluamos por verificación, no por rc.
docker exec -e PGPASSWORD="${SUPER_PW}" "${CONTAINER}" \
  pg_restore -U fulkro --no-owner --role=fulkro -d "${RESTORE_DB}" "${DUMP_FILE}" \
  >/tmp/restoretest_restore.log 2>&1
green "pg_restore ejecutado (warnings no-fatales tolerados; se valida por contenido)"

info "4/5 · verificaciones de integridad post-restore"

# Check A · la DB abre y responde
if [ "$(psql_super_q -d "${RESTORE_DB}" -c 'SELECT 1;' 2>/dev/null)" = "1" ]; then
  green "DB ${RESTORE_DB} abre y responde"
else
  red "DB ${RESTORE_DB} NO responde"
fi

# Check B · nº de tablas >= umbral
N_TABLES=$(psql_super_q -d "${RESTORE_DB}" -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo 0)
if [ "${N_TABLES:-0}" -ge "${MIN_TABLES}" ]; then
  green "esquema restaurado · ${N_TABLES} tablas (>= ${MIN_TABLES})"
else
  red "esquema incompleto · ${N_TABLES} tablas (< ${MIN_TABLES})"
fi

# Check C · ENS por nivel 52/68/73
ENS_LINE=$(psql_super_q -d "${RESTORE_DB}" -c \
  "SELECT count(*) FILTER (WHERE aplica_basica)||'/'||count(*) FILTER (WHERE aplica_media)||'/'||count(*) FILTER (WHERE aplica_alta) FROM ens_measures;" 2>/dev/null || echo "ERR")
if [ "${ENS_LINE}" = "52/68/73" ]; then
  green "ENS por nivel correcto · ${ENS_LINE} (BÁSICA/MEDIA/ALTA)"
else
  red "ENS por nivel INCORRECTO · '${ENS_LINE}' (esperado 52/68/73)"
fi

# Check D · cadena hash audit_log intacta (R6)
CHAIN_OK=$(psql_super_q -d "${RESTORE_DB}" -c \
  "SELECT ok FROM fn_audit_log_verify_chain();" 2>/dev/null || echo "ERR")
if [ "${CHAIN_OK}" = "t" ]; then
  green "cadena hash audit_log intacta (R6) · fn_audit_log_verify_chain().ok=TRUE"
elif [ "${CHAIN_OK}" = "ERR" ]; then
  red "fn_audit_log_verify_chain() no disponible (¿migración d4f8b2a90001 aplicada?)"
else
  red "cadena hash audit_log ROTA tras restore (R6 violado) · ok=${CHAIN_OK}"
fi

info "5/5 · limpieza de la DB throwaway"
psql_super -d postgres -c "DROP DATABASE IF EXISTS ${RESTORE_DB};" >/dev/null 2>&1 \
  && green "DB throwaway eliminada" || red "no se pudo eliminar ${RESTORE_DB} (limpiar a mano)"
docker exec "${CONTAINER}" rm -f "${DUMP_FILE}" 2>/dev/null || true

RTO=$(( $(date +%s) - START_TS ))

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " RESULTADO · PASS=${PASS} FAIL=${FAIL} · RTO=${RTO}s"
echo "════════════════════════════════════════════════════════════════"
if [ "${FAIL}" -eq 0 ]; then
  echo " ✓ RESTORE TEST SUPERADO (R8) · registrar en m26 BackupRestoreTest"
  exit 0
else
  echo " ✗ RESTORE TEST FALLIDO · revisar checks marcados FAIL"
  exit 1
fi
