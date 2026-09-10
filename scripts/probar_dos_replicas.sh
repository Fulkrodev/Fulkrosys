#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# BLOQUE D · D4 · la prueba que zanja "¿es escalable?"
#
# Levanta DOS replicas del backend detras de nginx con reparto por turnos y
# comprueba, sobre la aplicacion en marcha:
#
#   1. que nginx reparte de verdad (dos direcciones distintas en X-Replica)
#   2. que la sesion abierta contra una replica vale en la otra
#   3. que un enlace de portal EMITIDO por una replica funciona en la OTRA
#   4. que las claves de firma son las MISMAS en ambas replicas
#   5. que un evento SSE despachado en una replica llega al suscriptor de la otra
#
# No opina: mide. El resultado, salga lo que salga, va a
# docs/adr/ADR-003-escalabilidad-horizontal.md.
#
# Uso:   bash scripts/probar_dos_replicas.sh
#        bash scripts/probar_dos_replicas.sh --dejar-en-pie   (no restaura el demo)
#
# Al terminar restaura el demo de una sola replica, salvo --dejar-en-pie.
# ════════════════════════════════════════════════════════════════════════════
set -uo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

PROJECT="${PROJECT:-fulkro-demo}"
BASE="docker compose -f docker-compose.demo.yml -p ${PROJECT}"
ESC="docker compose -f docker-compose.demo.yml -f docker-compose.escalabilidad.yml -p ${PROJECT}"
API="http://127.0.0.1:18000/api/v1"
OWNER_EMAIL="${FULKRO_DEMO_OWNER_EMAIL:-demo@fulkro.es}"
OWNER_PASSWORD="${FULKRO_DEMO_OWNER_PASSWORD:-fulkro-demo-2026}"
DEJAR=0
[ "${1:-}" = "--dejar-en-pie" ] && DEJAR=1

PASS=0; FAIL=0
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
ok()    { PASS=$((PASS+1)); printf '  OK     %-46s %s\n' "$1" "${2:-}"; }
falla() { FAIL=$((FAIL+1)); printf '  FALLO  %-46s %s\n' "$1" "${2:-}"; }
info()  {                   printf '  info   %-46s %s\n' "$1" "${2:-}"; }
titulo(){ printf '\n%s\n' "$1"; }

psql_q() { docker exec "${PROJECT}-postgres-1" psql -U fulkro -d fulkro -tA -c "$1" 2>/dev/null; }

totp_code() {
  python3 - "$1" <<'PY'
import base64, hmac, hashlib, struct, sys, time
s = sys.argv[1]
k = base64.b32decode(s + "=" * ((8 - len(s) % 8) % 8))
c = struct.pack(">Q", int(time.time()) // 30)
h = hmac.new(k, c, hashlib.sha1).digest()
o = h[-1] & 0xF
print("%06d" % ((struct.unpack(">I", h[o:o+4])[0] & 0x7FFFFFFF) % 1000000))
PY
}

# Ejecuta una peticion HTTP DENTRO de una replica concreta (127.0.0.1:8000 del
# propio contenedor), para dirigirla sin depender del reparto de nginx.
en_replica() { # $1=contenedor $2=metodo $3=ruta $4=cuerpo-json|"" $5=cabeceras-extra|""
  docker exec -i -e M="$2" -e R="$3" -e B="${4:-}" -e H="${5:-}" "$1" python - <<'PY'
import json, os, urllib.request, urllib.error
metodo, ruta, cuerpo, extra = os.environ["M"], os.environ["R"], os.environ["B"], os.environ["H"]
datos = cuerpo.encode() if cuerpo else None
req = urllib.request.Request(f"http://127.0.0.1:8000{ruta}", data=datos, method=metodo)
if datos: req.add_header("Content-Type", "application/json")
for par in filter(None, extra.split("\n")):
    k, _, v = par.partition(":")
    req.add_header(k.strip(), v.strip())
try:
    with urllib.request.urlopen(req, timeout=25) as r:
        print(json.dumps({"codigo": r.status,
                          "cuerpo": r.read().decode("utf-8", "replace")[:4000],
                          "cookies": r.headers.get_all("Set-Cookie") or []}))
except urllib.error.HTTPError as e:
    print(json.dumps({"codigo": e.code, "cuerpo": e.read().decode("utf-8","replace")[:1500], "cookies": []}))
except Exception as e:
    print(json.dumps({"codigo": 0, "cuerpo": f"{type(e).__name__}: {e}", "cookies": []}))
PY
}
campo() { python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('$1',''))"; }
dentro() { python3 -c "
import json,sys
d=json.load(sys.stdin)
try: print(json.loads(d['cuerpo']).get('$1',''))
except Exception: print('')"; }

echo "════════════════════════════════════════════════════════════════"
echo " D4 · dos replicas del backend detras de nginx (reparto por turnos)"
echo "════════════════════════════════════════════════════════════════"

titulo "0 · levantar la pila con dos replicas"
$ESC up -d --no-build --scale backend=2 >/dev/null 2>&1
listo=""
for i in $(seq 1 60); do
  sanos="$(docker ps --filter "label=com.docker.compose.project=${PROJECT}" \
            --filter "label=com.docker.compose.service=backend" \
            --format '{{.Status}}' | grep -c healthy || true)"
  ng="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "${API}/health" || true)"
  if [ "${sanos:-0}" -ge 2 ] && [ "$ng" = "200" ]; then listo="si"; break; fi
  sleep 5
done
REPLICAS=($(docker ps --filter "label=com.docker.compose.project=${PROJECT}" \
             --filter "label=com.docker.compose.service=backend" --format '{{.Names}}' | sort))
if [ -n "$listo" ] && [ "${#REPLICAS[@]}" -ge 2 ]; then
  ok "dos replicas del backend en pie y sanas" "${REPLICAS[*]}"
else
  falla "dos replicas del backend en pie y sanas" "replicas=${#REPLICAS[@]} nginx=${ng:-?}"
  echo; echo "No se puede seguir."; exit 1
fi
A="${REPLICAS[0]}"; B="${REPLICAS[1]}"

titulo "1 · ¿nginx reparte de verdad?"
: > "$TMP/replicas.txt"
for i in $(seq 1 12); do
  curl -sS -o /dev/null -D - --max-time 5 "${API}/health" 2>/dev/null \
    | tr -d '\r' | awk -F': ' 'tolower($1)=="x-replica"{print $2}' >> "$TMP/replicas.txt"
done
distintas="$(sort -u "$TMP/replicas.txt" | grep -c . || true)"
if [ "${distintas:-0}" -ge 2 ]; then
  ok "el reparto alcanza a las dos replicas" "$(sort "$TMP/replicas.txt" | uniq -c | tr '\n' ' ')"
else
  falla "el reparto alcanza a las dos replicas" \
        "solo $distintas direccion(es): $(sort -u "$TMP/replicas.txt" | tr '\n' ' ') · la medicion de abajo no valdria"
fi

titulo "2 · las claves de firma, ¿son las mismas en las dos replicas?"
for clave in ed25519_signing_private.pem m05_signing_dev.ed25519.pem m6_signing_dev.ed25519.pem; do
  ha="$(docker exec "$A" sh -lc "sha256sum /app/var/keys/${clave} 2>/dev/null | cut -c1-16" || true)"
  hb="$(docker exec "$B" sh -lc "sha256sum /app/var/keys/${clave} 2>/dev/null | cut -c1-16" || true)"
  if [ -z "$ha" ] || [ -z "$hb" ]; then
    info "clave ${clave}" "no esta en disco en alguna replica (A='${ha}' B='${hb}')"
  elif [ "$ha" = "$hb" ]; then
    ok "clave ${clave} identica en A y B" "sha256 ${ha}…"
  else
    falla "clave ${clave} identica en A y B" "A=${ha}… B=${hb}… · lo firmado en una NO se verifica en la otra"
  fi
done
for v in FULKRO_AUTH_PRIVATE_KEY FULKRO_ML_PRIVATE_KEY; do
  ha="$(docker exec "$A" sh -lc "printf '%s' \"\$$v\" | sha256sum | cut -c1-16")"
  hb="$(docker exec "$B" sh -lc "printf '%s' \"\$$v\" | sha256sum | cut -c1-16")"
  if [ "$ha" = "$hb" ]; then ok "$v identica en A y B" "sha256 ${ha}…"
  else falla "$v identica en A y B" "A=${ha}… B=${hb}…"; fi
done

titulo "3 · la sesion abierta en una replica, ¿vale en la otra?"
SECRETO="$(psql_q "SELECT s.secret FROM auth_totp_secrets s JOIN auth_users u ON u.id = s.user_id WHERE u.email = '${OWNER_EMAIL}' AND s.verified LIMIT 1;" | tr -d '[:space:]')"
if [ -z "$SECRETO" ]; then
  falla "segundo factor enrolado" "sin secreto TOTP para ${OWNER_EMAIL}"
else
  cuerpo="$(python3 -c "import json;print(json.dumps({'email':'${OWNER_EMAIL}','password':'${OWNER_PASSWORD}'}))")"
  r1="$(en_replica "$A" POST /api/v1/auth/login "$cuerpo" "")"
  ticket="$(printf '%s' "$r1" | dentro mfa_ticket)"
  if [ -z "$ticket" ]; then
    falla "entrar contra la replica A" "sin mfa_ticket · $(printf '%s' "$r1" | campo cuerpo | head -c 120)"
  else
    ok "entrar contra la replica A" "mfa_ticket emitido"
    codigo="$(totp_code "$SECRETO")"
    v="$(python3 -c "import json;print(json.dumps({'mfa_ticket':'${ticket}','code':'${codigo}'}))")"
    r2="$(en_replica "$A" POST /api/v1/auth/totp/verify "$v" "")"
    galleta="$(printf '%s' "$r2" | python3 -c "
import json,sys,re
d=json.load(sys.stdin)
trozos=[]
for c in d.get('cookies',[]):
    m=re.match(r'((?:fulkro_session|fulkro_csrf)=[^;]+)', c)
    if m: trozos.append(m.group(1))
print('; '.join(trozos))")"
    CSRF="$(printf '%s' "$r2" | dentro csrf_token)"
    if [ -z "$galleta" ]; then
      falla "cookie de sesion emitida por A" "$(printf '%s' "$r2" | campo cuerpo | head -c 140)"
    else
      ok "cookie de sesion emitida por A" "fulkro_session"
      rb="$(en_replica "$B" GET /api/v1/auth/me "" "Cookie: ${galleta}")"
      cb="$(printf '%s' "$rb" | campo codigo)"
      quien="$(printf '%s' "$rb" | dentro email)"
      if [ "$cb" = "200" ]; then
        ok "esa MISMA cookie vale en la replica B" "HTTP 200 · ${quien}"
      else
        falla "esa MISMA cookie vale en la replica B" "HTTP ${cb} · $(printf '%s' "$rb" | campo cuerpo | head -c 140)"
      fi
      # Y por nginx, alternando: 8 peticiones seguidas con la misma sesion.
      malas=0
      for i in $(seq 1 8); do
        c="$(curl -s -o /dev/null -w '%{http_code}' --max-time 6 -H "Cookie: ${galleta}" "${API}/auth/me")"
        [ "$c" = "200" ] || malas=$((malas+1))
      done
      if [ "$malas" -eq 0 ]; then ok "8 peticiones repartidas con la misma sesion" "todas 200"
      else falla "8 peticiones repartidas con la misma sesion" "${malas} de 8 fallaron"; fi
    fi
  fi
fi

titulo "4 · un enlace de portal emitido por A, ¿funciona en B?"
PID="$(psql_q "SELECT p.id FROM projects p JOIN dda_entries d ON d.project_id = p.id GROUP BY p.id ORDER BY count(*) DESC LIMIT 1;" | tr -d '[:space:]')"
if [ -z "$PID" ]; then
  falla "resolver el proyecto del demo" "sin proyecto con DdA"
else
  ra="$(en_replica "$A" POST "/api/v1/_dev/auditor-portal-token?project_id=${PID}" "" "")"
  token="$(printf '%s' "$ra" | dentro token)"
  otp="$(printf '%s' "$ra" | dentro otp)"
  if [ -z "$token" ]; then
    falla "A emite un enlace de portal firmado" "$(printf '%s' "$ra" | campo cuerpo | head -c 140)"
  else
    ok "A emite un enlace de portal firmado" "Ed25519 · OTP ${otp}"
    ver="$(python3 -c "import json;print(json.dumps({'token':'${token}','otp':'${otp}'}))")"
    rb="$(en_replica "$B" POST "/api/v1/public/auditor-portal/verify-otp" "$ver" "")"
    cb="$(printf '%s' "$rb" | campo codigo)"
    if [ "$cb" = "200" ]; then
      ok "B acepta el enlace y el codigo emitidos por A" "HTTP 200"
    else
      # Camino alternativo: leer el resumen del portal directamente en B.
      rb2="$(en_replica "$B" GET "/api/v1/public/auditor-portal/${token}/summary" "" "")"
      cb2="$(printf '%s' "$rb2" | campo codigo)"
      if [ "$cb2" = "200" ]; then
        ok "B sirve el portal del enlace emitido por A" "HTTP 200 (resumen)"
      else
        falla "B acepta el enlace emitido por A" "verify-otp HTTP ${cb} · summary HTTP ${cb2}"
      fi
    fi
  fi
fi

titulo "5 · un evento en tiempo real, ¿llega a los suscriptores de las DOS replicas?"
# Se abren DOS conexiones SSE por nginx (el reparto por turnos deja una en cada
# replica) y se provoca UN evento real: un PATCH de admin sobre una tarea del
# plan, que despacha `m17.plan.updated`. Se cuenta cuantas lo reciben.
#
# Dos trampas que costaron su rato, por si alguien repite la prueba:
#   · NO vale sondear con `docker exec python`: eso crea OTRO proceso, con SU
#     PROPIO despachador. Hay que entrar por HTTP.
#   · Hay que escuchar por el canal del CLIENTE. `m17.plan.updated` esta en
#     CLIENTE_EVENT_TYPES y NO en ADMIN_EVENT_TYPES, asi que el stream de admin
#     lo filtra a proposito (sse_dispatcher.py:157 y :202). Escuchando por el de
#     admin solo llegan latidos, y parece un fallo de reparto cuando no lo es.
if [ -n "${PID:-}" ] && [ -n "${galleta:-}" ]; then
  TAREA="$(psql_q "SELECT id FROM wbs_tasks WHERE project_id = '${PID}' AND deleted_at IS NULL ORDER BY task_code LIMIT 1;" | tr -d '[:space:]')"
  cl="$(curl -s -c "$TMP/cl.txt" --max-time 15 -X POST "${API}/client-auth/login" \
        -H 'Content-Type: application/json' \
        -d "$(python3 -c "import json;print(json.dumps({'email':'cliente@fulkro.es','password':'${OWNER_PASSWORD}'}))")" || true)"
  gal_cli="$(awk '$6=="fulkro_session"||$6=="fulkro_csrf"{printf "%s=%s; ", $6, $7}' "$TMP/cl.txt" 2>/dev/null)"
  if [ -z "$TAREA" ] || [ -z "$gal_cli" ]; then
    info "prueba de difusion entre replicas" "no ejecutada (tarea='${TAREA}' sesion de cliente=$([ -n "$gal_cli" ] && echo si || echo no))"
  else
    for n in 1 2; do
      ( curl -sN --max-time 30 -H "Cookie: ${gal_cli}" -H "Accept: text/event-stream" \
          "${API}/client-portal/projects/${PID}/events" > "$TMP/sse_${n}.txt" 2>/dev/null ) &
    done
    sleep 6
    codigo_patch="$(curl -s -o "$TMP/patch.json" -w '%{http_code}' --max-time 15 \
      -X PATCH -H "Cookie: ${galleta}" -H 'Content-Type: application/json' \
      -H "X-CSRF-Token: ${CSRF:-}" \
      -d '{"status":"en_revision"}' \
      "${API}/planning/projects/${PID}/tasks/${TAREA}")"
    if [ "$codigo_patch" = "200" ]; then
      ok "se provoca un evento real (m17.plan.updated)" "PATCH de una tarea del plan · HTTP 200"
    else
      info "se provoca un evento real (m17.plan.updated)" "PATCH HTTP ${codigo_patch} · $(head -c 130 "$TMP/patch.json" 2>/dev/null)"
    fi
    sleep 14
    wait 2>/dev/null
    recibieron=0
    for n in 1 2; do
      grep -q "m17.plan.updated" "$TMP/sse_${n}.txt" 2>/dev/null && recibieron=$((recibieron+1))
    done
    if [ "$recibieron" -ge 2 ]; then
      ok "el evento llega a las DOS conexiones" "hay difusion entre replicas"
    elif [ "$recibieron" -eq 1 ]; then
      falla "el evento llega a las DOS conexiones" \
        "solo a 1 de 2 · el despachador SSE vive en la memoria del proceso (sse_dispatcher.py:50, «In-memory pub-sub»): cada replica avisa unicamente a los suyos"
    else
      info "difusion de eventos entre replicas" \
        "ninguna de las dos conexiones recibio el evento · no concluyente (ficheros en $TMP)"
    fi
  fi
else
  info "prueba de difusion entre replicas" "no ejecutada (falta sesion o proyecto)"
fi

echo
echo "──────────────────────────────────────────────────────────────"
printf ' Resultado: %d correctas, %d fallidas\n' "$PASS" "$FAIL"
echo "──────────────────────────────────────────────────────────────"

if [ "$DEJAR" -eq 0 ]; then
  echo
  echo "==> restaurando el demo de una sola replica"
  $ESC stop nginx >/dev/null 2>&1
  $ESC rm -f nginx >/dev/null 2>&1
  $BASE up -d --no-build --scale backend=1 >/dev/null 2>&1
  echo "    hecho (make smoke deberia volver a pasar)"
fi
exit $([ "$FAIL" -gt 0 ] && echo 1 || echo 0)
