#!/usr/bin/env bash
# Start FULKRO frontend production build
# Auto-build si .next missing · paridad start_backend.sh ops
set -euo pipefail

cd "$(dirname "$0")/frontend"

# Verify .env exists con FULKRO_AUTH_PUBLIC_KEY (middleware JWT verify)
if [ ! -f ".env" ]; then
    echo "FATAL: frontend/.env NOT found"
    exit 1
fi
if ! grep -q "^FULKRO_AUTH_PUBLIC_KEY=" .env; then
    echo "FATAL: FULKRO_AUTH_PUBLIC_KEY NOT in frontend/.env"
    exit 1
fi

# Auto-build si .next missing o BUILD_ID ausente
if [ ! -f ".next/BUILD_ID" ]; then
    echo "Building production frontend (NO existing build)..."
    pnpm build
fi

exec pnpm start --port 3000 "$@"
