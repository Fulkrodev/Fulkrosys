#!/usr/bin/env bash
# Start FULKRO backend production-grade · Ed25519 keys persistentes
# Bug #6 fix: uvicorn --env-file (carga .env antes de import crypto)
# Ver progress/MB6_ATOM_02_FIRMAS_HUB_2026_05_11.md · Issue colateral
set -euo pipefail

cd "$(dirname "$0")/backend"

# Verify .env exists
if [ ! -f "../.env" ]; then
    echo "FATAL: ../.env NOT found · run scripts/generate_dev_signing_keys.py"
    exit 1
fi

# Verify critical keys present (sin imprimir el valor)
for var in FULKRO_AUTH_PRIVATE_KEY FULKRO_ML_PRIVATE_KEY FULKRO_BACKUP_SIGNING_KEY DATABASE_MIGRATE_URL; do
    if ! grep -q "^${var}=" ../.env; then
        echo "FATAL: ${var} NOT in .env · run scripts/generate_dev_signing_keys.py"
        exit 1
    fi
done

# Activate venv si existe (paridad con dev convention)
if [ -f "../.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source ../.venv/bin/activate
fi

# PYTHONPATH para import backend.app.main
export PYTHONPATH="$(cd ..; pwd)"

exec uvicorn backend.app.main:app \
    --env-file ../.env \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    "$@"
