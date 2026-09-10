#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Levanta una "maquina limpia" para verificar instalabilidad SIN el estado del
# checkout local: Ubuntu 24.04 con su PROPIO demonio Docker (aislado del
# anfitrion), git y curl. El repositorio entra por git clone desde GitHub.
#
# /var/lib/docker va sobre un VOLUMEN real y no sobre el overlay del contenedor:
# sin eso, el docker interno falla al construir imagenes con
# "failed to convert whiteout file: operation not permitted", que es un artefacto
# del arnes y no un fallo del repositorio. Ver docs/INSTALL_TRACE.md.
#
#   bash scripts/maquina_limpia_up.sh fulkro-limpia
#   docker cp scripts/traza_instalacion_limpia.sh fulkro-limpia:/t.sh
#   docker exec fulkro-limpia bash /t.sh && docker exec fulkro-limpia cat /trace3.log
# ─────────────────────────────────────────────────────────────────────────────
# Levanta una "maquina limpia": Ubuntu 24.04 con su PROPIO demonio Docker (dind)
# aislado del host, mas git y curl. Nada del checkout local entra aqui: el repo
# se clona desde GitHub. Uso: clean_machine_up.sh <nombre>
set -euo pipefail
NAME="${1:-fulkro-limpia}"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker volume create "${NAME}-docker" >/dev/null; docker run -d --privileged --name "$NAME" -v "${NAME}-docker":/var/lib/docker \
  -e DOCKER_TLS_CERTDIR= \
  ubuntu:24.04 sleep infinity >/dev/null
docker exec "$NAME" bash -lc '
set -eux
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  ca-certificates curl gnupg git iptables uidmap >/dev/null
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y -qq docker-ce-cli docker-ce containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
'
# arranca el demonio dentro del contenedor
docker exec -d "$NAME" bash -lc 'dockerd --host=unix:///var/run/docker.sock > /var/log/dockerd.log 2>&1'
for i in $(seq 1 60); do
  if docker exec "$NAME" docker info >/dev/null 2>&1; then echo "dind listo (intento $i)"; break; fi
  [ "$i" = 60 ] && { echo "ERROR: dockerd no arranco"; docker exec "$NAME" tail -30 /var/log/dockerd.log; exit 1; }
  sleep 2
done
docker exec "$NAME" bash -lc 'echo "--- versiones de la maquina limpia ---"; . /etc/os-release; echo "os=$PRETTY_NAME"; git --version; docker --version; docker compose version; python3 --version 2>/dev/null || echo "python3: NO INSTALADO"; free -m | head -2; df -h / | tail -1; nproc'
