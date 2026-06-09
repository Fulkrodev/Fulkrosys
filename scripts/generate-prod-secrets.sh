#!/usr/bin/env bash
# =============================================================================
# FULKRO — Generador de SECRETOS DE PRODUCCIÓN (Hetzner deploy).
#
# Genera claves FRESCAS de producción y las escribe a .env.prod (modo 600,
# gitignored). NO toca el .env de desarrollo ni el de batch2 — son entornos
# distintos. Las claves DEV se rotan al final del proceso de deploy, no aquí.
#
# Vars secretas generadas:
#   - FULKRO_AUTH_PRIVATE_KEY     Ed25519 PEM PKCS8 (firma JWT session post-MFA)
#   - FULKRO_AUTH_PUBLIC_KEY      Ed25519 PEM SPKI · DERIVADA de la private
#                                 (frontend middleware JWT verify · OPS-052 72ª)
#   - FULKRO_ML_PRIVATE_KEY       Ed25519 PEM PKCS8 (magic links + signing intents M12/M25)
#   - FULKRO_BACKUP_SIGNING_KEY   Ed25519 PEM PKCS8 (M25/M26 backup manifest signing)
#   - APP_SECRET_KEY              random urlsafe 48 bytes (Fernet OAuth m16 + SSH pentest m08)
#   - POSTGRES_PASSWORD           contraseña rol fulkro (superuser migraciones+seeds)
#   - FULKRO_APP_DB_PASSWORD      contraseña rol fulkro_app (runtime app · RLS)
#   - FULKRO_MIGRATE_DB_PASSWORD  contraseña rol fulkro_migrate (Alembic prod)
#   - MINIO_ROOT_USER             usuario root MinIO (access key)
#   - MINIO_ROOT_PASSWORD         password root MinIO (secret key)
#   - BACKUP_ENCRYPTION_KEY       random urlsafe 48 bytes (Fernet AES backups M26)
#   - BACKUP_S3_ACCESS_KEY        access key Hetzner Object Storage (offsite backups)
#   - BACKUP_S3_SECRET_KEY        secret key Hetzner Object Storage
#
# Las DATABASE_URL* + MINIO_* se componen a partir de las passwords + user.
#
# Vars NO generadas (las pone Marcos · ver .env.prod.template):
#   ANTHROPIC_API_KEY · APP_BASE_URL/ALLOWED_HOSTS/WEBAUTHN_RP_* (dominio) · SMTP_*
#
# Uso:
#   ./scripts/generate-prod-secrets.sh                 # idempotente · NO sobrescribe si existe
#   ./scripts/generate-prod-secrets.sh --force         # regenera TODO (INVALIDA firmas/sesiones)
#   ./scripts/generate-prod-secrets.sh --out .env.prod.throwaway   # destino alternativo (validación)
#
# REQUISITO CRÍTICO (OPS-052 72ª): la FULKRO_AUTH_PUBLIC_KEY que consume el
# build del frontend de prod DEBE ser la pareja exacta de la
# FULKRO_AUTH_PRIVATE_KEY del backend. Este script la DERIVA de la private
# generada, garantizando el match. Si se desincronizan, jwtVerify falla y el
# portal cliente entra en bucle de login. El build del frontend toma esa
# public como build-arg/env (FULKRO_AUTH_PUBLIC_KEY).
# =============================================================================
set -euo pipefail

FORCE=0
OUT_FILE=".env.prod"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    --out) OUT_FILE="$2"; shift 2 ;;
    --out=*) OUT_FILE="${1#--out=}"; shift ;;
    -h|--help)
      sed -n '2,46p' "$0"; exit 0 ;;
    *) echo "ERROR: argumento desconocido: $1" >&2; exit 2 ;;
  esac
done

# Resolver repo root (este script vive en scripts/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# Resolver intérprete python (.venv si existe).
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PY="${REPO_ROOT}/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python || true)"
fi
if [[ -z "${PY}" ]]; then
  echo "ERROR: python no encontrado · necesario para generar claves Ed25519." >&2
  exit 1
fi
if ! "${PY}" -c "import cryptography" 2>/dev/null; then
  echo "ERROR: paquete 'cryptography' no instalado en ${PY}." >&2
  echo "       Activa el venv: source .venv/bin/activate" >&2
  exit 1
fi

# Guard de seguridad: NUNCA escribir sobre los .env de dev.
case "${OUT_FILE}" in
  .env|./.env|"${REPO_ROOT}/.env"|frontend/.env|frontend/.env.local)
    echo "ERROR: ${OUT_FILE} es un fichero de DEV · este script NO lo toca." >&2
    echo "       Destino válido: .env.prod (default) o .env.prod.*" >&2
    exit 2 ;;
esac

if [[ -f "${OUT_FILE}" && "${FORCE}" -eq 0 ]]; then
  echo "✓ ${OUT_FILE} ya existe · NO sobrescribo (idempotente)."
  echo "  Para regenerar TODO (invalida sesiones/firmas existentes): --force"
  exit 0
fi

echo "=== FULKRO · generación de secretos de PRODUCCIÓN ==="
echo "Destino: ${REPO_ROOT}/${OUT_FILE}"
[[ "${FORCE}" -eq 1 ]] && echo "Modo: --force (regenera TODO)"
echo

# -----------------------------------------------------------------------------
# Toda la generación criptográfica ocurre en un único proceso Python que
# emite líneas KEY=VALUE. La AUTH_PUBLIC se DERIVA de la AUTH_PRIVATE recién
# generada en el MISMO proceso · match garantizado.
# -----------------------------------------------------------------------------
GENERATED="$("${PY}" - <<'PYEOF'
import base64
import secrets

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def ed25519_pair():
    """Devuelve (private_pem, public_pem) · mismo formato que crypto.py."""
    priv = Ed25519PrivateKey.generate()
    private_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii").strip()
    public_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii").strip()
    return private_pem, public_pem


def emit_multiline(key: str, value: str) -> None:
    # Multi-line PEM entre comillas dobles · compat python-dotenv + middleware.
    print(f'{key}="{value}"')


def emit(key: str, value: str) -> None:
    print(f"{key}={value}")


# --- 1. AUTH keypair (private + public DERIVADA · OPS-052 72ª) ---
auth_priv, auth_pub = ed25519_pair()
emit_multiline("FULKRO_AUTH_PRIVATE_KEY", auth_priv)
emit_multiline("FULKRO_AUTH_PUBLIC_KEY", auth_pub)

# --- 2. ML + BACKUP signing keys (Ed25519) ---
ml_priv, _ = ed25519_pair()
emit_multiline("FULKRO_ML_PRIVATE_KEY", ml_priv)
backup_priv, _ = ed25519_pair()
emit_multiline("FULKRO_BACKUP_SIGNING_KEY", backup_priv)

# --- 2.bis. Claves de firma documental/evidencia M05/M06/M07 (Ed25519) ---
# FIX P0-1: antes los 3 motores autogeneraban su clave en var/keys/ si faltaba;
# sin volumen persistente en Hetzner cada recreate rotaba la clave e invalidaba
# toda firma previa (contratos, dossier ENAC, evidencias). Ahora se inyectan
# estables por env (una sola vez aquí). Cada motor deriva su pública en memoria.
m05_priv, _ = ed25519_pair()
emit_multiline("FULKRO_M05_SIGNING_PRIVATE_KEY", m05_priv)
m06_priv, _ = ed25519_pair()
emit_multiline("FULKRO_M06_SIGNING_PRIVATE_KEY", m06_priv)
m07_priv, _ = ed25519_pair()
emit_multiline("FULKRO_M07_SIGNING_PRIVATE_KEY", m07_priv)

# --- 3. Secretos de aplicación (random) ---
emit("APP_SECRET_KEY", secrets.token_urlsafe(48))
emit("BACKUP_ENCRYPTION_KEY", secrets.token_urlsafe(48))

# --- 4. Passwords de roles PostgreSQL ---
# alfanumérico (sin símbolos) · evita escaping en DATABASE_URL.
def db_password() -> str:
    return secrets.token_hex(24)  # 48 hex chars · sin chars problemáticos en URL

emit("POSTGRES_PASSWORD", db_password())
emit("FULKRO_APP_DB_PASSWORD", db_password())
emit("FULKRO_MIGRATE_DB_PASSWORD", db_password())

# --- 5. Credenciales MinIO root ---
emit("MINIO_ROOT_USER", "fulkro_prod_" + secrets.token_hex(4))
emit("MINIO_ROOT_PASSWORD", secrets.token_urlsafe(36))

# --- 5.bis. Password Redis (broker Celery · FIX P3-1) ---
emit("REDIS_PASSWORD", secrets.token_hex(24))  # hex · sin chars problemáticos en URL

# --- 6. Credenciales backup S3 (Hetzner Object Storage offsite) ---
# Placeholders FRESCOS · Marcos los reemplaza con las keys reales que le dé
# Hetzner al crear el bucket. Generamos algo para que el fichero esté completo.
emit("BACKUP_S3_ACCESS_KEY", "REPLACE_WITH_HETZNER_OBJSTORE_ACCESS_KEY")
emit("BACKUP_S3_SECRET_KEY", "REPLACE_WITH_HETZNER_OBJSTORE_SECRET_KEY")
PYEOF
)"

# -----------------------------------------------------------------------------
# Parsear las KEY=VALUE generadas a un mapa asociativo (respeta multi-line PEM).
# -----------------------------------------------------------------------------
declare -A SECRETS
declare -a SECRET_ORDER
current_key=""
current_val=""
in_multiline=0
while IFS= read -r line; do
  if [[ "${in_multiline}" -eq 1 ]]; then
    current_val+=$'\n'"${line}"
    if [[ "${line}" == *'"' ]]; then
      SECRETS["${current_key}"]="${current_val}"
      SECRET_ORDER+=("${current_key}")
      in_multiline=0
      current_key=""; current_val=""
    fi
    continue
  fi
  [[ -z "${line}" ]] && continue
  key="${line%%=*}"
  val="${line#*=}"
  if [[ "${val}" == '"'* && "${val}" != *'"' ]]; then
    # Inicio de valor multi-línea (PEM).
    current_key="${key}"
    current_val="${val}"
    in_multiline=1
  else
    SECRETS["${key}"]="${val}"
    SECRET_ORDER+=("${key}")
  fi
done <<< "${GENERATED}"

# -----------------------------------------------------------------------------
# Componer DATABASE_URL* y MINIO_* a partir de las passwords/users generados.
# Host/puerto/bucket apuntan a los nombres de servicio del compose de prod.
# -----------------------------------------------------------------------------
PG_HOST="postgres"
PG_PORT="5432"
PG_DB="fulkro"
APP_PW="${SECRETS[FULKRO_APP_DB_PASSWORD]}"
MIG_PW="${SECRETS[FULKRO_MIGRATE_DB_PASSWORD]}"
MINIO_USER="${SECRETS[MINIO_ROOT_USER]}"
MINIO_PW="${SECRETS[MINIO_ROOT_PASSWORD]}"

DATABASE_URL="postgresql+asyncpg://fulkro_app:${APP_PW}@${PG_HOST}:${PG_PORT}/${PG_DB}"
DATABASE_URL_SYNC="postgresql://fulkro_app:${APP_PW}@${PG_HOST}:${PG_PORT}/${PG_DB}"
DATABASE_MIGRATE_URL="postgresql://fulkro_migrate:${MIG_PW}@${PG_HOST}:${PG_PORT}/${PG_DB}"

# -----------------------------------------------------------------------------
# Escribir el fichero .env.prod. Sección 1 = secretos generados. El resto de
# vars (dominio, SMTP, ANTHROPIC) las añade Marcos copiando del template.
# -----------------------------------------------------------------------------
umask 077  # el fichero nacerá 600
TMP_OUT="$(mktemp "${OUT_FILE}.XXXXXX.tmp")"
trap 'rm -f "${TMP_OUT}"' EXIT

{
  echo "# ============================================================================="
  echo "# FULKRO · .env.prod — SECRETOS DE PRODUCCIÓN (generado $(date -u +%Y-%m-%dT%H:%M:%SZ))"
  echo "# GENERADO POR scripts/generate-prod-secrets.sh · NO COMMIT (gitignored, modo 600)"
  echo "#"
  echo "# Las vars de esta sección son SECRETOS generados criptográficamente."
  echo "# Las vars 'TUYAS' (ANTHROPIC_API_KEY, dominio, SMTP) se rellenan abajo a mano"
  echo "# copiando de .env.prod.template. Ver ese fichero para la lista completa."
  echo "# ============================================================================="
  echo

  echo "# --- Entorno ---"
  echo "APP_ENV=production"
  echo

  echo "# --- Claves Ed25519 (firma JWT / magic-links / backups / docs+evidencia) ---"
  echo "# FULKRO_AUTH_PUBLIC_KEY es la pareja DERIVADA de FULKRO_AUTH_PRIVATE_KEY."
  echo "# El build del frontend la toma como build-arg/env (OPS-052 72ª)."
  echo "# M05/M06/M07: firma de contratos, documentos y evidencias (FIX P0-1 ·"
  echo "# estables cross-recreate · antes efímeras en var/keys → invalidaban firmas)."
  for k in FULKRO_AUTH_PRIVATE_KEY FULKRO_AUTH_PUBLIC_KEY FULKRO_ML_PRIVATE_KEY FULKRO_BACKUP_SIGNING_KEY FULKRO_M05_SIGNING_PRIVATE_KEY FULKRO_M06_SIGNING_PRIVATE_KEY FULKRO_M07_SIGNING_PRIVATE_KEY; do
    echo "${k}=${SECRETS[$k]}"
  done
  echo

  echo "# --- Secretos de aplicación ---"
  echo "APP_SECRET_KEY=${SECRETS[APP_SECRET_KEY]}"
  echo "BACKUP_ENCRYPTION_KEY=${SECRETS[BACKUP_ENCRYPTION_KEY]}"
  echo

  echo "# --- PostgreSQL · passwords de roles (consumidas por init-roles.sql + compose) ---"
  echo "POSTGRES_PASSWORD=${SECRETS[POSTGRES_PASSWORD]}"
  echo "FULKRO_APP_DB_PASSWORD=${APP_PW}"
  echo "FULKRO_MIGRATE_DB_PASSWORD=${MIG_PW}"
  echo "# URLs compuestas (host=service '${PG_HOST}' del compose de prod):"
  echo "DATABASE_URL=${DATABASE_URL}"
  echo "DATABASE_URL_SYNC=${DATABASE_URL_SYNC}"
  echo "DATABASE_MIGRATE_URL=${DATABASE_MIGRATE_URL}"
  echo

  echo "# --- Redis (broker Celery · FIX P3-1 · password + host de servicio + var correcta) ---"
  echo "# Celery lee FULKRO_REDIS_URL/RESULT (NO REDIS_URL) · antes caía al default"
  echo "# redis://localhost (host equivocado en compose) → broker inalcanzable."
  echo "REDIS_PASSWORD=${SECRETS[REDIS_PASSWORD]}"
  echo "REDIS_URL=redis://:${SECRETS[REDIS_PASSWORD]}@redis:6379/0"
  echo "FULKRO_REDIS_URL=redis://:${SECRETS[REDIS_PASSWORD]}@redis:6379/1"
  echo "FULKRO_REDIS_RESULT_URL=redis://:${SECRETS[REDIS_PASSWORD]}@redis:6379/2"
  echo

  echo "# --- MinIO (object storage local) ---"
  echo "MINIO_ROOT_USER=${MINIO_USER}"
  echo "MINIO_ROOT_PASSWORD=${MINIO_PW}"
  echo "MINIO_ENDPOINT=minio:9000"
  echo "MINIO_ACCESS_KEY=${MINIO_USER}"
  echo "MINIO_SECRET_KEY=${MINIO_PW}"
  echo "MINIO_BUCKET=fulkro"
  echo

  echo "# --- Backup offsite S3 (Hetzner Object Storage) ---"
  echo "# Reemplaza las 2 keys con las reales que te dé Hetzner al crear el bucket."
  echo "BACKUP_S3_ACCESS_KEY=${SECRETS[BACKUP_S3_ACCESS_KEY]}"
  echo "BACKUP_S3_SECRET_KEY=${SECRETS[BACKUP_S3_SECRET_KEY]}"
  echo "BACKUP_S3_ENDPOINT=https://nbg1.your-objectstorage.com"
  echo "BACKUP_S3_BUCKET=backup-vault-fulkro"
  echo "PGBACKREST_STANZA=fulkro-prod"
  echo

  echo "# ============================================================================="
  echo "# VARS 'TUYAS' (Marcos) — RELLENAR A MANO antes del deploy."
  echo "# Copiadas de .env.prod.template con placeholders. Sin estas, el deploy NO"
  echo "# es funcional (LLM copiloto, dominio TLS, emails)."
  echo "# ============================================================================="
  echo "ANTHROPIC_API_KEY=sk-ant-api03-REPLACE_ME"
  echo "ANTHROPIC_DEFAULT_MODEL=claude-sonnet-4-5"
  echo "ANTHROPIC_FALLBACK_MODEL=claude-opus-4-6"
  echo
  echo "APP_BASE_URL=https://app.fulkro.es"
  echo "ALLOWED_HOSTS=app.fulkro.es"
  echo "WEBAUTHN_RP_ID=app.fulkro.es"
  echo "WEBAUTHN_RP_NAME=FULKRO"
  echo
  echo "SMTP_HOST=smtp.REPLACE_ME"
  echo "SMTP_PORT=587"
  echo "SMTP_USER=REPLACE_ME"
  echo "SMTP_PASSWORD=REPLACE_ME"
  echo "SMTP_FROM=no-reply@fulkro.es"
  echo
  echo "EMBEDDINGS_MODEL=intfloat/multilingual-e5-large"
  echo "EMBEDDINGS_ENDPOINT=http://fastembed:8080"
} > "${TMP_OUT}"

chmod 600 "${TMP_OUT}"
mv -f "${TMP_OUT}" "${OUT_FILE}"
chmod 600 "${OUT_FILE}"
trap - EXIT

# -----------------------------------------------------------------------------
# Reporte: QUÉ se generó (nombres de vars · NUNCA valores).
# -----------------------------------------------------------------------------
echo "✓ Escrito ${OUT_FILE} (modo $(stat -c '%a' "${OUT_FILE}" 2>/dev/null || echo 600))"
echo
echo "Vars SECRETAS generadas (valores NO mostrados):"
for k in "${SECRET_ORDER[@]}"; do
  echo "  · ${k}"
done
echo "  · DATABASE_URL / DATABASE_URL_SYNC / DATABASE_MIGRATE_URL  (compuestas)"
echo "  · MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY / MINIO_BUCKET"
echo "  · REDIS_URL / BACKUP_S3_ENDPOINT / BACKUP_S3_BUCKET / PGBACKREST_STANZA"
echo
echo "Vars 'TUYAS' (Marcos) con placeholder · RELLENAR:"
echo "  · ANTHROPIC_API_KEY"
echo "  · APP_BASE_URL / ALLOWED_HOSTS / WEBAUTHN_RP_ID / WEBAUTHN_RP_NAME"
echo "  · SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM"
echo "  · BACKUP_S3_ACCESS_KEY / BACKUP_S3_SECRET_KEY (keys reales Hetzner)"
echo
echo "RECORDATORIO CRÍTICO (OPS-052 72ª):"
echo "  El build del frontend de prod DEBE recibir FULKRO_AUTH_PUBLIC_KEY = la"
echo "  pareja de FULKRO_AUTH_PRIVATE_KEY de este fichero. Ya está derivada y"
echo "  garantizada aquí. Pásala como build-arg/env al construir la imagen del"
echo "  frontend. Si no coincide → jwtVerify falla → portal cliente en bucle login."
echo
echo "SEGURIDAD: ${OUT_FILE} está en .gitignore · NUNCA hacer commit."
