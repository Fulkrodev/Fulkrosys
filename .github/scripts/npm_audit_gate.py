#!/usr/bin/env python3
"""Puerta de npm audit: CRITICAL y HIGH cortan, salvo los acotados por escrito.

Por que existe, y no un `npm audit --audit-level=critical` a secas:

  - `npm audit` devuelve 1 si hay CUALQUIER aviso de la severidad pedida o
    superior, y no distingue entre "aviso nuevo" y "aviso conocido, con su
    motivo escrito y su fecha de revision". Un rojo permanente se convierte en
    ruido que la gente aprende a ignorar, que es la misma enfermedad que un
    verde que no comprueba nada.
  - Un fallo de la herramienta (informe ausente, JSON corrupto, esquema
    cambiado) NO puede pasar por exito. Aqui bloquea.

El umbral, y por que es este.

  Hasta 2026-09-15 este gate solo miraba `critical`. El dia que se subio a
  `high`, el recuento medido con `npm audit --production --json` sobre el
  frontend era:

      {"info": 0, "low": 0, "moderate": 0, "high": 1, "critical": 1, "total": 2}

  Es decir: subir el umbral no dejo el build rojo de forma permanente, que es
  la unica razon de peso para no subirlo. Los dos que quedan estan en la lista
  con su motivo y su fecha: el `critical` de next (dos RCE no alcanzables en
  el despliegue de referencia) y el `high` de la copia de postcss que next
  trae dentro, que solo se arregla saltando a next 16.

  Antes de subirlo se arreglaron los que si tenian arreglo sin cambio mayor:
  `npm audit fix --package-lock-only` subio nanoid 3.3.11 -> 3.3.19, postcss
  8.5.10 -> 8.5.28 y postcss-selector-parser 6.1.2 -> 6.1.4, y con ese arbol
  `tsc` sigue en 0 y `next build` en verde.

  Ojo a un detalle que cuesta una discusion: los SIETE avisos `high` que se
  ven en el repositorio salen de `npm audit` SIN `--production`. Cinco de
  ellos son dependencias de desarrollo (eslint-config-next,
  @next/eslint-plugin-next, glob, brace-expansion, js-yaml) y nunca han pasado
  por esta puerta, porque el informe que la alimenta se genera con
  `--production`. Se cuentan e informan aparte, sin tumbar el build: no viajan
  al contenedor, pero que no se vean no es lo mismo que que no existan.

Reglas:
  informe ausente / JSON invalido / esquema desconocido -> BLOQUEA (codigo 2)
  CRITICAL o HIGH fuera de la lista                     -> BLOQUEA (codigo 1)
  CRITICAL o HIGH en la lista, con fecha vigente        -> avisa y pasa
  CRITICAL o HIGH en la lista con fecha CADUCADA        -> BLOQUEA (codigo 1)
  MODERATE y por debajo                                 -> avisa y pasa
  avisos de dependencias de desarrollo                  -> se cuentan e informan

Uso:  python3 .github/scripts/npm_audit_gate.py <informe.json> <lista.json>
      python3 .github/scripts/npm_audit_gate.py <informe.json> <lista.json> \
              --informe-dev <informe-con-dev.json>
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


#: Severidades que cortan el build. Subido de {"critical"} a {"critical",
#: "high"} el 2026-09-15; el recuento de ese dia esta en la cabecera.
_CORTAN = frozenset({"critical", "high"})


def _muere(msg: str, codigo: int = 2) -> None:
    print(f"[GATE npm audit] BLOQUEA · {msg}", file=sys.stderr)
    raise SystemExit(codigo)


def _informar_dependencias_de_desarrollo(
    argv: list[str], en_produccion: set[str],
) -> None:
    """Cuenta los avisos que solo afectan a herramientas de construccion.

    NO tumban el build, y por una razon concreta: no viajan al contenedor de
    produccion. Pero que no se vean tampoco es sano —`npm audit --production`
    los oculta enteros— asi que aqui se cuentan y se nombran.
    """
    if "--informe-dev" not in argv:
        return
    ruta = Path(argv[argv.index("--informe-dev") + 1])
    if not ruta.exists():
        print(f"[GATE npm audit] aviso: no existe {ruta}, no se informa de dev")
        return
    try:
        informe = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[GATE npm audit] aviso: {ruta} no es JSON valido ({exc})")
        return
    por_severidad = informe.get("metadata", {}).get("vulnerabilities", {})
    # Lo que aparece con dev y NO aparece en el informe de produccion es,
    # exactamente, lo que esta puerta nunca ha mirado.
    solo_dev = sorted(set(informe.get("vulnerabilities", {})) - en_produccion)
    print(
        "[GATE npm audit] con dependencias de DESARROLLO incluidas: "
        f"{ {k: v for k, v in por_severidad.items() if v} }"
    )
    if not solo_dev:
        print("[GATE npm audit] nada exclusivo de desarrollo")
        return
    print(
        f"[GATE npm audit] {len(solo_dev)} paquete(s) SOLO de desarrollo: "
        + ", ".join(solo_dev)
        + "\n                 NO tumban el build: no viajan al contenedor de "
        "produccion, y el informe que alimenta esta puerta se genera con "
        "--production, que los oculta enteros. Se cuentan para que no "
        "desaparezcan de la vista."
    )


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 5):
        _muere(
            f"uso: {argv[0]} <informe.json> <lista.json> "
            f"[--informe-dev <informe-con-dev.json>]"
        )

    informe_p, lista_p = Path(argv[1]), Path(argv[2])

    # ── el informe TIENE que existir y ser legible: si no, es un crash ──
    if not informe_p.exists():
        _muere(f"no existe el informe {informe_p}: npm audit no llego a escribirlo")
    try:
        informe = json.loads(informe_p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _muere(f"el informe {informe_p} no es JSON valido ({exc})")
    if not isinstance(informe, dict) or "vulnerabilities" not in informe:
        _muere(
            f"el informe {informe_p} no tiene la forma esperada "
            f"(falta 'vulnerabilities'): puede que npm haya cambiado de esquema"
        )

    try:
        lista = json.loads(lista_p.read_text(encoding="utf-8"))
        aceptados = {a["ghsa"]: a for a in lista["avisos_aceptados"]}
    except Exception as exc:  # noqa: BLE001 — la lista rota tambien bloquea
        _muere(f"no se pudo leer la lista de avisos acotados {lista_p} ({exc})")

    hoy = date.today()
    criticos_nuevos: list[tuple[str, str, str]] = []
    criticos_acotados: list[tuple[str, str]] = []
    caducados: list[tuple[str, str]] = []
    por_severidad: dict[str, int] = {}

    for paquete, v in informe["vulnerabilities"].items():
        sev = v.get("severity", "?")
        por_severidad[sev] = por_severidad.get(sev, 0) + 1
        for via in v.get("via", []):
            if not isinstance(via, dict) or via.get("severity") not in _CORTAN:
                continue
            ghsa = (via.get("url") or "").rsplit("/", 1)[-1]
            titulo = via.get("title", "(sin titulo)")
            entrada = aceptados.get(ghsa)
            if entrada is None:
                criticos_nuevos.append((paquete, ghsa, titulo))
                continue
            limite = entrada.get("revisar_antes_de")
            if limite and date.fromisoformat(limite) < hoy:
                caducados.append((ghsa, limite))
            else:
                criticos_acotados.append((ghsa, titulo))

    print("[GATE npm audit] recuento por severidad:", por_severidad or "sin avisos")

    for ghsa, titulo in sorted(set(criticos_acotados)):
        e = aceptados[ghsa]
        print(
            f"[GATE npm audit] AVISO ACOTADO · {e['severidad'].upper()} · {ghsa} ({e['paquete']} "
            f"{e['version_instalada']}) · {titulo}\n"
            f"                 se arregla en {e['arreglado_en']} · "
            f"revisar antes de {e['revisar_antes_de']}"
        )

    if caducados:
        for ghsa, limite in caducados:
            print(
                f"[GATE npm audit] CADUCADO · {ghsa} debia revisarse antes "
                f"de {limite} y sigue aqui",
                file=sys.stderr,
            )
        _muere(f"{len(caducados)} aviso(s) acotado(s) con la fecha pasada", 1)

    if criticos_nuevos:
        for paquete, ghsa, titulo in criticos_nuevos:
            print(f"[GATE npm audit] SIN ACOTAR · {paquete} · {ghsa} · {titulo}",
                  file=sys.stderr)
        _muere(
            f"{len(criticos_nuevos)} aviso(s) CRITICAL/HIGH sin acotar. Arreglalo, o "
            f"anadelo a .github/npm-audit-allowlist.json con su motivo escrito y "
            f"su fecha de revision.",
            1,
        )

    _informar_dependencias_de_desarrollo(argv, set(informe["vulnerabilities"]))

    print("[GATE npm audit] PASA · ningun CRITICAL ni HIGH sin acotar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
