#!/usr/bin/env python3
"""Comprueba que las descripciones del catálogo ENS no copian el texto anterior.

Contexto. Hasta 2026-09-10 el campo `descripcion` de
``docs/catalogs/ens_measures_catalog_v1.yaml`` era un extracto literal de la
guía CCN-STIC 804 v2017. Este repositorio es público, así que esas
descripciones se reescribieron con redacción propia. Este script mide que la
reescritura es real y que no rompió nada más.

Qué mide, exactamente
---------------------
1. **Copia literal**: para cada medida calcula la secuencia de palabras
   CONSECUTIVAS más larga que comparten la descripción anterior (leída de git)
   y la actual (leída del árbol de trabajo). Normaliza antes de comparar:
   minúsculas, sin tildes, sin puntuación. Falla si alguna medida llega al
   umbral de 8 palabras seguidas.
2. **Integridad**: que el conjunto de `codigo` sea idéntico antes y después, y
   que ningún campo distinto de `descripcion` haya cambiado en ninguna medida.

Qué NO mide (dicho explícitamente, para que nadie lo suponga)
------------------------------------------------------------
NO comprueba que la descripción sea normativamente exacta ni que describa
correctamente la medida. Una descripción inventada, incompleta o equivocada
pasa este script sin problema mientras no repita palabras del original. Esa
revisión es humana y corresponde al consultor ENS.

Uso
---
    python3 scripts/verificar_catalogo_sin_copia_literal.py
    python3 scripts/verificar_catalogo_sin_copia_literal.py --ref <commit>
    python3 scripts/verificar_catalogo_sin_copia_literal.py --umbral 10

`--ref` es la versión con la que se compara; por defecto HEAD. Tras commitear
la reescritura, HEAD ya contiene el texto nuevo: hay que apuntar al commit
ANTERIOR a ella (el script lo detecta y avisa en lugar de dar un rojo mudo).

Dónde se ejecuta: en el HOST. Necesita `git` y PyYAML. La imagen
`fulkro/backend:test` no lleva git, así que dentro del contenedor no funciona;
la guardia que sí corre en CI es
``backend/tests/scripts/test_catalogo_sin_copia_literal.py``.

Sobre el umbral de 8. Medido el 2026-09-10 sobre las 79 medidas reescritas: la
racha común más larga que queda es de 7 palabras ("relación de personas
autorizadas y un sistema", en mp.if.2), así que el margen es de UNA palabra.
Bajarlo a 5 marca español corriente ("del responsable de la información") y da
falsos positivos. Si una edición futura roza el umbral, mírese la racha que
imprime antes de subir el número: puede ser copia de verdad.

Salida: 0 si pasa, 1 si alguna medida copia o si cambió algo que no debía.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - entorno sin PyYAML
    sys.exit("ERROR: falta PyYAML (pip install pyyaml)")

CATALOGO = "docs/catalogs/ens_measures_catalog_v1.yaml"
UMBRAL_POR_DEFECTO = 8
# Marca de que un ref YA contiene la reescritura (comparar contra él no mide nada).
MARCA_REESCRITO = "Redacción propia de FULKRO"


def normalizar(texto: str) -> list[str]:
    """minúsculas, sin tildes, sin puntuación -> lista de palabras."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^a-z0-9ñ]+", " ", t)
    return t.split()


def racha_comun_mas_larga(a: list[str], b: list[str]) -> tuple[int, list[str]]:
    """Palabras consecutivas en común más larga (longest common substring).

    Devuelve (longitud, palabras). DP por filas: O(len(a)*len(b)) en tiempo,
    O(len(b)) en memoria.
    """
    if not a or not b:
        return 0, []
    mejor_len = 0
    mejor_fin_a = 0
    previa = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        actual = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                actual[j] = previa[j - 1] + 1
                if actual[j] > mejor_len:
                    mejor_len = actual[j]
                    mejor_fin_a = i
        previa = actual
    return mejor_len, a[mejor_fin_a - mejor_len:mejor_fin_a]


def cargar_desde_git(ref: str, ruta: str) -> dict:
    try:
        crudo = subprocess.run(
            ["git", "show", f"{ref}:{ruta}"],
            capture_output=True, check=True, text=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        sys.exit(f"ERROR: no se pudo leer {ruta} en {ref}\n{exc.stderr.strip()}")
    return yaml.safe_load(crudo)


def indexar(doc: dict) -> dict[str, dict]:
    return {m["codigo"]: m for m in doc.get("medidas", [])}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--ref", default="HEAD",
                   help="Versión de referencia con la que comparar (por defecto HEAD)")
    p.add_argument("--umbral", type=int, default=UMBRAL_POR_DEFECTO,
                   help=f"Palabras consecutivas que se consideran copia (por defecto {UMBRAL_POR_DEFECTO})")
    args = p.parse_args()

    raiz = Path(__file__).resolve().parent.parent
    trabajo = raiz / CATALOGO
    if not trabajo.exists():
        sys.exit(f"ERROR: no existe {trabajo}")

    doc_antes = cargar_desde_git(args.ref, CATALOGO)
    doc_ahora = yaml.safe_load(trabajo.read_text(encoding="utf-8"))

    marca = str(doc_antes.get("fuentes", {}).get("descripciones", ""))
    if MARCA_REESCRITO in marca:
        print(f"AVISO: la versión de referencia ({args.ref}) YA contiene la reescritura.")
        print("       Comparar el texto nuevo consigo mismo no mide nada: da copia total.")
        print("       Usa --ref <commit anterior a la reescritura>.")
        return 1

    antes = indexar(doc_antes)
    ahora = indexar(doc_ahora)

    print("=" * 72)
    print(f"Catálogo:   {CATALOGO}")
    print(f"Referencia: {args.ref}  ({len(antes)} medidas)")
    print(f"Trabajo:    árbol actual ({len(ahora)} medidas)")
    print(f"Umbral:     {args.umbral} palabras consecutivas")
    print("=" * 72)

    fallos: list[str] = []

    # --- 1. Integridad del conjunto de códigos -----------------------------
    faltan = sorted(set(antes) - set(ahora))
    sobran = sorted(set(ahora) - set(antes))
    if faltan:
        fallos.append(f"CÓDIGOS DESAPARECIDOS ({len(faltan)}): {', '.join(faltan)}")
    if sobran:
        fallos.append(f"CÓDIGOS NUEVOS ({len(sobran)}): {', '.join(sobran)}")

    # --- 2. Ningún campo distinto de `descripcion` cambió -----------------
    cambios_prohibidos: list[str] = []
    for codigo in sorted(set(antes) & set(ahora)):
        va, na = antes[codigo], ahora[codigo]
        claves = set(va) | set(na)
        for clave in sorted(claves):
            if clave == "descripcion":
                continue
            if va.get(clave, "<ausente>") != na.get(clave, "<ausente>"):
                cambios_prohibidos.append(
                    f"  {codigo}.{clave}: {va.get(clave, '<ausente>')!r} -> {na.get(clave, '<ausente>')!r}"
                )
    if cambios_prohibidos:
        fallos.append(
            "CAMPOS QUE NO DEBÍAN CAMBIAR Y CAMBIARON "
            f"({len(cambios_prohibidos)}):\n" + "\n".join(cambios_prohibidos)
        )

    # --- 3. Copia literal --------------------------------------------------
    medidas: list[tuple[str, int, str]] = []
    for codigo in sorted(set(antes) & set(ahora)):
        pal_antes = normalizar(antes[codigo].get("descripcion", ""))
        pal_ahora = normalizar(ahora[codigo].get("descripcion", ""))
        n, racha = racha_comun_mas_larga(pal_antes, pal_ahora)
        medidas.append((codigo, n, " ".join(racha)))

    copiadas = [m for m in medidas if m[1] >= args.umbral]
    if copiadas:
        detalle = "\n".join(
            f"  {c:12} {n:3} palabras seguidas: \"{txt}\""
            for c, n, txt in sorted(copiadas, key=lambda x: -x[1])
        )
        fallos.append(
            f"COPIA LITERAL: {len(copiadas)} medida(s) con {args.umbral}+ "
            f"palabras consecutivas del texto original:\n{detalle}"
        )

    # --- Resumen (se imprime SIEMPRE) --------------------------------------
    longitudes = [n for _, n, _ in medidas] or [0]
    maxima = max(longitudes)
    peor = max(medidas, key=lambda x: x[1]) if medidas else ("-", 0, "")
    media = sum(longitudes) / len(longitudes)
    print(f"Medidas comparadas:        {len(medidas)}")
    print(f"Coincidencia máxima:       {maxima} palabras consecutivas (en {peor[0]})")
    if peor[1]:
        print(f"  texto de esa racha:      \"{peor[2]}\"")
    print(f"Coincidencia media:        {media:.2f} palabras consecutivas")
    print(f"Medidas en el umbral o por encima ({args.umbral}+): {len(copiadas)}")
    print("-" * 72)

    if fallos:
        for f in fallos:
            print(f"FALLO: {f}")
        print("-" * 72)
        print("RESULTADO: ROJO")
        return 1

    print("RESULTADO: VERDE")
    print("Recordatorio: esto NO verifica que las descripciones sean")
    print("normativamente exactas. Eso lo revisa una persona.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
