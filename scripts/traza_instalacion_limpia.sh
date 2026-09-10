#!/usr/bin/env bash
# C0.1 v3 · maquina limpia. Sigue el README PUBLICADO en GitHub, LITERAL, incluido
# el clon con el nombre por defecto (Fulkrosys) y el sleep 30 que el texto pone.
# Cada paso: se intenta tal cual. Si falla se registra FALLO con su traza y se aplica
# el arreglo minimo que haria un usuario decidido, registrado como MANUAL.
# Los codigos de salida NUNCA pasan por una tuberia (eso enmascararia el rc).
set -u
LOG=/trace3.log; : > "$LOG"
NF=0; NM=0; NP=0
say(){ printf '%s\n' "$*" >>"$LOG"; }
run(){ local t0=$SECONDS rc
       say "\$ $1"
       eval "$1" >/tmp/step.out 2>&1; rc=$?
       tail -25 /tmp/step.out >>"$LOG"
       say "  [rc=$rc  $((SECONDS-t0))s]"
       return "$rc"; }
paso(){ NP=$((NP+1)); say ""; say "──────── PASO $NP · $1"; }
fallo(){ NF=$((NF+1)); say "  [X] FALLO F$NF: $1"; }
manual(){ NM=$((NM+1)); say "  [M] MANUAL M$NM (no esta en el README): $1"; }
ok(){ say "  [OK] $1"; }
T0=$SECONDS

cd /
paso "clonar desde GitHub con el nombre por DEFECTO"
run 'git clone --quiet https://github.com/Fulkrodev/Fulkrosys.git' && ok "clonado en /Fulkrosys" || fallo "git clone"
cd /Fulkrosys || exit 1
say "  commit publicado: $(git rev-parse --short HEAD)"
say "  el directorio se llama: $(basename "$PWD")  -> proyecto de compose: $(basename "$PWD" | tr 'A-Z' 'a-z')"

paso "README 1a · python3.12 -m venv .venv"
if run 'python3.12 -m venv .venv'; then ok "venv creado"
else fallo "python3.12 -m venv: ensurepip no disponible en Ubuntu 24.04 limpio"
     manual "apt-get install -y python3.12-venv python3-pip"
     run 'DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3.12-venv python3-pip'
     run 'python3.12 -m venv .venv' && ok "venv creado tras el paso manual" || fallo "venv sigue roto"; fi

paso "README 1b · pip install -e backend[dev]"
if run '.venv/bin/pip install -q -e "backend[dev]"'; then ok instalado
else
  fallo "pip install -e backend[dev]: mjml-python arrastra pycairo, que compila desde fuente"
  say "  --- causa exacta ---"; command grep -iE "cairo|pkg-config|CMake|meson" /tmp/step.out | head -6 >>"$LOG"
  manual "apt-get install -y pkg-config cmake libcairo2-dev python3.12-dev build-essential"
  run 'DEBIAN_FRONTEND=noninteractive apt-get install -y -qq pkg-config cmake libcairo2-dev python3.12-dev build-essential'
  if run '.venv/bin/pip install -q -e "backend[dev]"'; then ok "instalado tras el paso manual"
  else fallo "pip install sigue fallando tras instalar las dependencias de sistema"; fi
fi

paso "README 2 · docker compose up -d postgres redis minio  (+ el sleep 30 que el README pone)"
if run 'docker compose up -d postgres redis minio'; then ok "servicios arriba"; run 'sleep 30'; run 'docker compose ps --format "{{.Name}}  {{.Status}}"'
else fallo "docker compose up -d postgres redis minio"; fi

paso "README 3 · cp .env.example .env"
run 'cp .env.example .env' && ok copiado
say "  las 4 obligatorias de backend/app/startup_checks.py:"
F=0; for v in DATABASE_URL FULKRO_AUTH_PRIVATE_KEY FULKRO_ML_PRIVATE_KEY FULKRO_BACKUP_SIGNING_KEY; do
  if command grep -qE "^${v}=" .env; then say "    $v: SI"; else say "    $v: NO"; F=$((F+1)); fi; done
[ "$F" -gt 0 ] && fallo "cp .env.example .env deja $F de 4 variables obligatorias sin definir"

paso "README 4 · bash scripts/build_test_db.sh"
if run 'bash scripts/build_test_db.sh'; then ok "BD de test construida"
else fallo "build_test_db.sh"
     say "  --- CONTAINER que busca vs el que compose ha creado ---"
     say "    busca : ${FULKRO_PG_CONTAINER:-fulkro-postgres-1}  (default cableado)"
     docker ps --format '    existe: {{.Names}}' >>"$LOG"
fi

paso "README 5 · pytest --collect-only (¿recolecta sin errores de import?)"
if run 'PYTHONPATH=. .venv/bin/python -m pytest backend/tests/ --collect-only -q'; then ok "recoleccion limpia"
else fallo "la recoleccion de pytest sale con error"; fi
command grep -E "^[0-9]+ tests collected|error" /tmp/step.out | tail -3 >>"$LOG"

paso "arrancar el backend · uvicorn --env-file .env"
run 'timeout 45 .venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --env-file .env'
if command grep -qE "CriticalConfigError|criticas ausentes" /tmp/step.out; then fallo "el backend aborta en el arranque por env vars criticas ausentes"
elif command grep -qE "Uvicorn running|Application startup complete" /tmp/step.out; then ok "el backend arranca"
else fallo "el backend no arranca (motivo distinto)"; fi

paso "frontend · npm install"
if command -v npm >/dev/null 2>&1; then run 'cd frontend && npm install' && ok "npm install ok" || fallo "npm install"
else fallo "npm/node no existen en la maquina y el README no dice que haya que instalarlos"
     manual "curl -fsSL deb.nodesource.com | apt-get install -y nodejs"
     run 'curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/n.sh && bash /tmp/n.sh >/dev/null 2>&1 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs'
     if run 'cd /Fulkrosys/frontend && npm install'; then ok "npm install ok tras el paso manual"; else fallo "npm install"; fi; fi

say ""
say "════════ RESUMEN C0.1 · README publicado, maquina limpia ════════"
say "pasos ejecutados : $NP"
say "FALLOS           : $NF"
say "pasos MANUALES   : $NM"
say "tiempo total     : $((SECONDS-T0))s"
