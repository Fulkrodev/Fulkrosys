#!/usr/bin/env bash
# Arranca el container OpenVAS (Greenbone Community Edition) local.
#
# Primera vez: descarga imagen (~5GB) + sync feed NVT (~45-60 min pasivos).
# Tras ese tiempo, GMP queda expuesto en localhost:9390 (TLS) y Web UI en
# https://localhost:9392 (credenciales admin / fulkro_openvas_dev por
# default — se pueden sobreescribir via OPENVAS_ADMIN_PASSWORD).
#
# Uso:
#     ./backend/scripts/start_openvas_container.sh
#
# Para ejecutar un scan real desde Python:
#     export GVM_HOST=localhost
#     export GVM_PORT=9390
#     export GVM_USERNAME=admin
#     export GVM_PASSWORD=fulkro_openvas_dev
#     PYTHONPATH=. python backend/scripts/demo_s10_paso4_3_openvas.py
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/backend/mcp_servers/docker-compose.pentest.yml"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "ERROR: compose file no encontrado: ${COMPOSE_FILE}" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker no disponible en PATH." >&2
  exit 1
fi

echo ">> Arrancando container fulkro-openvas (primera vez tarda ~45-60 min)"
docker compose -f "${COMPOSE_FILE}" up -d openvas

echo ""
echo ">> Container arrancado. Estado actual:"
docker ps --filter "name=fulkro-openvas" --format "  {{.Names}}  {{.Status}}"

cat <<'EOF'

Siguientes pasos:

  1. Esperar sync NVT (primera vez ~45-60 min). Ver progreso:
         docker logs -f fulkro-openvas | head -80

  2. Web UI:
         https://localhost:9392
         user: admin
         pass: fulkro_openvas_dev    (o $OPENVAS_ADMIN_PASSWORD)

  3. Variables de entorno para modo real del runner FULKRO:
         export GVM_HOST=localhost
         export GVM_PORT=9390
         export GVM_USERNAME=admin
         export GVM_PASSWORD=fulkro_openvas_dev

  4. Verificar feed listo:
         docker exec fulkro-openvas greenbone-feed-sync --type GVMD_DATA

  5. Ejecutar demo Python (solo cuando feed listo):
         PYTHONPATH=. python backend/scripts/demo_s10_paso4_3_openvas.py

Stop:
    docker compose -f backend/mcp_servers/docker-compose.pentest.yml stop openvas

Destroy (conserva volumen openvas-data):
    docker compose -f backend/mcp_servers/docker-compose.pentest.yml down

Reset completo (borra feed descargado):
    docker compose -f backend/mcp_servers/docker-compose.pentest.yml down -v
EOF
