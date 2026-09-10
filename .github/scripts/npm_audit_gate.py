#!/usr/bin/env python3
"""Puerta de npm audit: los CRITICAL cortan, salvo los acotados por escrito.

Por que existe, y no un `npm audit --audit-level=critical` a secas:

  - `npm audit` devuelve 1 si hay CUALQUIER aviso de la severidad pedida o
    superior, y no distingue entre "aviso nuevo" y "aviso conocido, con su
    motivo escrito y su fecha de revision". Un rojo permanente se convierte en
    ruido que la gente aprende a ignorar, que es la misma enfermedad que un
    verde que no comprueba nada.
  - Un fallo de la herramienta (informe ausente, JSON corrupto, esquema
    cambiado) NO puede pasar por exito. Aqui bloquea.

Reglas:
  informe ausente / JSON invalido / esquema desconocido -> BLOQUEA (codigo 2)
  CRITICAL fuera de la lista                            -> BLOQUEA (codigo 1)
  CRITICAL en la lista, con fecha vigente               -> avisa y pasa
  CRITICAL en la lista con fecha CADUCADA               -> BLOQUEA (codigo 1)
  HIGH y por debajo                                     -> avisa y pasa

Uso:  python3 .github/scripts/npm_audit_gate.py <informe.json> <lista.json>
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


def _muere(msg: str, codigo: int = 2) -> None:
    print(f"[GATE npm audit] BLOQUEA · {msg}", file=sys.stderr)
    raise SystemExit(codigo)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        _muere(f"uso: {argv[0]} <informe.json> <lista.json>")

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
            if not isinstance(via, dict) or via.get("severity") != "critical":
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
            f"[GATE npm audit] AVISO ACOTADO · {ghsa} ({e['paquete']} "
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
            print(f"[GATE npm audit] CRITICO NUEVO · {paquete} · {ghsa} · {titulo}",
                  file=sys.stderr)
        _muere(
            f"{len(criticos_nuevos)} aviso(s) CRITICAL sin acotar. Arreglalo, o "
            f"anadelo a .github/npm-audit-allowlist.json con su motivo escrito y "
            f"su fecha de revision.",
            1,
        )

    print("[GATE npm audit] PASA · ningun CRITICAL sin acotar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
