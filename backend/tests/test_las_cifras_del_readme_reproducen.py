"""Guardia: cada cifra del README que lleva su comando REPRODUCE ese comando.

El README presume, con razon, de que cada cifra lleva el comando que la
produce. Eso solo vale si alguien vuelve a ejecutarlo: cuatro de ellas habian
derivado en silencio —271 migraciones cuando ya habia 273, 616 ficheros de
test cuando ya habia 627, y las lineas de Python por partida doble— y nada lo
detectaba. Una cifra con su comando al lado que ya no reproduce es peor que no
tener cifra: invita a comprobarla y falla la comprobacion.

Aqui se ejecuta el comando de verdad y se compara con lo escrito.

Lo que este fichero NO cubre, a proposito: el resultado de la suite completa
(``44 failed, 6510 passed ...``). Eso no es un comando de segundos, es una
ejecucion de catorce minutos contra una base sembrada, y su cifra es el
resultado fechado de una ejecucion concreta, no algo reproducible al vuelo.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


_RAIZ = Path(__file__).resolve().parents[2]
_README = _RAIZ / "README.md"


def _numero_del_readme(patron: str) -> int:
    """Extrae la cifra escrita en el README, con o sin separador de millares."""
    texto = _README.read_text(encoding="utf-8")
    m = re.search(patron, texto)
    assert m, f"no se encontro en el README el patron {patron!r}"
    return int(m.group(1).replace(".", ""))


def _contar(comando: str) -> int:
    r = subprocess.run(
        ["bash", "-c", comando], cwd=_RAIZ, capture_output=True, text=True,
    )
    assert r.returncode == 0, f"{comando!r} fallo: {r.stderr.strip()}"
    return int(r.stdout.strip().split()[0])


# (que es, patron en el README, comando que lo mide)
_CIFRAS = [
    (
        "motores de dominio",
        r"\| Motores de dominio \| \*\*([\d.]+)\*\*",
        "ls -d backend/app/motors/m*/ | wc -l",
    ),
    (
        "migraciones alembic",
        r"\| Migraciones Alembic \| \*\*([\d.]+)\*\*",
        "ls backend/migrations/versions/*.py | wc -l",
    ),
    (
        "paginas del frontend",
        r"\| Páginas del frontend \| \*\*([\d.]+)\*\*",
        "find frontend/app -name page.tsx | wc -l",
    ),
    (
        "componentes react",
        r"\| Componentes React \| \*\*([\d.]+)\*\*",
        "find frontend/components -name '*.tsx' | wc -l",
    ),
    (
        "lineas de python",
        r"\| Líneas de Python \| \*\*([\d.]+)\*\*",
        "find backend/app -name '*.py' | xargs wc -l | tail -1",
    ),
    (
        "ficheros de test",
        r"\| Ficheros de test \| \*\*([\d.]+)\*\*",
        "find backend/tests -name 'test_*.py' | wc -l",
    ),
    (
        "specs de playwright",
        r"\| Specs de Playwright \| \*\*([\d.]+)\*\*",
        "find frontend/tests -name '*.spec.ts' | wc -l",
    ),
    # Las mismas cifras repetidas en otras secciones: la tabla se actualizo y
    # estas no (268 y 269 migraciones, 46 motores cuando ya eran 273 y 44).
    (
        "migraciones alembic (bloque de cifras)",
        r"ls backend/migrations/versions/\*\.py \| wc -l\n(\d+)",
        "ls backend/migrations/versions/*.py | wc -l",
    ),
    (
        "motores de dominio (bloque de cifras)",
        r"ls -d backend/app/motors/m\*/ \| wc -l\n(\d+)",
        "ls -d backend/app/motors/m*/ | wc -l",
    ),
    (
        "motores de dominio (estructura)",
        r"· (\d+) directorios de motor",
        "ls -d backend/app/motors/m*/ | wc -l",
    ),
    (
        "migraciones alembic (estructura)",
        r"directorios de motor en app/motors/ · (\d+) migraciones",
        "ls backend/migrations/versions/*.py | wc -l",
    ),
    (
        "servicios de docker compose",
        r"`docker-compose.yml` declara (\d+) servicios",
        "python3 -c \"import yaml; "
        "print(len(yaml.safe_load(open('docker-compose.yml'))['services']))\"",
    ),
]


@pytest.mark.parametrize(
    "que,patron,comando", _CIFRAS, ids=[c[0] for c in _CIFRAS],
)
def test_la_cifra_del_readme_reproduce(que, patron, comando):
    escrita = _numero_del_readme(patron)
    medida = _contar(comando)
    assert escrita == medida, (
        f"el README dice {escrita} {que} y el comando que trae al lado devuelve "
        f"{medida}.\n  $ {comando}\nActualiza la cifra, no el comando."
    )


def test_el_bloque_de_las_cifras_coincide_con_la_tabla():
    """El README trae las lineas de Python DOS veces, con dos comandos distintos.

    La tabla usa ``find``; el bloque "Las cifras, cada una con su comando" usa
    ``git ls-files``. Cuentan lo mismo salvo ficheros sin versionar, asi que si
    se separan es que uno de los dos se quedo sin actualizar — que es
    exactamente lo que habia pasado (242.267 y 237.617).
    """
    del_bloque = _numero_del_readme(r"\n\s*(\d+) total")
    de_la_tabla = _numero_del_readme(r"\| Líneas de Python \| \*\*([\d.]+)\*\*")
    medida_git = _contar(
        "git ls-files backend/app | grep '\\.py$' | xargs wc -l | tail -1"
    )
    assert del_bloque == medida_git, (
        f"el bloque dice {del_bloque} lineas y `git ls-files` devuelve {medida_git}"
    )
    assert abs(del_bloque - de_la_tabla) < 2000, (
        f"la tabla dice {de_la_tabla} y el bloque {del_bloque}: uno de los dos "
        "se quedo atras"
    )
