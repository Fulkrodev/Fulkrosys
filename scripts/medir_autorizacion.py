#!/usr/bin/env python3
"""Mide el reparto REAL de las puertas de autorizacion sobre la aplicacion en ejecucion.

Por que existe este script, y no un `git grep`:

    $ git grep -o 'Depends(require_owner)' -- backend/app | wc -l
    249

Ese comando cuenta OCURRENCIAS DE UN LITERAL en el fuente, no endpoints protegidos, y las dos
cosas no guardan una proporcion fija:

  · 132 de esas 249 son `dependencies=[Depends(require_owner)]` en el constructor de un
    APIRouter. Una sola ocurrencia protege TODOS los endpoints que cuelguen de ese router, que
    pueden ser uno o dieciseis.
  · La proporcion de ocurrencias a nivel de router difiere entre puertas (53 %, 19 %, 46 %), asi
    que el cociente entre los tres numeros no mide "que parte de los endpoints exige ser
    administrador": compara poblaciones que no son la misma.
  · Y el error no va necesariamente en la direccion que parece: si una ocurrencia de router cuelga
    de un router con dieciseis rutas, la cifra de 249 se queda CORTA, no larga.

Aqui se introspecciona el objeto `app` real y se recorre el arbol de dependencias de cada ruta de
forma RECURSIVA: una puerta puede estar anidada dentro de otra dependencia y no aparecer en el
primer nivel.

Dos avisos de version, medidos el 2026-09-10 con fastapi 0.141.1 y starlette 1.6.0:

  1. `include_router` YA NO aplana las rutas en `app.routes`: deja objetos `_IncludedRouter` con
     resolucion perezosa. El recorrido ingenuo
         [r for r in app.routes if isinstance(r, APIRoute)]
     devuelve 0 en esta version. Este script resuelve el arbol efectivo.
  2. Las dependencias de NIVEL DE ROUTER no estan en el `dependant` de la ruta original: se
     componen al incluir el router. Por eso se usa `effective_route_contexts()`, que devuelve la
     composicion efectiva, y no `original_router.routes`, que devolveria la ruta sin la puerta que
     le pone su router. Medir ahi seria contar de menos justamente en los 132 casos que importan.

Uso:
    PYTHONPATH=. python3 scripts/medir_autorizacion.py
    PYTHONPATH=. python3 scripts/medir_autorizacion.py --detalle require_client_user
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

# Evita que el arranque exija claves y base de datos reales.
os.environ.setdefault("FULKRO_TESTING", "1")

PUERTAS = ("require_owner", "require_client_user", "require_marcos_or_client")

# O1.2 · puertas que NO son dependencias y por tanto NO salen en el arbol de
# `dependant` ni en el esquema OpenAPI. Se llaman desde el CUERPO del endpoint.
#
# Por que estan en el cuerpo, que no es descuido: `require_ens_role` consulta
# `client_contacts JOIN projects`, y `projects` tiene RLS por
# `current_project_id()`. La consulta solo ve algo DESPUES de fijar el contexto
# de inquilino, cosa que hace el propio endpoint (`_set_project_rls`,
# `_get_analysis_with_rls`). Como dependencia se ejecutaria ANTES de ese
# contexto y devolveria "no hay titular" siempre, o sea 403 tambien para quien
# si tiene el rol.
#
# La contrapartida, dicha: al no ser dependencias no aparecen en OpenAPI, asi
# que un consumidor de la API no las ve. Por eso se cuentan aqui: la cifra
# publicada no puede dejarlas fuera.
PUERTAS_EN_CUERPO = ("require_ens_role", "require_ens_role_asignado")
METODOS_HTTP = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"}


def nombres_dependencias(dependant) -> set[str]:
    """Todos los nombres de dependencia del arbol, RECURSIVO.

    Recursivo a proposito: una puerta puede colgar de otra dependencia y no aparecer en el
    primer nivel.
    """
    vistos: set[str] = set()

    def _walk(d) -> None:
        for sub in getattr(d, "dependencies", ()):
            call = getattr(sub, "call", None)
            if call is not None:
                vistos.add(getattr(call, "__name__", repr(call)))
            _walk(sub)

    _walk(dependant)
    return vistos


def rutas_efectivas():
    """Devuelve (camino, metodos, dependant) por cada ruta de la aplicacion.

    Robusto a la version: usa `effective_route_contexts()` cuando existe (fastapi >= 0.141) y cae
    al recorrido clasico de `app.routes` cuando no.
    """
    from fastapi.routing import APIRoute

    from backend.app.main import app

    try:  # fastapi >= 0.141
        from fastapi.routing import _IncludedRouter
    except ImportError:  # pragma: no cover — fastapi antiguo
        _IncludedRouter = ()  # type: ignore[assignment]

    salida = []

    def _visitar(rutas) -> None:
        for r in rutas:
            if isinstance(r, APIRoute):
                salida.append((r.path, set(r.methods or ()), r.dependant))
            elif _IncludedRouter and isinstance(r, _IncludedRouter):
                for ctx in r.effective_route_contexts():
                    metodos = set(getattr(ctx, "methods", None) or ())
                    salida.append((ctx.path, metodos, ctx.dependant))
                for cand in r.effective_candidates():
                    if _IncludedRouter and isinstance(cand, _IncludedRouter):
                        _visitar([cand])
            else:
                sub = getattr(r, "routes", None)
                if sub:
                    _visitar(sub)

    _visitar(app.routes)
    return salida, app


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--detalle", metavar="PUERTA", help="lista los caminos protegidos por esa puerta")
    args = ap.parse_args()

    rutas, app = rutas_efectivas()
    if not rutas:
        print("ERROR: 0 rutas resueltas. El recorrido no ha funcionado con esta version de "
              "fastapi; NO publiques ninguna cifra a partir de esto.", file=sys.stderr)
        return 2

    # ── Dos poblaciones, contadas por separado y nombradas ────────────────────
    # (a) RUTAS            = objetos de ruta (un camino puede aparecer varias veces con
    #                        metodos distintos si se declararon por separado)
    # (b) OPERACIONES      = camino x metodo, que es lo que ve quien consume la API
    n_rutas = len(rutas)
    operaciones = [(c, m) for c, ms, _ in rutas for m in ms if m in METODOS_HTTP]
    n_ops = len(operaciones)

    por_puerta_rutas: Counter[str] = Counter()
    por_puerta_ops: Counter[str] = Counter()
    protegidas_rutas = 0
    protegidas_ops = 0
    detalle: list[str] = []

    for camino, metodos, dep in rutas:
        nombres = nombres_dependencias(dep)
        ops_de_esta = len([m for m in metodos if m in METODOS_HTTP]) or 1
        puertas_aqui = [p for p in PUERTAS if p in nombres]
        if puertas_aqui:
            protegidas_rutas += 1
            protegidas_ops += ops_de_esta
        for p in puertas_aqui:
            por_puerta_rutas[p] += 1
            por_puerta_ops[p] += ops_de_esta
            if args.detalle == p:
                detalle.append(f"  {'/'.join(sorted(metodos & METODOS_HTTP)) or '-':22s} {camino}")

    esquema = app.openapi()
    ops_esquema = sum(1 for v in esquema["paths"].values() for m in v if m.upper() in METODOS_HTTP)

    print("Reparto de las puertas de autorizacion · medido sobre la aplicacion en ejecucion")
    print()
    print(f"  rutas resueltas          {n_rutas}")
    print(f"  operaciones (camino x metodo) {n_ops}")
    print(f"  contraste con el esquema OpenAPI: {len(esquema['paths'])} caminos, "
          f"{ops_esquema} operaciones")
    if n_ops != ops_esquema:
        print(f"  AVISO: el recorrido y el esquema no coinciden ({n_ops} vs {ops_esquema}). "
              f"Alguna ruta queda fuera del esquema (include_in_schema=False) o del recorrido.")
    print()
    print(f"  {'puerta':28s} {'rutas':>7s} {'% rutas':>9s} {'operaciones':>12s} {'% ops':>8s}")
    for p in PUERTAS:
        r, o = por_puerta_rutas[p], por_puerta_ops[p]
        print(f"  {p:28s} {r:7d} {100*r/n_rutas:8.1f}% {o:12d} {100*o/n_ops:7.1f}%")
    print(f"  {'-- alguna de las tres --':28s} {protegidas_rutas:7d} "
          f"{100*protegidas_rutas/n_rutas:8.1f}% {protegidas_ops:12d} {100*protegidas_ops/n_ops:7.1f}%")
    print(f"  {'-- sin ninguna --':28s} {n_rutas-protegidas_rutas:7d} "
          f"{100*(n_rutas-protegidas_rutas)/n_rutas:8.1f}% {n_ops-protegidas_ops:12d} "
          f"{100*(n_ops-protegidas_ops)/n_ops:7.1f}%")
    print()
    print("  Nota: los porcentajes son sobre el TOTAL de la aplicacion, no sobre el subconjunto")
    print("  protegido. Una ruta puede pasar por mas de una puerta, asi que las filas pueden sumar")
    print("  mas que la fila 'alguna de las tres'.")

    # ── Corte por poblacion de sujeto (el que de verdad informa) ─────────────
    # `require_owner` / `require_client_user` no son las unicas puertas: hay endpoints que
    # resuelven el sujeto con `get_current_user` (pool administrador) o
    # `get_current_client_user` (pool cliente) sin pasar por las tres nombradas. Contar solo
    # las tres deja fuera 151 rutas de cliente y presenta como "sin puerta" cosas que si la
    # tienen. Estas categorias son EXCLUYENTES y suman el total.
    GRUPO_ADMIN = {"require_owner", "get_current_user"}
    GRUPO_CLIENTE = {"require_client_user", "get_current_client_user"}
    solo_admin = solo_cliente = ambos = ninguna = 0
    con_authenticate = 0
    for _c, _m, dep in rutas:
        ns = nombres_dependencias(dep)
        if "authenticate_request" in ns:
            con_authenticate += 1
        if "require_marcos_or_client" in ns:
            ambos += 1
        elif GRUPO_ADMIN & ns and not GRUPO_CLIENTE & ns:
            solo_admin += 1
        elif GRUPO_CLIENTE & ns and not GRUPO_ADMIN & ns:
            solo_cliente += 1
        else:
            ninguna += 1

    print()
    print("  Corte por poblacion de sujeto (categorias EXCLUYENTES, suman el total):")
    print(f"  {'solo administrador':28s} {solo_admin:7d} {100*solo_admin/n_rutas:8.1f}%")
    print(f"  {'solo cliente':28s} {solo_cliente:7d} {100*solo_cliente/n_rutas:8.1f}%")
    print(f"  {'cualquiera de los dos':28s} {ambos:7d} {100*ambos/n_rutas:8.1f}%")
    print(f"  {'ninguna de esas':28s} {ninguna:7d} {100*ninguna/n_rutas:8.1f}%")
    con_puerta = solo_admin + solo_cliente + ambos
    if con_puerta:
        print()
        print(f"  De las {con_puerta} rutas con puerta de poblacion, {solo_admin} exigen ser el")
        print(f"  administrador: {100*solo_admin/con_puerta:.1f}%.")
    print(f"  Rutas que pasan por `authenticate_request` (dependencia global): "
          f"{con_authenticate}/{n_rutas}.")

    # ── O1.2 · puertas llamadas desde el cuerpo ──────────────────────────
    import re as _re
    from pathlib import Path as _Path

    raiz = _Path(__file__).resolve().parents[1]
    encontradas: list[tuple[str, int, str]] = []
    for py in (raiz / "backend" / "app").rglob("*.py"):
        if py.name == "require_ens_role.py":
            continue  # su definicion, no una llamada
        texto = py.read_text("utf-8", errors="ignore")
        for i, linea in enumerate(texto.splitlines(), 1):
            sin_com = linea.split("#", 1)[0]
            for puerta in PUERTAS_EN_CUERPO:
                if _re.search(rf"\bawait\s+{puerta}\s*\(", sin_com):
                    encontradas.append((str(py.relative_to(raiz)), i, puerta))

    print()
    print("  Puertas llamadas desde el CUERPO (no salen en OpenAPI · ver cabecera):")
    if not encontradas:
        print("    ninguna")
    else:
        for fich, ln, puerta in sorted(encontradas):
            print(f"    {puerta:26s} {fich}:{ln}")
        print(f"    TOTAL: {len(encontradas)} llamadas en "
              f"{len({f for f, _, _ in encontradas})} ficheros")
        print("    Estas rutas exigen ADEMAS ser el titular de un rol ENS del")
        print("    proyecto (RD 311/2022 art. 11), cosa que las tres puertas de")
        print("    poblacion de arriba no comprueban.")

    if detalle:
        print()
        print(f"Caminos que pasan por {args.detalle} ({len(detalle)}):")
        print("\n".join(sorted(detalle)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
