"""Genera el ARTEFACTO que recibe el usuario con las dos logicas y lo diferencia.

LA REGLA QUE IMPLEMENTA (bloque O, retroactiva a N)
    Un arreglo de calculo normativo NO esta cerrado hasta que cambia el
    documento que recibe el usuario. Si el fichero sale identico, no esta
    arreglado.

    Es exactamente el fallo que destapo O1: `medidas_aplicables` estaba escrita,
    probada con un test dorado y documentada en un ADR, y la DdA que el cliente
    firma seguia saliendo del camino viejo porque nadie la habia enchufado. Los
    tests pasaban. El documento no cambiaba.

QUE HACE
    Sobre la MISMA categorizacion, construye la DdA con las dos rutas:

      ANTES · `_measure_applies(measure, category)` — solo eje categoria, que es
              como se generaba hasta el commit 13030b0.
      AHORA · `medidas_aplicables(categoria, niveles)` — los dos ejes del Anexo
              II punto 5, con NO_AFECTADA sin adscribir (Anexo I punto 3).

    Y enseña el diferencial: cuantas medidas entran y salen, cuales, y por que.
    No compara tablas de la base: compara la LISTA DE MEDIDAS que acaba impresa
    en el acta E-012 y en la DdA que se firma.

Uso:
    docker run --rm -v "$PWD:/app" -w /app \\
      --entrypoint python fulkro/backend:test backend/scripts/diferencial_artefactos.py
"""
from __future__ import annotations

import json

from backend.app.motors.m01_categorization.aplicabilidad import (
    DIMENSIONES_ENS,
    NO_AFECTADA,
    medidas_aplicables,
)
from backend.app.motors.m03_dda.anexo2_rd311_2022 import (
    ANEXO_II_RD311,
    EJE_Y_DIMENSIONES,
)

_COLUMNA = {"BASICA": 0, "MEDIA": 1, "ALTA": 2}


def dda_logica_vieja(categoria: str) -> set[str]:
    """Lo que generaba `_measure_applies`: la celda de la categoria y ya."""
    i = _COLUMNA[categoria]
    return {
        codigo for codigo, entrada in ANEXO_II_RD311.items()
        if entrada[1 + i]
    }


def dda_logica_nueva(categoria: str, niveles: dict[str, str]) -> dict:
    return medidas_aplicables(categoria, niveles, exigir_alguna_afectada=False)


def diferencial(nombre: str, categoria: str, niveles: dict[str, str]) -> dict:
    antes = dda_logica_vieja(categoria)
    ahora = dda_logica_nueva(categoria, niveles)
    salen = sorted(antes - set(ahora))
    entran = sorted(set(ahora) - antes)

    print(f"\n{'=' * 74}")
    print(f"CASO: {nombre}")
    print(f"  categoria {categoria} · " + " · ".join(
        f"{d}={niveles[d]}" for d in DIMENSIONES_ENS))
    print(f"{'=' * 74}")
    print(f"  ANTES (solo eje categoria) : {len(antes):2d} medidas")
    print(f"  AHORA (los dos ejes)       : {len(ahora):2d} medidas")
    print(f"  DIFERENCIA                 : {len(ahora) - len(antes):+d}")

    if not salen and not entran:
        print("\n  ARTEFACTO IDENTICO · el arreglo NO ha cambiado el documento.")
    for codigo in salen:
        eje, ini = EJE_Y_DIMENSIONES[codigo]
        print(f"  - {codigo:11s} {ANEXO_II_RD311[codigo][0][:44]:46s} "
              f"(se exige por {ini or eje})")
    for codigo in entran:
        print(f"  + {codigo:11s} {ANEXO_II_RD311[codigo][0][:44]:46s} "
              f"({ahora[codigo].explica()})")

    return {
        "caso": nombre, "categoria": categoria, "niveles": niveles,
        "antes": len(antes), "ahora": len(ahora),
        "salen": salen, "entran": entran,
        "artefacto_cambia": bool(salen or entran),
    }


def main() -> int:
    casos = [
        ("BASICA · trazabilidad no afectada", "BASICA",
         {"D": "BAJO", "I": "BAJO", "C": "BAJO", "A": "BAJO", "T": NO_AFECTADA}),
        ("MEDIA · disponibilidad no afectada", "MEDIA",
         {"D": NO_AFECTADA, "I": "MEDIO", "C": "MEDIO", "A": "MEDIO", "T": "MEDIO"}),
        ("MEDIA · solo confidencialidad afectada", "MEDIA",
         {d: NO_AFECTADA for d in DIMENSIONES_ENS} | {"C": "MEDIO"}),
        ("ALTA · todo afectado (control)", "ALTA",
         dict.fromkeys(DIMENSIONES_ENS, "ALTO")),
    ]
    resultados = [diferencial(*c) for c in casos]

    cambian = sum(1 for r in resultados if r["artefacto_cambia"])
    print(f"\n{'=' * 74}")
    print(f"RESUMEN · {cambian} de {len(resultados)} casos cambian el artefacto.")
    if cambian == 0:
        print("  El arreglo NO llega al documento. NO esta cerrado.")
        return 1
    print("  El arreglo llega al documento que recibe el usuario.")
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
