#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# FULKRO · deploy-hetzner.sh · despliegue turnkey en el servidor Hetzner
# ════════════════════════════════════════════════════════════════════════════
# Orquesta el compose de producción (docker-compose.prod.yml · Tarea A) de
# principio a fin. NO re-implementa la provisión: delega en los servicios
# one-shot que ya viven en ese compose:
#   - servicio `provision`  → infra/docker/provision-entrypoint.sh ejecuta el
#                             ORDEN INVIOLABLE (init-roles → alembic upgrade head
#                             → seed → REVOKE audit_log R6). Idempotente.
#   - servicio `minio-init` → infra/docker/minio-init.sh crea los buckets, incl.
#                             fulkro-evidence-worm con Object Lock COMPLIANCE 7y.
#
# Secuencia:
#   1. cargar/validar .env.prod          (secretos · Tarea B · gitignored)
#   2. docker compose build              (backend + frontend + postgres prod)
#   3. up -d postgres + esperar healthy
#   4. run --rm provision                (one-shot · orden inviolable + R6)
#   5. up -d minio + run --rm minio-init (buckets + WORM)
#   6. up -d                             (resto de servicios)
#   7. esperar healthy + recordar verify-deploy.sh
#
# Frontera honesta: SOLO turnkey-completo EN EL SERVIDOR Hetzner (Docker Linux,
# TLS/dominio reales). En dev Windows/WSL NO se ejecuta de principio a fin (no
# toca los contenedores dev `fulkro-*`). Aborta limpio si faltan .env.prod o el
# compose de producción.
#
# Uso (en el servidor, desde la raíz del repo desplegado):
#   bash scripts/deploy-hetzner.sh
#
# Flags:
#   --skip-build   no reconstruir imágenes (usar las ya construidas)
#   --skip-seed    pasa PROVISION_SEED_FLAGS para no re-sembrar contenido
#   --dry-run      imprime el plan, no ejecuta nada
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

COMPOSE_FILE="${FULKRO_COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${FULKRO_ENV_FILE:-.env.prod}"
PG_SERVICE="${FULKRO_PG_SERVICE:-postgres}"
ALEMBIC_EXPECTED_HEAD="client_mfa_email_code_001"

SKIP_BUILD=0; SKIP_SEED=0; DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=1 ;;
    --skip-seed)  SKIP_SEED=1 ;;
    --dry-run)    DRY_RUN=1 ;;
    *) echo "Flag desconocido: $arg" >&2; exit 2 ;;
  esac
done

log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
die()  { printf '\n\033[31mFATAL: %s\033[0m\n' "$1" >&2; exit 1; }
run()  { if [ "${DRY_RUN}" -eq 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

dc() { docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" "$@"; }

# ── Pre-flight ───────────────────────────────────────────────────────────────
log "Pre-flight"
command -v docker >/dev/null 2>&1 || die "docker no instalado"
docker compose version >/dev/null 2>&1 || die "'docker compose' v2 no disponible"

if [ ! -f "${ENV_FILE}" ]; then
  die "${ENV_FILE} no existe. Generar con: bash scripts/generate-prod-secrets.sh
       (Tarea B) y rellenar ANTHROPIC_API_KEY/SMTP/dominio. Ver runbook §1."
fi
if [ ! -f "${COMPOSE_FILE}" ]; then
  die "${COMPOSE_FILE} no existe (compose de producción · Tarea A)."
fi
ok "docker + compose · ${ENV_FILE} y ${COMPOSE_FILE} presentes"

# Sanity de secretos mínimos (no imprime valores). Lee del .env.prod.
get_env() { grep -E "^${1}=" "${ENV_FILE}" 2>/dev/null | head -1 | cut -d= -f2- ; }
for v in APP_SECRET_KEY POSTGRES_PASSWORD ANTHROPIC_API_KEY \
         FULKRO_AUTH_PRIVATE_KEY BACKUP_ENCRYPTION_KEY MINIO_ROOT_PASSWORD; do
  val="$(get_env "${v}")"
  # Quita comillas envolventes para evaluar vacío real.
  val="${val%\"}"; val="${val#\"}"
  if [ -z "${val}" ]; then
    die "Variable obligatoria vacía en ${ENV_FILE}: ${v}"
  fi
done
ok "secretos mínimos presentes en ${ENV_FILE}"

# Avisa (no bloquea) de placeholders sin rellenar.
if grep -qE 'CHANGE_?ME|REPLACE_?ME|sk-ant-api03-XXXXX' "${ENV_FILE}" 2>/dev/null; then
  echo "  ⚠ ${ENV_FILE} contiene placeholders sin rellenar (CHANGEME/XXXXX) · revisar antes de prod"
fi

# Valida que el compose parsea con este env (detecta vars :? requeridas vacías).
if [ "${DRY_RUN}" -eq 0 ]; then
  dc config -q || die "docker compose config inválido con ${ENV_FILE} (¿faltan vars requeridas?)"
  ok "compose válido con ${ENV_FILE}"
fi

# ── 2 · Build ────────────────────────────────────────────────────────────────
if [ "${SKIP_BUILD}" -eq 0 ]; then
  log "2 · Build de imágenes (backend + frontend + postgres)"
  run dc build
  ok "imágenes construidas"
else
  log "2 · Build OMITIDO (--skip-build)"
fi

# ── 3 · Postgres + healthy ───────────────────────────────────────────────────
log "3 · Arrancar PostgreSQL y esperar healthy"
run dc up -d "${PG_SERVICE}"
if [ "${DRY_RUN}" -eq 0 ]; then
  for i in $(seq 1 60); do
    if dc exec -T "${PG_SERVICE}" pg_isready -U fulkro >/dev/null 2>&1; then break; fi
    sleep 2
    [ "$i" -eq 60 ] && die "PostgreSQL no llegó a aceptar conexiones en 120s"
  done
fi
ok "PostgreSQL acepta conexiones"

# ── 4 · Provisión (servicio one-shot · orden inviolable + R6) ────────────────
log "4 · Provisión (servicio 'provision' · orden inviolable · esperado head ${ALEMBIC_EXPECTED_HEAD})"
echo "      init-roles → alembic upgrade head → seed → REVOKE audit_log (R6) · idempotente"
if dc config --services 2>/dev/null | grep -qx 'provision'; then
  SEED_OVERRIDE=()
  if [ "${SKIP_SEED}" -eq 1 ]; then
    # Forzamos flags de seed conservadores que NO recargan catálogos pesados.
    SEED_OVERRIDE=(-e PROVISION_SEED_FLAGS="--skip-corpus --skip-age-kg --skip-clients")
    echo "      (--skip-seed · PROVISION_SEED_FLAGS conservador)"
  fi
  run dc run --rm "${SEED_OVERRIDE[@]}" provision
  ok "provision completado (esquema + roles endurecidos + seed + audit_log append-only)"
else
  die "el compose no define el servicio 'provision' (lo aporta la Tarea A)."
fi

# ── 5 · MinIO + buckets (incl. WORM Object Lock) ─────────────────────────────
log "5 · MinIO + bootstrap de buckets (incl. fulkro-evidence-worm WORM 7y)"
if dc config --services 2>/dev/null | grep -qx 'minio'; then
  run dc up -d minio
  if [ "${DRY_RUN}" -eq 0 ]; then
    for i in $(seq 1 30); do
      dc exec -T minio mc ready local >/dev/null 2>&1 && break
      curl -fsS "http://localhost:9000/minio/health/live" >/dev/null 2>&1 && break
      sleep 2
    done
  fi
  if dc config --services 2>/dev/null | grep -qx 'minio-init'; then
    run dc run --rm minio-init
    ok "buckets provisionados vía servicio 'minio-init' (WORM Object Lock incluido)"
  else
    echo "      (servicio 'minio-init' ausente · fallback manual:"
    echo "       bash scripts/provision-minio-buckets.sh)"
  fi
else
  echo "      (sin servicio minio en el compose · ¿Object Storage Hetzner externo?"
  echo "       provisionar buckets a mano · ver scripts/provision-minio-buckets.sh)"
fi

# ── 6 · Up de todo ───────────────────────────────────────────────────────────
log "6 · docker compose up -d (todos los servicios)"
run dc up -d
ok "servicios arrancados"

# ── 7 · Esperar healthy ──────────────────────────────────────────────────────
log "7 · Esperar a que los servicios estén healthy"
if [ "${DRY_RUN}" -eq 0 ]; then
  for i in $(seq 1 90); do
    bad="$(dc ps -a --format '{{.Name}} {{.Health}}' 2>/dev/null | awk '$2=="unhealthy" || $2=="starting" {print $1}' | tr '\n' ' ')"
    [ -z "${bad}" ] && break
    sleep 4
    [ "$i" -eq 90 ] && { echo "  aún no healthy tras 6 min: ${bad} (clamav/fastembed tardan en cold-start)"; break; }
  done
fi
dc ps || true

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " DEPLOY COMPLETADO. Verificar el gate (EN el servidor):"
echo "     bash scripts/verify-deploy.sh"
echo " Primer arranque · stanza pgBackRest + primer backup + restore-test:"
echo "     ver docs/deploy/HETZNER_DEPLOY_RUNBOOK.md §5"
echo "════════════════════════════════════════════════════════════════"
