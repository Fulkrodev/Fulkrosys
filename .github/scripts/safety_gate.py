#!/usr/bin/env python3
"""Gate de `safety` para CI: convierte el informe JSON en un veredicto honesto.

Problema que resuelve
---------------------
La versión anterior de este gate vivía incrustada en `security-scan.yml` y era
inofensiva por dos motivos independientes, ambos medidos el 2026-09-10:

1. La invocación era inválida para safety 3.x. `safety check --json --output
   safety-report.json --continue-on-error` falla con «Invalid value for
   '--output': 'safety-report.json' is not one of 'screen', 'text', 'json',
   'bare', 'html'» y sale con código 2 SIN escribir informe. La ruta de fichero
   va en `--save-json`, no en `--output`.
2. El parser hacía `except Exception: sys.exit(0)`. Como el informe no existía,
   entraba siempre por esa rama y el job salía VERDE. Un `|| true` en el paso
   remataba la máscara.

Y aun con informe, el filtro `severity == 'critical'` no podía saltar nunca: en
el nivel gratuito (sin API key) safety deja `severity: null` en las 102
vulnerabilidades del informe de ejemplo que se midió. Medición:

    $ python -c "import json;r=json.load(open('sr.json'));
      print(len(r['vulnerabilities']), {v['severity'] for v in r['vulnerabilities']})"
    102 {None}

Política (decidida y documentada, no heredada)
----------------------------------------------
Tres casos distintos, tres desenlaces distintos:

* La herramienta REVIENTA (código de salida desconocido, informe ausente, JSON
  ilegible, o JSON válido con un esquema que no reconocemos)  -> el gate FALLA.
  Un fallo de la herramienta no puede seguir pareciéndose a «no hay
  vulnerabilidades». Éste es el cambio de fondo respecto al parser anterior.
* La herramienta CORRE y encuentra vulnerabilidades -> AVISA (anotación
  `::warning` + resumen del job) y NO bloquea, salvo que exista fichero de
  baseline (ver abajo), en cuyo caso cualquier ID nuevo SÍ bloquea.
* La herramienta CORRE limpia (0 vulnerabilidades) -> pasa.

Por qué «avisa» y no «bloquea» cuando hay hallazgos: sin API key no hay campo de
severidad, así que un umbral por severidad es literalmente inimplementable, y
bloquear ante *cualquier* vulnerabilidad dejaría `main` en rojo permanente sobre
un conjunto de avisos que nadie ha triado todavía. El mecanismo para cerrar ese
hueco sin números inventados es el baseline: se ejecuta el gate una vez, se
promueve la lista observada a `.github/safety-baseline.json`, y a partir de ahí
cualquier vulnerabilidad NUEVA bloquea. Mientras ese fichero no exista, el gate
lo dice en el resumen en vez de fingir que no hay hueco.

Uso:
    python .github/scripts/safety_gate.py \
        --report safety-report.json --tool-exit-code "$rc" \
        [--baseline .github/safety-baseline.json]

Códigos de salida: 0 = pasa (con o sin aviso) · 1 = bloquea.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Códigos de salida de safety que significan «la herramienta corrió»:
#   0  -> sin vulnerabilidades
#   64 -> corrió y encontró vulnerabilidades (medido con safety 3.8.1)
# Cualquier otro (1 error interno, 2 error de uso, 127 no instalado, 137 OOM...)
# es un fallo de la herramienta y bloquea.
CODIGOS_QUE_CORRIERON = {0, 64}


def _resumen(texto: str) -> None:
    """Escribe en el resumen del job de GitHub, si estamos dentro de uno."""
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as fh:
            fh.write(texto + "\n")
    print(texto)


def _bloquea(motivo: str) -> int:
    _resumen(f"### safety · BLOQUEA\n\n{motivo}")
    print(f"::error title=safety::{motivo.splitlines()[0]}", file=sys.stderr)
    return 1


def extraer_vulnerabilidades(datos: object) -> list[dict]:
    """Devuelve la lista de vulnerabilidades, o lanza ValueError si el esquema
    no es ninguno de los conocidos.

    Reconocer el esquema de forma POSITIVA es lo que permite distinguir
    «informe limpio» de «safety cambió el formato». El parser anterior no lo
    hacía: cualquier JSON sin la clave `vulnerabilities` se leía como limpio.
    """
    # safety check --output json --save-json  (3.x, y 2.x)
    if isinstance(datos, dict) and isinstance(datos.get("vulnerabilities"), list):
        if "report_meta" not in datos and "scanned_packages" not in datos:
            raise ValueError(
                "dict con 'vulnerabilities' pero sin 'report_meta' ni "
                "'scanned_packages': no parece un informe de safety check",
            )
        return datos["vulnerabilities"]
    # safety scan --output json (3.x, formato nuevo)
    if isinstance(datos, dict) and isinstance(datos.get("scan_results"), dict):
        deps = datos["scan_results"].get("dependencies", [])
        vulns: list[dict] = []
        for dep in deps if isinstance(deps, list) else []:
            for spec in dep.get("specifications", []):
                vulns.extend(spec.get("vulnerabilities", {}).get("known_vulnerabilities", []))
        return vulns
    # safety check --json de versiones antiguas: lista pelada
    if isinstance(datos, list):
        return [v if isinstance(v, dict) else {"vulnerability_id": str(v)} for v in datos]
    raise ValueError(
        f"esquema no reconocido (tipo raíz {type(datos).__name__}, "
        f"claves {sorted(datos)[:8] if isinstance(datos, dict) else 'n/a'})",
    )


def identificador(vuln: dict) -> str:
    for clave in ("vulnerability_id", "CVE", "id"):
        valor = vuln.get(clave)
        if valor:
            return str(valor)
    return f"{vuln.get('package_name', '?')}@{vuln.get('analyzed_version', '?')}"


def main() -> int:
    p = argparse.ArgumentParser(description="Gate de safety para CI")
    p.add_argument("--report", required=True, help="ruta del informe JSON de safety")
    p.add_argument(
        "--tool-exit-code", type=int, required=True,
        help="código de salida con el que terminó safety",
    )
    p.add_argument(
        "--baseline", default="",
        help="JSON con la lista de IDs ya conocidos; si existe, un ID nuevo bloquea",
    )
    args = p.parse_args()

    # Caso 1 · la herramienta reventó. Esto se comprueba ANTES de mirar el
    # informe: un informe viejo de otra ejecución no puede tapar un crash.
    if args.tool_exit_code not in CODIGOS_QUE_CORRIERON:
        return _bloquea(
            f"safety terminó con código {args.tool_exit_code}, que no es ni 0 "
            f"(limpio) ni 64 (con hallazgos): la herramienta no llegó a "
            f"analizar nada. Revisa el log del paso anterior.",
        )

    ruta = Path(args.report)
    # Caso 2 · informe ausente.
    if not ruta.is_file():
        return _bloquea(
            f"safety salió con código {args.tool_exit_code} pero no escribió "
            f"'{ruta}'. La ruta del informe va en --save-json; --output sólo "
            f"acepta un FORMATO (screen/text/json/bare/html).",
        )

    bruto = ruta.read_text(encoding="utf-8", errors="replace")
    # Caso 3 · informe vacío o JSON corrupto.
    if not bruto.strip():
        return _bloquea(f"'{ruta}' existe pero está vacío (0 bytes útiles).")
    try:
        datos = json.loads(bruto)
    except json.JSONDecodeError as exc:
        return _bloquea(f"'{ruta}' no es JSON válido: {exc}")

    # Caso 4 · JSON válido con un esquema que no sabemos leer.
    try:
        vulns = extraer_vulnerabilidades(datos)
    except ValueError as exc:
        return _bloquea(
            f"el informe de safety cambió de formato y este gate no sabe "
            f"leerlo: {exc}. Actualiza extraer_vulnerabilidades() en "
            f".github/scripts/safety_gate.py.",
        )

    # Caso 5 · corrió limpia.
    if not vulns:
        _resumen(
            "### safety · limpio\n\n"
            "0 vulnerabilidades en el informe (esquema reconocido y leído).",
        )
        return 0

    # Caso 6 · corrió y encontró hallazgos.
    ids = sorted({identificador(v) for v in vulns})
    paquetes = sorted({str(v.get("package_name", "?")) for v in vulns})
    ruta_baseline = Path(args.baseline) if args.baseline else None

    if ruta_baseline is not None and ruta_baseline.is_file():
        try:
            conocidos = set(json.loads(ruta_baseline.read_text(encoding="utf-8"))["ids"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return _bloquea(f"baseline '{ruta_baseline}' ilegible: {exc}")
        nuevos = [i for i in ids if i not in conocidos]
        if nuevos:
            return _bloquea(
                f"{len(nuevos)} vulnerabilidad(es) NUEVA(s) respecto al "
                f"baseline: {', '.join(nuevos[:20])}"
                + (" ..." if len(nuevos) > 20 else ""),
            )
        _resumen(
            f"### safety · sin novedades\n\n{len(ids)} vulnerabilidades, todas "
            f"ya presentes en `{ruta_baseline}`.",
        )
        return 0

    _resumen(
        f"### safety · {len(ids)} vulnerabilidades (AVISO, no bloquea)\n\n"
        f"Paquetes afectados ({len(paquetes)}): {', '.join(paquetes[:25])}"
        + (" ..." if len(paquetes) > 25 else "")
        + "\n\nNo bloquea porque el nivel gratuito de safety no rellena el campo "
        "`severity` (queda a `null`), así que no hay umbral de severidad que "
        "aplicar. Para que esto pase a bloquear ante hallazgos NUEVOS, promueve "
        "la lista observada a `.github/safety-baseline.json` con el formato "
        '`{\"ids\": [...]}` (el artefacto `safety-report` del run trae el informe '
        "completo). En cuanto ese fichero exista, cualquier ID que no esté en él "
        "tumba el job.",
    )
    print(f"::warning title=safety::{len(ids)} vulnerabilidades conocidas sin triar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
