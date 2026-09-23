#!/usr/bin/env python3
"""Comprueba que las descripciones del catálogo ENS no copian el texto anterior.

Contexto. Hasta 2026-09-10 el campo `descripcion` de
``docs/catalogs/ens_measures_catalog_v1.yaml`` era un extracto literal de la
guía CCN-STIC 804 v2017. Este repositorio es público, así que esas
descripciones se reescribieron con redacción propia. Este script mide que la
reescritura es real y que la copia no vuelve.

Contra qué compara
------------------
Contra ``docs/catalogs/ens_catalog_huella_ccn804.json``: el SHA-256 de cada
racha de 8 palabras consecutivas de las descripciones antiguas. El texto
antiguo no está en el repositorio, ni en el árbol ni en el historial; la
huella basta para detectar la copia sin volver a publicarlo. Antes el script
leía ese texto de git (``--ref <commit>``), y eso obligaba a conservarlo.

Qué mide, exactamente
---------------------
1. **Copia literal**: normaliza cada descripción actual (minúsculas, sin
   tildes, sin puntuación), calcula el SHA-256 de cada racha de 8 palabras y
   falla si alguna está en la huella. Compara contra la huella entera, no solo
   contra la misma medida: copiar la descripción de otra medida también cuenta.
2. **Códigos**: avisa de las medidas actuales que no estaban en el catálogo
   antiguo. No es un fallo (el catálogo puede crecer), pero esa medida no tiene
   contra qué compararse más que la huella global.

Qué NO mide (dicho explícitamente, para que nadie lo suponga)
------------------------------------------------------------
NO comprueba que la descripción sea normativamente exacta ni que describa
correctamente la medida. Una descripción inventada, incompleta o equivocada
pasa este script sin problema mientras no repita palabras del original. Esa
revisión es humana.

Tampoco da la racha común más larga, como hacía antes: con hashes de 8
palabras solo se sabe si hay 8 o más seguidas, no cuántas por debajo. Medido
el 2026-09-10 contra el texto original, la más larga era de 7 palabras
("relación de personas autorizadas y un sistema", en mp.if.2).

Uso
---
    python3 scripts/verificar_catalogo_sin_copia_literal.py

No necesita git. La guardia que corre en CI es
``backend/tests/scripts/test_catalogo_sin_copia_literal.py``, que usa las
mismas funciones.

Salida: 0 si pasa, 1 si alguna medida copia.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - entorno sin PyYAML
    sys.exit("ERROR: falta PyYAML (pip install pyyaml)")

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = "docs/catalogs/ens_measures_catalog_v1.yaml"
HUELLA = "docs/catalogs/ens_catalog_huella_ccn804.json"


def normalizar(texto: str) -> list[str]:
    """minúsculas, sin tildes, sin puntuación -> lista de palabras."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^a-z0-9ñ]+", " ", t)
    return t.split()


def hashes_de_rachas(texto: str, palabras: int) -> dict[str, str]:
    """{sha256: racha} de cada racha de `palabras` palabras seguidas."""
    p = normalizar(texto)
    rachas = (" ".join(p[i:i + palabras]) for i in range(len(p) - palabras + 1))
    return {hashlib.sha256(r.encode()).hexdigest(): r for r in rachas}


def cargar_huella(ruta: Path | None = None) -> tuple[int, set[str], set[str]]:
    """(palabras por racha, todos los hashes, códigos del catálogo antiguo)."""
    datos = json.loads((ruta or RAIZ / HUELLA).read_text(encoding="utf-8"))
    todos: set[str] = set()
    for hashes in datos["medidas"].values():
        todos.update(hashes)
    return int(datos["palabras_por_racha"]), todos, set(datos["medidas"])


def rachas_copiadas(descripcion: str, huella: set[str], palabras: int) -> list[str]:
    """Rachas de la descripción actual cuyo hash está en la huella."""
    return sorted(r for h, r in hashes_de_rachas(descripcion, palabras).items() if h in huella)


def main() -> int:
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args()

    trabajo = RAIZ / CATALOGO
    if not trabajo.exists():
        sys.exit(f"ERROR: no existe {trabajo}")
    palabras, huella, codigos_antiguos = cargar_huella()
    medidas = yaml.safe_load(trabajo.read_text(encoding="utf-8")).get("medidas", [])

    print("=" * 72)
    print(f"Catálogo:   {CATALOGO} ({len(medidas)} medidas)")
    print(f"Huella:     {HUELLA} ({len(codigos_antiguos)} medidas, {len(huella)} rachas)")
    print(f"Racha:      {palabras} palabras consecutivas")
    print("=" * 72)

    copiadas: list[tuple[str, list[str]]] = []
    for m in medidas:
        rachas = rachas_copiadas(m.get("descripcion", ""), huella, palabras)
        if rachas:
            copiadas.append((m["codigo"], rachas))

    nuevas = sorted({m["codigo"] for m in medidas} - codigos_antiguos)
    if nuevas:
        print(f"AVISO: {len(nuevas)} medida(s) que no estaban en el catálogo antiguo: {', '.join(nuevas)}")

    print(f"Medidas comparadas:                {len(medidas)}")
    print(f"Medidas con {palabras}+ palabras copiadas:  {len(copiadas)}")
    print("-" * 72)
    if copiadas:
        for codigo, rachas in copiadas:
            print(f"FALLO: {codigo}: {len(rachas)} racha(s) del texto original, p. ej. \"{rachas[0]}\"")
        print("RESULTADO: ROJO")
        return 1

    print("RESULTADO: VERDE")
    print("Recordatorio: esto NO verifica que las descripciones sean")
    print("normativamente exactas. Eso lo revisa una persona.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
