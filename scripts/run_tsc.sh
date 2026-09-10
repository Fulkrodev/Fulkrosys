#!/bin/bash
# Dev helper · ejecuta tsc con un PATH saneado (escapa los paréntesis del PATH de
# Windows cuando se trabaja bajo WSL con interop activado).
#
# Reconstruir el PATH de cero es el workaround y se mantiene. Lo que ya NO se
# cablea es la ruta del node de una máquina concreta: se prueban candidatos por
# orden y se coge el primero que tenga un npx ejecutable:
#   1. $FULKRO_NODE_BIN              (override explícito: directorio bin de node)
#   2. el directorio del `node` activo en el PATH actual (el de nvm si lo hay)
#   3. el node más reciente instalado por nvm en ${NVM_DIR:-$HOME/.nvm}
#   4. /usr/bin
# Uso: bash scripts/run_tsc.sh [args de tsc]
set -uo pipefail

_candidates=()
[ -n "${FULKRO_NODE_BIN:-}" ] && _candidates+=("${FULKRO_NODE_BIN}")

_node="$(command -v node 2>/dev/null || true)"
[ -n "${_node}" ] && _candidates+=("$(dirname "${_node}")")

# `ls -d` + `sort -V`: la versión mayor instalada por nvm, si hay alguna.
_nvm_bin="$(ls -d "${NVM_DIR:-$HOME/.nvm}"/versions/node/*/bin 2>/dev/null | sort -V | tail -n1)"
[ -n "${_nvm_bin}" ] && _candidates+=("${_nvm_bin}")

_candidates+=("/usr/bin")

NODE_BIN=""
for _c in "${_candidates[@]}"; do
  if [ -x "${_c}/npx" ]; then NODE_BIN="${_c}"; break; fi
done

if [ -z "${NODE_BIN}" ]; then
  echo "ERROR: no encuentro un npx ejecutable. Candidatos probados:" >&2
  printf '  %s\n' "${_candidates[@]}" >&2
  echo "Instala Node 20+ o exporta FULKRO_NODE_BIN=/ruta/al/bin/de/node" >&2
  exit 1
fi

PATH="${NODE_BIN}:/usr/bin:/bin"
export PATH

cd "$(dirname "${BASH_SOURCE[0]}")/../frontend" || exit 1
exec "${NODE_BIN}/npx" tsc --noEmit "$@"
