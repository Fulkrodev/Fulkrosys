#!/bin/sh
# FULKRO — MinIO bucket bootstrap (docker-compose.prod.yml · servicio `minio-init`)
# ════════════════════════════════════════════════════════════════════════════
# Crea los buckets que el backend espera. Idempotente (mc mb --ignore-existing).
# El bucket de evidencias WORM (`fulkro-evidence-worm`) se crea CON Object Lock
# habilitado (solo posible AL CREAR el bucket) + retención COMPLIANCE 7 años
# (ENS · evidencia inmutable · R6 + ADR-043). Object Lock NO se puede activar
# sobre un bucket pre-existente → si el bucket ya existe sin lock, hay que
# recrearlo (no se hace aquí · destructivo).
#
# Buckets canónicos (backend/app/core/storage/minio_client.py):
#   fulkro-documents · fulkro-evidence · fulkro-evidence-worm (WORM 7y) ·
#   fulkro-exports · fulkro-admin-assets (public read) · fulkro-corpus ·
#   backup-vault-fulkro
# ════════════════════════════════════════════════════════════════════════════
set -eu

MC_ALIAS="fulkroprod"
MINIO_URL="${MINIO_INIT_ENDPOINT:-http://minio:9000}"
ROOT_USER="${MINIO_ROOT_USER:?MINIO_ROOT_USER requerido}"
ROOT_PW="${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD requerido}"

echo "==> esperando a MinIO en ${MINIO_URL}"
i=0
until mc alias set "${MC_ALIAS}" "${MINIO_URL}" "${ROOT_USER}" "${ROOT_PW}" >/dev/null 2>&1; do
  i=$((i+1))
  if [ "${i}" -ge 60 ]; then echo "ERROR: MinIO no respondió en 60 intentos" >&2; exit 1; fi
  sleep 2
done
echo "    alias configurado"

# Buckets normales (sin object lock)
for b in fulkro-documents fulkro-evidence fulkro-exports fulkro-corpus backup-vault-fulkro; do
  mc mb --ignore-existing "${MC_ALIAS}/${b}"
  echo "    bucket ${b} ok"
done

# Bucket admin assets · public read (logos, etc.)
mc mb --ignore-existing "${MC_ALIAS}/fulkro-admin-assets"
mc anonymous set download "${MC_ALIAS}/fulkro-admin-assets" || true
echo "    bucket fulkro-admin-assets (public download) ok"

# Bucket WORM · Object Lock SOLO se puede activar al crear el bucket.
if mc ls "${MC_ALIAS}/fulkro-evidence-worm" >/dev/null 2>&1; then
  echo "    bucket fulkro-evidence-worm ya existe (no se recrea · object lock NO modificable post-creación)"
else
  mc mb --with-lock "${MC_ALIAS}/fulkro-evidence-worm"
  # Retención COMPLIANCE 7 años (2555 días) · inmutable incluso para root (WORM real).
  mc retention set --default COMPLIANCE 2555d "${MC_ALIAS}/fulkro-evidence-worm"
  echo "    bucket fulkro-evidence-worm creado con Object Lock + COMPLIANCE 7y"
fi

echo "==> MINIO BUCKETS DONE"
mc ls "${MC_ALIAS}"
