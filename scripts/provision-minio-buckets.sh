#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# FULKRO · provision-minio-buckets.sh · crea los buckets MinIO/Object Storage
# ════════════════════════════════════════════════════════════════════════════
# Crea los buckets que la app NO auto-crea (el SDK Python no puede habilitar
# Object Lock, que SÓLO se activa al CREAR el bucket). Idempotente.
#
# Buckets (ver backend/app/core/storage/minio_client.py):
#   fulkro-documents        files de cliente
#   fulkro-evidence         evidencias estándar
#   fulkro-evidence-worm    evidencias WORM · Object Lock COMPLIANCE 7 años (R6/ENAC)
#   fulkro-exports          exports
#   fulkro-admin-assets     assets admin (public read · lo aplica la app)
#   fulkro-corpus           corpus normativo (signed-url only)
#   backup-vault-fulkro     vault offsite cifrado (m26)
#
# Frontera honesta: Hetzner-only en práctica (corre contra el MinIO/Object
# Storage de producción). Localmente puede correr contra el MinIO dev, pero el
# bucket WORM con Object Lock requiere que el servidor MinIO tenga versioning +
# object-lock habilitados (MinIO los soporta; algunos S3 gateway no).
#
# Uso:
#   MINIO_URL=http://minio:9000 MINIO_ROOT_USER=... MINIO_ROOT_PASSWORD=... \
#     bash scripts/provision-minio-buckets.sh
#
# Variables:
#   MINIO_URL            endpoint S3 (default http://localhost:9000)
#   MINIO_ROOT_USER      access key admin (default fulkro)
#   MINIO_ROOT_PASSWORD  secret key admin (default changeme123)
#   MINIO_ALIAS          alias mc a configurar (default fulkroprov)
#   WORM_RETENTION       retención WORM (default 7y)
#   FULKRO_MC_VIA        'host' (mc en PATH) | 'docker:<container>' (mc dentro)
# ════════════════════════════════════════════════════════════════════════════
set -uo pipefail

MINIO_URL="${MINIO_URL:-http://localhost:9000}"
ROOT_USER="${MINIO_ROOT_USER:-fulkro}"
ROOT_PW="${MINIO_ROOT_PASSWORD:-changeme123}"
ALIAS="${MINIO_ALIAS:-fulkroprov}"
WORM_RETENTION="${WORM_RETENTION:-7y}"
VIA="${FULKRO_MC_VIA:-host}"

mc() {
  case "${VIA}" in
    host) command mc "$@" ;;
    docker:*) docker exec -i "${VIA#docker:}" mc "$@" ;;
    *) echo "FULKRO_MC_VIA inválido: ${VIA}" >&2; return 2 ;;
  esac
}

ok() { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

echo "==> Configurando alias mc '${ALIAS}' → ${MINIO_URL}"
mc alias set "${ALIAS}" "${MINIO_URL}" "${ROOT_USER}" "${ROOT_PW}" --api S3v4 >/dev/null 2>&1 \
  && ok "alias configurado" || { echo "FATAL: no se pudo configurar alias mc"; exit 1; }

# Buckets normales (sin object-lock)
for b in fulkro-documents fulkro-evidence fulkro-exports fulkro-admin-assets fulkro-corpus backup-vault-fulkro; do
  if mc ls "${ALIAS}/${b}" >/dev/null 2>&1; then
    ok "${b} ya existe"
  else
    mc mb "${ALIAS}/${b}" >/dev/null 2>&1 && ok "${b} creado" || warn "${b} no se pudo crear"
  fi
done

# Bucket WORM · Object Lock SÓLO al crear (mc mb --with-lock)
echo "==> Bucket WORM fulkro-evidence-worm (Object Lock · COMPLIANCE ${WORM_RETENTION})"
if mc ls "${ALIAS}/fulkro-evidence-worm" >/dev/null 2>&1; then
  ok "fulkro-evidence-worm ya existe (Object Lock NO modificable post-creación)"
else
  if mc mb --with-lock "${ALIAS}/fulkro-evidence-worm" >/dev/null 2>&1; then
    ok "fulkro-evidence-worm creado con Object Lock"
  else
    warn "no se pudo crear con --with-lock (¿servidor sin versioning/object-lock?)"
  fi
fi
# Retención por defecto modo COMPLIANCE (inmutable incluso para admin · ENAC/R6)
if mc retention set --default compliance "${WORM_RETENTION}" "${ALIAS}/fulkro-evidence-worm" >/dev/null 2>&1; then
  ok "retención COMPLIANCE ${WORM_RETENTION} aplicada"
else
  warn "no se pudo aplicar retención (el bucket debe tener Object Lock activo)"
fi

echo ""
echo "==> Verificación"
mc retention info "${ALIAS}/fulkro-evidence-worm" 2>/dev/null || warn "retention info no disponible"
echo "==> Buckets provisionados."
