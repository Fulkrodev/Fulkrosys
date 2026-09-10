#!/usr/bin/env python3
"""Detector de tests sospechosos de verdad vacua.

Un test es *vacuamente verdadero* cuando pasa porque no hay datos que puedan
contradecirlo, no porque el sistema haga lo correcto. El caso canonico es un
assert de la forma "no hay huerfanos" o "X no aparece en los resultados": sobre
una tabla vacia se satisface solo. Ese test da verde para siempre y no vuelve a
comprobar nada, que es peor que no tenerlo, porque ademas cuenta como cobertura.

La deteccion es una consecuencia de esa definicion: se provisiona una base con
el esquema COMPLETO pero SIN DATOS y se ejecuta la suite que requiere base de
datos. Todo test que pase ahi es SOSPECHOSO.

SOSPECHOSO NO ES LO MISMO QUE VACUO, y esta distincion es el nucleo de la
herramienta. Hay tests que pasan legitimamente sobre una base vacia:

  * los que comprueban que una consulta NO devuelve nada (su sujeto es el vacio);
  * los de manejo de errores (esperan una excepcion o un 404);
  * los que validan constraints insertando ellos mismos sus datos;
  * los que crean sus propias fixtures dentro del test.

Por eso la salida se llama `sospechosos` y trae una columna `veredicto` vacia:
cada linea necesita que una persona la mire. Publicar el recuento de sospechosos
como si fueran vacuos seria cometer, a escala, el error que la herramienta
existe para detectar.

Uso:
    python scripts/vacuity_check.py --database-url URL [--out informe.csv]

La base que se le pase debe estar en `alembic head`, con los roles de RLS
creados y sin datos de negocio. El detector NO la provisiona: se niega a
ejecutarse si encuentra datos, para no dar un resultado enganyoso.
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Tablas que las propias migraciones siembran: su contenido es esquema, no datos
# de negocio, y su presencia no invalida la medicion.
SEEDED_BY_MIGRATIONS = {
    "magerit_risk_matrix", "fulkro_ropa_treatments", "whatsapp_critical_events_routing",
    "pricing_config", "auth_users", "admin_settings", "audit_log", "pricing_catalog",
    "alembic_version",
}


def assert_database_is_empty(database_url: str) -> None:
    """Aborta si la base tiene datos de negocio: mediria otra cosa."""
    import sqlalchemy

    sync_url = database_url.replace("+asyncpg", "+psycopg2")
    engine = sqlalchemy.create_engine(sync_url)
    try:
        with engine.connect() as conn:
            head = conn.execute(sqlalchemy.text(
                "SELECT to_regclass('public.alembic_version')"
            )).scalar()
            if head is None:
                raise SystemExit(
                    "ABORTA: la base no tiene tabla alembic_version, o sea que no se "
                    "provisiono con migraciones.\n"
                    "El detector necesita el esquema COMPLETO para que un test que pase "
                    "signifique algo:\n"
                    "sobre un esquema parcial los tests fallan por tablas ausentes, no por "
                    "falta de datos."
                )
            head = conn.execute(sqlalchemy.text(
                "SELECT version_num FROM alembic_version"
            )).scalar()
            rows = conn.execute(sqlalchemy.text(
                "SELECT relname, n_live_tup FROM pg_stat_user_tables WHERE n_live_tup > 0"
            )).fetchall()
    finally:
        engine.dispose()

    intrusos = [(t, n) for t, n in rows if t not in SEEDED_BY_MIGRATIONS]
    if intrusos:
        detalle = ", ".join(f"{t}={n}" for t, n in intrusos)
        raise SystemExit(
            f"ABORTA: la base tiene datos de negocio ({detalle}).\n"
            "El detector solo es valido contra una base vacia: con datos, un test\n"
            "que pase no dice nada sobre vacuidad."
        )
    print(f"  base en alembic head={head}, sin datos de negocio", file=sys.stderr)



def resolve_location(classname: str, name: str) -> tuple[str, str, str]:
    """Deriva (fichero, linea, nodeid) de un <testcase> del JUnit XML.

    pytest emite en el XML solo classname/name/time: no hay atributos file ni
    line, asi que hay que reconstruirlos. El classname es la ruta del modulo con
    puntos ("tests.corpus.test_hybrid_search") y, si el test vive en una clase,
    esa clase va al final en CamelCase. La linea se busca en el fuente porque no
    viaja en el informe.
    """
    partes = classname.split(".")
    clase = ""
    if partes and partes[-1][:1].isupper():
        clase = partes.pop()
    fichero = "backend/" + "/".join(partes) + ".py"
    if not (REPO / fichero).exists():
        return (fichero, "", f"{fichero}::{name}")

    # El nombre puede venir parametrizado: test_x[caso-1] -> test_x
    base = name.split("[", 1)[0]
    linea = ""
    try:
        for i, ln in enumerate((REPO / fichero).read_text(encoding="utf-8",
                                                          errors="replace").splitlines(), 1):
            stripped = ln.lstrip()
            if stripped.startswith(("def " + base + "(", "async def " + base + "(")):
                linea = str(i)
                break
    except OSError:
        pass

    nodeid = f"{fichero}::{clase}::{name}" if clase else f"{fichero}::{name}"
    return (fichero, linea, nodeid)


def run_suite(database_url: str, marker: str) -> Path:
    """Ejecuta la suite marcada y devuelve el informe JUnit XML de pytest.

    Se usa --junit-xml y no --json-report a proposito: el primero viene con
    pytest, el segundo es un plugin aparte. Un detector que necesita instalar
    algo mas es un detector que no se ejecuta.
    """
    report = Path(tempfile.mkdtemp()) / "report.xml"
    env = {
        **os.environ,
        "DATABASE_URL": database_url,
        "DATABASE_URL_SYNC": database_url.replace("+asyncpg", "+psycopg2"),
        "FULKRO_TESTING": "1",
    }
    cmd = [
        sys.executable, "-m", "pytest", "backend/tests/",
        "-m", marker, "-p", "no:cacheprovider", "-q", "--no-header",
        f"--junit-xml={report}", "--tb=no", "-p", "no:cov",
    ]
    print(f"  $ {' '.join(cmd[2:])}", file=sys.stderr)
    subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--database-url", default="",
                    help="URL de una base en alembic head, con roles RLS y SIN datos")
    ap.add_argument("--marker", default="requires_db",
                    help="marcador de los tests que necesitan base (por defecto: requires_db)")
    ap.add_argument("--out", type=Path, default=REPO / "out" / "vacuity_suspects.csv")
    ap.add_argument("--baseline", type=Path, default=None,
                    help="fichero de linea base: si se pasa, el proceso sale con codigo 1 "
                         "SOLO si aparecen sospechosos NUEVOS que no esten en ella")
    ap.add_argument("--counters", type=Path, default=None,
                    help="JSONL de scripts/vacuity_plugin.py con filas escritas/leidas por test")
    ap.add_argument("--report", type=Path, default=None,
                    help="reutiliza un JUnit XML ya generado en vez de reejecutar la suite "
                         "(la pasada completa tarda >10 min; esto permite re-triar sin repetirla)")
    args = ap.parse_args()

    if args.report:
        print(f"[1/3] reutilizando informe existente: {args.report}", file=sys.stderr)
        print("[2/3] (suite no reejecutada)", file=sys.stderr)
        report = args.report
    else:
        print("[1/3] comprobando que la base esta vacia...", file=sys.stderr)
        assert_database_is_empty(args.database_url)
        print(f"[2/3] ejecutando la suite -m {args.marker} contra la base vacia...", file=sys.stderr)
        report = run_suite(args.database_url, args.marker)
    if not report.exists():
        raise SystemExit("ABORTA: pytest no genero informe JUnit.")

    import xml.etree.ElementTree as ET

    root = ET.parse(report).getroot()
    tests, suspects = [], []
    for case in root.iter("testcase"):
        # Un testcase SIN hijos paso: failure/error/skipped se emiten como hijos.
        estado = next((c.tag for c in case), "passed")
        tests.append(case)
        if estado == "passed":
            suspects.append(case)

    contadores = {}
    if args.counters and args.counters.exists():
        import json as _json
        for ln in args.counters.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r = _json.loads(ln)
                contadores[r["nodeid"]] = r
        print(f"  contadores de ejecucion cargados: {len(contadores)} tests", file=sys.stderr)

    escritos = 0
    escritas_filas: list[tuple[str, str, str]] = []
    print("[3/3] escribiendo el informe...", file=sys.stderr)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["fichero", "linea", "test_id", "filas_escritas",
                    "filas_leidas_reales", "sentencias", "veredicto", "nota_triaje"])
        filas = [resolve_location(c.get("classname") or "", c.get("name") or "")
                 for c in suspects]
        for fichero, linea, nodeid in sorted(filas, key=lambda r: (r[0], int(r[1] or 0))):
            # El plugin usa el nodeid de pytest, cuyo rootdir es backend/.
            c = contadores.get(nodeid.removeprefix("backend/"), {})
            if contadores and not c:
                continue  # sin contadores no se puede aplicar el filtro fino
            if contadores and (c.get("filas_escritas") or c.get("filas_leidas_reales")):
                continue  # escribio o leyo filas reales: no es sospechoso
            w.writerow([fichero, linea, nodeid, c.get("filas_escritas", ""),
                        c.get("filas_leidas_reales", ""), c.get("sentencias", ""), "", ""])
            escritas_filas.append((fichero, linea, nodeid))
            escritos += 1

    total = len(tests)
    print(file=sys.stderr)
    print(f"  ejecutados : {total}", file=sys.stderr)
    if contadores:
        print(f"  pasaron sin datos          : {len(suspects)}", file=sys.stderr)
        print(f"  SOSPECHOSOS (3 senales)    : {escritos}", file=sys.stderr)
        print("     = pasaron + escribieron 0 filas + leyeron 0 filas reales", file=sys.stderr)
    else:
        print(f"  SOSPECHOSOS: {len(suspects)}  (solo senal 1: pasaron sin datos)", file=sys.stderr)
        print("     AVISO: sin --counters el filtro es grueso y sobre-marca.", file=sys.stderr)
    print(f"  fallaron   : {total - len(suspects)}  (se comportan como se espera sin datos)", file=sys.stderr)
    print(file=sys.stderr)
    print(f"  informe -> {args.out}", file=sys.stderr)
    print("  SOSPECHOSO != VACUO: la columna `veredicto` esta vacia a proposito.", file=sys.stderr)
    print("  Cada linea necesita triaje humano antes de contarla como hallazgo.", file=sys.stderr)

    if not args.baseline:
        return 0

    # Modo linea base. La puerta NO se cierra sobre el total heredado: se cierra
    # solo sobre lo que aparezca despues. Una puerta que tumba el build con 299
    # sospechosos heredados no la activa nadie, y una puerta que nadie activa no
    # protege de nada.
    if not args.baseline.exists():
        print(f"\n  AVISO: no existe {args.baseline}; no hay nada contra lo que comparar.",
              file=sys.stderr)
        return 0
    conocidos = {ln.strip() for ln in args.baseline.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.startswith("#")}
    actuales = {fila[2] for fila in escritas_filas}
    nuevos = sorted(actuales - conocidos)
    resueltos = sorted(conocidos - actuales)

    print(file=sys.stderr)
    print(f"  linea base : {len(conocidos)}", file=sys.stderr)
    print(f"  resueltos  : {len(resueltos)}", file=sys.stderr)
    print(f"  NUEVOS     : {len(nuevos)}", file=sys.stderr)
    if resueltos:
        print("\n  Sospechosos de la linea base que ya no aparecen (actualizala):", file=sys.stderr)
        for r in resueltos[:20]:
            print(f"    - {r}", file=sys.stderr)
    if nuevos:
        print("\n  SOSPECHOSOS NUEVOS (no estaban en la linea base):", file=sys.stderr)
        for r in nuevos:
            print(f"    + {r}", file=sys.stderr)
        print("\n  Cada uno necesita triaje: si es legitimo, anadelo a la linea base;", file=sys.stderr)
        print("  si es vacuo, arregla la asercion.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
