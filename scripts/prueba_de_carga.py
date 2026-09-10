#!/usr/bin/env python3
"""Prueba de carga modesta contra la pila del demo · BLOQUE H.

POR QUE EXISTE
--------------
Para poder decir "escalable" con un numero detras. Sin un limite medido, la
palabra no significa nada: toda aplicacion escala hasta que deja de hacerlo, y
lo unico defendible es decir DONDE deja de hacerlo y con que carga.

QUE MIDE
--------
Una rampa de concurrencia sobre los endpoints MAS USADOS de verdad (elegidos
contando el trafico real que genero el recorrido completo del BLOQUE E sobre el
registro de acceso del backend, no a ojo), buscando el punto en el que el p95 se
rompe. Y lo mismo con dos replicas, para contestar si la segunda sirve de algo.

QUE **NO** MIDE, y hay que tenerlo delante al leer los numeros
--------------------------------------------------------------
  * NO es una prueba de produccion. Corre contra un Docker Compose en un
    portatil, con la base, Redis, MinIO, el frontend y el generador de carga
    COMPARTIENDO las mismas CPU. Los numeros absolutos valen para ESTA maquina;
    lo que se traslada es la FORMA de la curva y donde esta el cuello.
  * NO mide el frontend. Entra por el puerto del backend a proposito: aqui
    interesa el limite del servidor, no el de React.
  * NO mide escrituras. Todos los endpoints son de lectura: una rampa de
    escrituras sobre el demo lo dejaria inservible para el resto de bloques.
  * El generador de carga es Python con hilos. Con concurrencias altas, parte
    del limite medido puede ser del propio generador; por eso se publica tambien
    el uso de CPU de cada contenedor, que es lo que permite distinguir "se
    rompio el servidor" de "se rompio mi medidor".

Uso:
    python3 scripts/prueba_de_carga.py --salida out/carga_1_replica.json
    python3 scripts/prueba_de_carga.py --replicas 2 --salida out/carga_2_replicas.json
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import http.cookiejar
import json
import statistics
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field

API = "http://127.0.0.1:18000"
PROYECTO_DOCKER = "fulkro-demo"

# Umbral de rotura, DECLARADO ANTES DE MEDIR para no elegirlo despues segun
# convenga. 1 s de p95 en un endpoint de lectura es donde una interfaz empieza a
# sentirse rota: por debajo se percibe instantanea, por encima se nota la espera.
UMBRAL_P95_S = 1.0

# Escalones de la rampa. Se para en cuanto el p95 pasa el umbral o aparecen
# errores: seguir subiendo despues de romper solo mide como de mal se rompe.
ESCALONES = (1, 2, 5, 10, 20, 40, 80)
SEGUNDOS_POR_ESCALON = 12


@dataclass
class Medida:
    endpoint: str
    concurrencia: int
    peticiones: int
    errores: int
    codigos: dict = field(default_factory=dict)
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    rps: float = 0.0
    cpu: dict = field(default_factory=dict)


def totp(secreto: str) -> str:
    k = base64.b32decode(secreto + "=" * ((8 - len(secreto) % 8) % 8))
    c = struct.pack(">Q", int(time.time()) // 30)
    h = hmac.new(k, c, hashlib.sha1).digest()
    o = h[-1] & 0xF
    return "%06d" % ((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 1000000)


def secreto_totp() -> str:
    sql = ("SELECT s.secret FROM auth_totp_secrets s JOIN auth_users u "
           "ON u.id = s.user_id WHERE u.email = 'demo@fulkro.es' "
           "AND s.verified LIMIT 1;")
    out = subprocess.run(
        ["docker", "exec", f"{PROYECTO_DOCKER}-postgres-1", "psql", "-U", "fulkro",
         "-d", "fulkro", "-tA", "-c", sql],
        capture_output=True, text=True, check=True)
    return out.stdout.strip()


def abrir_sesion() -> urllib.request.OpenerDirector:
    """Entra como operador y devuelve un abridor con la cookie de sesion.

    Se entra POR EL MISMO CAMINO que una persona (contrasenya + segundo factor).
    Falsificar la cookie a mano habria medido otra cosa: los endpoints que se
    cargan estan detras de `require_owner`.
    """
    tarro = http.cookiejar.CookieJar()
    ab = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(tarro))

    def post(ruta: str, cuerpo: dict) -> dict:
        req = urllib.request.Request(
            API + ruta, data=json.dumps(cuerpo).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with ab.open(req, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")

    # El segundo factor NO es independiente del login: `/auth/totp/verify` exige
    # el `mfa_ticket` que devuelve `/auth/login`. Encadenarlos es lo que hace
    # que esto entre por el MISMO camino que una persona, en vez de fabricar una
    # cookie a mano — que mediria otra cosa.
    r = post("/api/v1/auth/login",
             {"email": "demo@fulkro.es", "password": "fulkro-demo-2026"})
    ticket = r.get("mfa_ticket") or r.get("ticket") or ""
    if not ticket:
        raise SystemExit(
            f"el login no devolvio mfa_ticket · respuesta: {list(r)[:8]}"
        )
    post("/api/v1/auth/totp/verify",
         {"mfa_ticket": ticket, "code": totp(secreto_totp())})
    # Comprobacion explicita: si la sesion no vale, toda la medida siguiente
    # seria de codigos 401 y tendria una forma preciosa que no significa nada.
    with ab.open(API + "/api/v1/auth/me", timeout=15) as r:
        if r.status != 200:
            raise SystemExit(f"la sesion de operador no vale (HTTP {r.status})")
    return ab


def cpu_contenedores() -> dict:
    """Uso de CPU por contenedor en el instante de la medida.

    Es lo que permite decir DONDE esta el cuello en vez de suponerlo, y tambien
    distinguir un servidor saturado de un generador de carga saturado.
    """
    try:
        out = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.CPUPerc}}"],
            capture_output=True, text=True, timeout=25, check=True).stdout
    except Exception:
        return {}
    d = {}
    for linea in out.strip().splitlines():
        partes = linea.split("\t")
        if len(partes) == 2 and PROYECTO_DOCKER in partes[0]:
            d[partes[0].replace(f"{PROYECTO_DOCKER}-", "")] = partes[1]
    return d


def escalon(ab, ruta: str, concurrencia: int, segundos: int) -> Medida:
    latencias: list[float] = []
    codigos: dict[str, int] = {}
    errores = 0
    lock = threading.Lock()
    fin = time.time() + segundos

    def trabajador() -> None:
        nonlocal errores
        while time.time() < fin:
            t0 = time.perf_counter()
            try:
                with ab.open(API + ruta, timeout=30) as r:
                    r.read()
                    cod = str(r.status)
            except urllib.error.HTTPError as e:
                cod = str(e.code)
            except Exception as e:  # noqa: BLE001
                cod = type(e).__name__
            dt = (time.perf_counter() - t0) * 1000
            with lock:
                latencias.append(dt)
                codigos[cod] = codigos.get(cod, 0) + 1
                if not cod.startswith("2"):
                    errores += 1

    hilos = [threading.Thread(target=trabajador, daemon=True)
             for _ in range(concurrencia)]
    t_ini = time.time()
    for h in hilos:
        h.start()
    # La CPU se mide A MITAD del escalon, no al final: al final los hilos ya
    # estan terminando y la lectura sale baja.
    time.sleep(min(segundos / 2, 6))
    cpu = cpu_contenedores()
    for h in hilos:
        h.join(timeout=segundos + 40)
    dur = time.time() - t_ini

    ordenadas = sorted(latencias)
    def pct(p: float) -> float:
        if not ordenadas:
            return 0.0
        i = min(len(ordenadas) - 1, int(len(ordenadas) * p))
        return round(ordenadas[i], 1)

    return Medida(
        endpoint=ruta, concurrencia=concurrencia, peticiones=len(latencias),
        errores=errores, codigos=codigos,
        p50_ms=pct(0.50), p95_ms=pct(0.95), p99_ms=pct(0.99),
        rps=round(len(latencias) / dur, 1) if dur else 0.0, cpu=cpu,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="out/carga.json")
    ap.add_argument("--replicas", type=int, default=1,
                    help="solo se anota en el informe · levantarlas es cosa del Makefile")
    ap.add_argument("--segundos", type=int, default=SEGUNDOS_POR_ESCALON)
    ap.add_argument("--endpoints", default="",
                    help="lista separada por comas · por omision, los seis medidos")
    args = ap.parse_args()

    ab = abrir_sesion()

    # Los seis endpoints se eligieron CONTANDO el trafico real que el recorrido
    # completo del BLOQUE E genero sobre el registro de acceso del backend
    # (`docker logs ... | grep '"GET /api'`), excluyendo dos cosas:
    #   · /api/v1/health, que lo dispara el healthcheck de Docker cada 5 s y no
    #     es trafico de nadie;
    #   · los `/events`, que son flujos SSE de larga duracion y en una rampa
    #     medirian cuantas conexiones caben abiertas, no cuanto se tarda.
    # El sexto es la busqueda del corpus: no es de los mas llamados, pero es el
    # unico que toca el embebido de la consulta, que es donde se sospechaba el
    # cuello. Sin el, la prueba no podria ni confirmar ni desmentir esa
    # sospecha.
    proyecto = subprocess.run(
        ["docker", "exec", f"{PROYECTO_DOCKER}-postgres-1", "psql", "-U", "fulkro",
         "-d", "fulkro", "-tA", "-c",
         "SELECT p.id::text FROM projects p JOIN clients c ON c.id=p.client_id "
         "WHERE c.nombre ILIKE 'NovaEdge%' AND p.deleted_at IS NULL "
         "ORDER BY p.created_at LIMIT 1;"],
        capture_output=True, text=True, check=True).stdout.strip()

    endpoints = args.endpoints.split(",") if args.endpoints else [
        "/api/v1/auth/me",
        "/api/v1/clients",
        "/api/v1/alerts/active",
        f"/api/v1/projects/{proyecto}/header",
        f"/api/v1/projects/{proyecto}/feature-flags",
        "/api/v1/corpus/search?q=plazo%20de%20notificacion%20de%20brechas&limit=5",
    ]

    print(f"Umbral de rotura declarado: p95 > {UMBRAL_P95_S * 1000:.0f} ms")
    print(f"Escalones: {ESCALONES} · {args.segundos} s cada uno · "
          f"{args.replicas} replica(s)\n")

    todo: list[dict] = []
    for ruta in endpoints:
        print(f"── {ruta}")
        roto_en = None
        for c in ESCALONES:
            m = escalon(ab, ruta, c, args.segundos)
            todo.append(asdict(m))
            marca = ""
            if m.p95_ms > UMBRAL_P95_S * 1000 or m.errores:
                marca = "  <-- ROMPE"
                roto_en = roto_en or c
            print(f"   c={c:<3} {m.peticiones:>5} pet · {m.rps:>7.1f} rps · "
                  f"p50 {m.p50_ms:>7.1f} ms · p95 {m.p95_ms:>8.1f} ms · "
                  f"{m.errores} err{marca}")
            if roto_en:
                break
        if roto_en is None:
            print(f"   no rompe hasta c={ESCALONES[-1]} (el techo de la rampa)")
        print()

    salida = {
        "replicas": args.replicas,
        "umbral_p95_ms": UMBRAL_P95_S * 1000,
        "segundos_por_escalon": args.segundos,
        "escalones": list(ESCALONES),
        "endpoints": endpoints,
        "medidas": todo,
        "generado": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    import pathlib
    p = pathlib.Path(args.salida)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(salida, indent=2, ensure_ascii=False))
    print(f"Medida en bruto: {args.salida}")


if __name__ == "__main__":
    main()
