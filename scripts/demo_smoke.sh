#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# FULKRO · comprobación de humo del demo (make smoke)
# ════════════════════════════════════════════════════════════════════════════
# Qué comprueba: que la pila levantada por `make demo` sirve DATOS REALES en
# los tres portales, no una cáscara vacía.
#
# QUÉ NO SE USA, Y POR QUÉ (esto es el núcleo del asunto)
# ------------------------------------------------------
# El único endpoint de salud del repositorio es GET /api/v1/health y devuelve
# {status,version,environment} SIN tocar la base de datos. Un smoke que le
# hiciera curl sería VACUAMENTE VERDADERO: pasaría con el esquema vacío, con
# las tablas sin una sola fila y hasta con Postgres caído. Aquí NO se usa como
# criterio (ni siquiera se llama).
#
# El criterio es el mismo que ya aplica el repositorio en
# scripts/vacuity_check.py: una comprobación solo vale si PUEDE fallar. Por eso
# todo lo de abajo se apoya en población real —los `final_checks` de
# backend/scripts/seed_all_fulkro.py:654— y en respuestas con contenido
# (identificadores, recuentos, nombres), no en códigos HTTP 200.
#
# CRITERIO DE ACEPTACIÓN: con la base de datos vacía, este script FALLA.
#
# Uso:
#     make smoke
#     bash scripts/demo_smoke.sh
#
# Variables que admite (con sus valores por defecto):
#     COMPOSE_FILE=docker-compose.demo.yml   PROJECT=fulkro-demo
#     ENV_FILE=.env.demo
#     BACKEND_URL=http://127.0.0.1:18000     DEMO_URL=http://localhost:3000
#     PG_USER=fulkro                         PG_DB=fulkro
#     FULKRO_SMOKE_PSQL="..."   manda las consultas a OTRA base (sirve para
#                               probar el propio smoke; ver el final del fichero)
# ════════════════════════════════════════════════════════════════════════════

# Sin `-e`: se ejecutan TODAS las comprobaciones y se informa de todas; el
# código de salida lo decide el recuento de fallos.
set -uo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.demo.yml}"
PROJECT="${PROJECT:-fulkro-demo}"
ENV_FILE="${ENV_FILE:-.env.demo}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:18000}"
DEMO_URL="${DEMO_URL:-http://localhost:3000}"
# El usuario y la base los fija docker-compose.demo.yml en `environment:`.
PG_USER="${PG_USER:-fulkro}"
PG_DB="${PG_DB:-fulkro}"

API="${BACKEND_URL}/api/v1"

PASS=0
FAIL=0
TMPDIR_SMOKE="$(mktemp -d)"
COOKIES="${TMPDIR_SMOKE}/cookies.txt"
# Tarro de galletas SEPARADO para el pool cliente: ADR-013, dos poblaciones de
# sujeto distintas que comparten el nombre de cookie fulkro_session.
CLIENT_COOKIES="${TMPDIR_SMOKE}/cookies-cliente.txt"
trap 'rm -rf "$TMPDIR_SMOKE"' EXIT

# ── salida ──────────────────────────────────────────────────────────────────
ok()    { PASS=$((PASS+1)); printf '  OK     %-34s %s\n' "$1" "${2:-}"; }
falla() { FAIL=$((FAIL+1)); printf '  FALLO  %-34s %s\n' "$1" "${2:-}"; }
info()  {                   printf '  info   %-34s %s\n' "$1" "${2:-}"; }
titulo(){ printf '\n%s\n' "$1"; }

# ── utilidades ──────────────────────────────────────────────────────────────
for t in docker curl python3; do
    command -v "$t" >/dev/null 2>&1 || {
        echo "ERROR: falta la herramienta '$t' en este equipo." >&2; exit 1; }
done

# Extractor de JSON. Camino con puntos; '#' devuelve la longitud de una lista.
# Si la entrada no es JSON válido devuelve cadena vacía (y la comprobación que
# lo use fallará, que es lo correcto).
_PY_JSON='
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit(0)
cur = d
for part in sys.argv[1].split("."):
    if part == "#":
        cur = len(cur) if isinstance(cur, (list, dict, str)) else 0
        continue
    if isinstance(cur, list):
        try: cur = cur[int(part)]
        except Exception: cur = ""; break
    elif isinstance(cur, dict):
        cur = cur.get(part, "")
    else:
        cur = ""; break
print("" if cur is None else cur)
'
json_get() { python3 -c "$_PY_JSON" "$1"; }

# Construye un objeto JSON a partir de pares clave valor, escapando de verdad
# (las contraseñas del demo pueden llevar cualquier carácter).
_PY_MKJSON='
import json, sys
a = sys.argv[1:]
print(json.dumps(dict(zip(a[0::2], a[1::2]))))
'
json_obj() { python3 -c "$_PY_MKJSON" "$@"; }

# Código TOTP (RFC 6238: HMAC-SHA1, ventana de 30 s, 6 dígitos) con la
# biblioteca estándar, para no exigir pyotp en el anfitrión. Es el mismo
# algoritmo que backend/app/auth/totp_svc.py (pyotp con los mismos parámetros).
_PY_TOTP='
import base64, hmac, hashlib, struct, sys, time
s = sys.argv[1].strip().replace(" ", "").upper()
s += "=" * (-len(s) % 8)
key = base64.b32decode(s, casefold=True)
counter = int(time.time()) // 30
mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
off = mac[-1] & 0x0F
val = (struct.unpack(">I", mac[off:off + 4])[0] & 0x7FFFFFFF) % 1000000
print("%06d" % val)
'
totp_code() { python3 -c "$_PY_TOTP" "$1"; }

# Consulta a la base de datos del demo. `FULKRO_SMOKE_PSQL` permite apuntar a
# otra base para probar el propio smoke; va sin comillas a propósito, para que
# se parta en palabras.
psql_q() {
    if [ -n "${FULKRO_SMOKE_PSQL:-}" ]; then
        # shellcheck disable=SC2086
        $FULKRO_SMOKE_PSQL -qtAX -c "$1" 2>/dev/null
    else
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec -T postgres \
            psql -qtAX -U "$PG_USER" -d "$PG_DB" -c "$1" 2>/dev/null
    fi
}

# Cuenta filas de una tabla y la contrasta con su mínimo.
check_count() {
    local tabla="$1" minimo="$2" n
    n="$(psql_q "SELECT count(*) FROM ${tabla};" | tr -d '[:space:]')"
    if [[ "$n" =~ ^[0-9]+$ ]]; then
        if [ "$n" -ge "$minimo" ]; then
            ok "$tabla" "${n} filas (mínimo ${minimo})"
        else
            falla "$tabla" "${n} filas (mínimo ${minimo})"
        fi
    else
        falla "$tabla" "sin dato: la tabla no existe o la base no responde (mínimo ${minimo})"
    fi
}

# ════════════════════════════════════════════════════════════════════════════
echo "FULKRO · comprobación de humo del demo"
echo "  backend  ${BACKEND_URL}"
echo "  frontend ${DEMO_URL}"

# ── credenciales del operador ───────────────────────────────────────────────
OWNER_EMAIL="${FULKRO_DEMO_OWNER_EMAIL:-}"
OWNER_PASSWORD="${FULKRO_DEMO_OWNER_PASSWORD:-}"
if [ -f "$ENV_FILE" ]; then
    # Solo estas dos líneas del fichero; no se hace `source` del fichero entero
    # (lleva claves PEM multilínea que romperían el intérprete).
    [ -n "$OWNER_EMAIL" ] || OWNER_EMAIL="$(grep -m1 '^FULKRO_DEMO_OWNER_EMAIL=' "$ENV_FILE" | cut -d= -f2-)"
    [ -n "$OWNER_PASSWORD" ] || OWNER_PASSWORD="$(grep -m1 '^FULKRO_DEMO_OWNER_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)"
fi
OWNER_EMAIL="${OWNER_EMAIL:-demo@fulkro.es}"
OWNER_PASSWORD="${OWNER_PASSWORD:-fulkro-demo-2026}"

# ════════════════════════════════════════════════════════════════════════════
titulo "1 · población de la base de datos (backend/scripts/seed_all_fulkro.py:654)"
# Estos nueve umbrales son EXACTAMENTE los `final_checks` del seed. Son los que
# hacen que este script no pueda pasar sobre una base vacía.
check_count ens_measures        73
check_count ens_reinforcements  18
check_count magerit_ens_mapping 73
check_count threats             50
check_count safeguards          80
check_count magerit_asset_types 50
check_count clients              3
check_count pricing_catalog     10
check_count templates           84

# Informativo, no decide nada: el demo siembra con --skip-corpus, así que estas
# dos tablas se quedan vacías a propósito. Se imprimen porque un smoke que solo
# mire los final_checks daría verde con la DdA sin refuerzos y conviene verlo.
# knowledge_chunks es el nombre REAL de la tabla del corpus (no corpus_chunks).
# Ya no van vacias: el compose monta backend/tests/fixtures/corpus_seed.sql.gz y
# demo_bootstrap.py lo carga (1.031 chunks con su vector ya embebido).
for t in knowledge_chunks ens_measure_refuerzos ens_measure_dimensiones; do
    n="$(psql_q "SELECT count(*) FROM ${t};" | tr -d '[:space:]')"
    if [[ "$n" =~ ^[0-9]+$ ]]; then
        info "$t" "${n} filas (informativo · llegan del fixture del corpus, no del seed)"
    else
        info "$t" "sin dato: la tabla no existe o la base no responde (informativo)"
    fi
done

# ════════════════════════════════════════════════════════════════════════════
titulo "2 · portal de administración (cookie de sesión tras el segundo factor)"

# POST /auth/login NO devuelve cookie de sesión: solo un mfa_ticket. La cookie
# la emite /auth/totp/verify. Por eso el demo auto-enrola TOTP.
login_body="$(json_obj email "$OWNER_EMAIL" password "$OWNER_PASSWORD")"
login_out="$(curl -s --max-time 15 -X POST "${API}/auth/login" \
    -H 'Content-Type: application/json' -d "$login_body")"
MFA_TICKET="$(printf '%s' "$login_out" | json_get mfa_ticket)"
if [ -n "$MFA_TICKET" ]; then
    ok "POST /auth/login" "mfa_ticket emitido para ${OWNER_EMAIL}"
else
    falla "POST /auth/login" "sin mfa_ticket · respuesta: $(printf '%s' "$login_out" | head -c 160)"
fi

# El secreto TOTP se lee de la base (auth_totp_secrets.secret, base32 en claro),
# no de la salida por pantalla de demo_bootstrap.py: así no dependemos de cómo
# imprima ese script.
TOTP_SECRET="$(psql_q "SELECT s.secret FROM auth_totp_secrets s JOIN auth_users u ON u.id = s.user_id WHERE u.email = '${OWNER_EMAIL}' AND s.verified LIMIT 1;" | tr -d '[:space:]')"
if [ -n "$TOTP_SECRET" ]; then
    ok "segundo factor enrolado" "auth_totp_secrets tiene secreto verificado del operador"
else
    falla "segundo factor enrolado" "auth_totp_secrets sin secreto verificado para ${OWNER_EMAIL} (¿corrió demo_bootstrap.py?)"
fi

CSRF=""
if [ -n "$MFA_TICKET" ] && [ -n "$TOTP_SECRET" ]; then
    code="$(totp_code "$TOTP_SECRET")"
    verify_body="$(json_obj mfa_ticket "$MFA_TICKET" code "$code")"
    verify_out="$(curl -s --max-time 15 -c "$COOKIES" -X POST "${API}/auth/totp/verify" \
        -H 'Content-Type: application/json' -d "$verify_body")"
    CSRF="$(printf '%s' "$verify_out" | json_get csrf_token)"
    if [ -n "$CSRF" ] && grep -q 'fulkro_session' "$COOKIES" 2>/dev/null; then
        ok "POST /auth/totp/verify" "cookie fulkro_session emitida"
    else
        falla "POST /auth/totp/verify" "sin cookie de sesión · respuesta: $(printf '%s' "$verify_out" | head -c 160)"
    fi
else
    falla "POST /auth/totp/verify" "no se intenta: falta el mfa_ticket o el secreto TOTP"
fi

me_email="$(curl -s --max-time 15 -b "$COOKIES" "${API}/auth/me" | json_get email)"
if [ "$me_email" = "$OWNER_EMAIL" ]; then
    ok "GET /auth/me" "identidad: ${me_email}"
else
    falla "GET /auth/me" "esperaba ${OWNER_EMAIL} · recibido: '${me_email:-vacío}'"
fi

clients_json="$(curl -s --max-time 20 -b "$COOKIES" "${API}/clients")"
n_clients="$(printf '%s' "$clients_json" | json_get '#')"
first_client="$(printf '%s' "$clients_json" | json_get '0.nombre')"
if [[ "$n_clients" =~ ^[0-9]+$ ]] && [ "$n_clients" -ge 3 ] && [ -n "$first_client" ]; then
    ok "GET /clients" "${n_clients} clientes · el primero: ${first_client}"
else
    falla "GET /clients" "${n_clients:-0} clientes con nombre '${first_client:-vacío}' (mínimo 3 y con nombre)"
fi

# /_dev/seed-info SÍ consulta auth_users (al contrario que /health).
seed_info="$(curl -s --max-time 15 "${API}/_dev/seed-info")"
marcos_id="$(printf '%s' "$seed_info" | json_get marcos_user_id)"
marcos_email="$(printf '%s' "$seed_info" | json_get marcos_email)"
if [[ "$marcos_id" =~ ^[0-9a-f-]{36}$ ]]; then
    ok "GET /_dev/seed-info" "administrador ${marcos_email} (${marcos_id})"
else
    falla "GET /_dev/seed-info" "sin UUID de administrador · respuesta: $(printf '%s' "$seed_info" | head -c 160)"
fi

# ════════════════════════════════════════════════════════════════════════════
titulo "3 · portal de cliente (correo + contraseña · ADR-013, pool separado)"

# El portal de cliente NO va por magic link: va por correo y contraseña, y
# ningún seed crea usuarios de portal. El único que los crea es este endpoint.
tc="$(curl -s --max-time 30 -X POST "${API}/_dev/create-test-client")"
TC_EMAIL="$(printf '%s' "$tc" | json_get email)"
TC_PASS="$(printf '%s' "$tc" | json_get password)"
TC_PROJECT="$(printf '%s' "$tc" | json_get project_id)"
if [ -n "$TC_EMAIL" ] && [ -n "$TC_PROJECT" ]; then
    ok "POST /_dev/create-test-client" "usuario ${TC_EMAIL} · proyecto ${TC_PROJECT}"
else
    falla "POST /_dev/create-test-client" "respuesta sin usuario ni proyecto: $(printf '%s' "$tc" | head -c 160)"
fi

CLIENT_TOKEN=""
if [ -n "$TC_EMAIL" ]; then
    cl_body="$(json_obj email "$TC_EMAIL" password "$TC_PASS")"
    # El pool cliente autentica por COOKIE (fulkro_session + fulkro_csrf), no por
    # cabecera Authorization: el `access_token` del cuerpo es compatibilidad hacia
    # atras (m21_portal_cliente/api.py:71) y el dep global lee request.cookies
    # (auth/global_dep.py:198). Con Bearer, /client-portal/project devolvia
    # {"detail":"Authentication required"}. Medido.
    cl_out="$(curl -s --max-time 15 -c "$CLIENT_COOKIES" -X POST "${API}/client-auth/login" \
        -H 'Content-Type: application/json' -d "$cl_body")"
    CLIENT_TOKEN="$(printf '%s' "$cl_out" | json_get access_token)"
    if [ -n "$CLIENT_TOKEN" ]; then
        ok "POST /client-auth/login" "sesión de cliente abierta"
    else
        falla "POST /client-auth/login" "sin access_token · respuesta: $(printf '%s' "$cl_out" | head -c 160)"
    fi
fi

if [ -n "$CLIENT_TOKEN" ]; then
    CLIENT_CSRF="$(awk '/fulkro_csrf/ {print $NF}' "$CLIENT_COOKIES" 2>/dev/null | tail -1)"
    proj="$(curl -s --max-time 15 -b "$CLIENT_COOKIES" \
        ${CLIENT_CSRF:+-H "X-CSRF-Token: ${CLIENT_CSRF}"} \
        "${API}/client-portal/project")"
    p_nombre="$(printf '%s' "$proj" | json_get nombre)"
    p_cat="$(printf '%s' "$proj" | json_get categoria_objetivo)"
    if [ -n "$p_nombre" ] && [ -n "$p_cat" ]; then
        ok "GET /client-portal/project" "proyecto '${p_nombre}' · categoría ${p_cat}"
    else
        falla "GET /client-portal/project" "sin proyecto con nombre y categoría: $(printf '%s' "$proj" | head -c 160)"
    fi
else
    falla "GET /client-portal/project" "no se intenta: no hay sesión de cliente"
fi

# ════════════════════════════════════════════════════════════════════════════
titulo "4 · portal de auditor (enlace firmado Ed25519 · M12)"

ap="$(curl -s --max-time 30 -X POST "${API}/_dev/auditor-portal-token")"
AUD_TOKEN="$(printf '%s' "$ap" | json_get token)"
AUD_PATH="$(printf '%s' "$ap" | json_get portal_path)"
if [ -n "$AUD_TOKEN" ]; then
    ok "POST /_dev/auditor-portal-token" "enlace emitido (${AUD_PATH})"
else
    falla "POST /_dev/auditor-portal-token" "sin token · respuesta: $(printf '%s' "$ap" | head -c 160)"
fi

if [ -n "$AUD_TOKEN" ]; then
    sm="$(curl -s --max-time 20 "${API}/public/auditor-portal/${AUD_TOKEN}/summary")"
    a_cif="$(printf '%s' "$sm" | json_get cliente.cif)"
    a_proj="$(printf '%s' "$sm" | json_get project.nombre)"
    a_dda="$(printf '%s' "$sm" | json_get counts.dda_entries)"
    if [ -n "$a_cif" ] && [ -n "$a_proj" ]; then
        ok "GET /public/auditor-portal/.../summary" "cliente ${a_cif} · proyecto '${a_proj}' · ${a_dda} entradas de DdA"
    else
        falla "GET /public/auditor-portal/.../summary" "sin datos del expediente: $(printf '%s' "$sm" | head -c 160)"
    fi
else
    falla "GET /public/auditor-portal/.../summary" "no se intenta: no hay enlace de auditor"
fi

# ════════════════════════════════════════════════════════════════════════════
titulo "5 · frontend"
# Esto es una comprobación de VIDA, no de datos: dice que Next.js sirve HTML.
# Lo que hay detrás de la pantalla de entrada ya lo han comprobado los apartados
# 1 a 4 contra la API.
: > "${TMPDIR_SMOKE}/index.html"
# OJO: cuando curl no conecta imprime "000" Y ADEMÁS sale con código != 0. Un
# `|| echo 000` encadenaría un segundo "000" y saldría "000000", que como número
# vale 0 y pasaría el `-lt 500` de abajo. Se recoge tal cual y se normaliza.
# -L a proposito: `/` responde 307 hacia /login cuando no hay cookie
# (frontend/middleware.ts). Sin seguir la redireccion se recogen 6 bytes y la
# comprobacion falla aunque el frontend este perfectamente vivo. Medido.
front_code="$(curl -sL -o "${TMPDIR_SMOKE}/index.html" -w '%{http_code}' --max-time 20 "${DEMO_URL}/" 2>/dev/null)"
front_code="${front_code:-000}"
front_bytes="$(wc -c < "${TMPDIR_SMOKE}/index.html" 2>/dev/null || echo 0)"
if [ "$front_code" != "000" ] && [ "$front_code" -lt 500 ] && [ "$front_bytes" -gt 500 ]; then
    ok "GET / (frontend)" "HTTP ${front_code} · ${front_bytes} bytes de HTML (vida, no datos)"
else
    falla "GET / (frontend)" "HTTP ${front_code} · ${front_bytes} bytes"
fi

# ════════════════════════════════════════════════════════════════════════════
echo
echo "──────────────────────────────────────────────────────────────"
printf ' Resultado: %d correctas, %d fallidas\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo " El demo NO está en condiciones. Para ver por qué:"
    echo "   make logs SERVICE=backend"
    echo "   docker compose -f ${COMPOSE_FILE} -p ${PROJECT} ps -a"
    echo "──────────────────────────────────────────────────────────────"
    exit 1
fi
echo " El demo sirve datos reales en los tres portales."
echo "──────────────────────────────────────────────────────────────"

# ── Cómo comprobar que este script NO es vacuamente verdadero ───────────────
# Contra una base con el esquema pero sin datos, o contra una base vacía, el
# apartado 1 tiene que ponerse en FALLO. Se puede forzar sin tocar el demo:
#
#   docker run -d --name smoke-vacio -e POSTGRES_PASSWORD=x pgvector/pgvector:pg16
#   FULKRO_SMOKE_PSQL="docker exec -i smoke-vacio psql -U postgres -d postgres" \
#       bash scripts/demo_smoke.sh
#   docker rm -f smoke-vacio
#
# Salida esperada: las nueve líneas del apartado 1 en FALLO ("sin dato: la tabla
# no existe") y código de salida 1.
