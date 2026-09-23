"""Guardia: sin postgres, los `requires_db` se SALTAN; no revientan.

La marca ``requires_db`` se deriva correctamente y ``-m "not requires_db"``
funciona, pero una marca es una etiqueta: no salta nada por si sola. Quien
clonara el repositorio y ejecutara un fichero marcado sin postgres levantado
se comia esto:

    $ pytest backend/tests/audit_fixes/test_el_simulacro_se_guarda_de_verdad.py
    ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5433)
    1 failed

Una traza de conexion dice "algo esta roto"; un SKIPPED con el motivo dice
"falta una dependencia y asi se levanta". La diferencia la nota justo la
persona que menos contexto tiene: la que acaba de clonar.

Se ejecuta en un SUBPROCESO a proposito. La sonda de ``conftest.py`` se cachea
una vez por sesion, asi que dentro de esta misma ejecucion ya esta resuelta;
para comprobar el comportamiento sin base de datos hay que arrancar pytest de
nuevo con ``DATABASE_URL`` apuntando a un puerto muerto.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


_RAIZ = Path(__file__).resolve().parents[2]

# Un puerto que nadie escucha. 1 esta reservado y no es asignable.
_PUERTO_MUERTO = "postgresql+asyncpg://fulkro:fulkro@127.0.0.1:1/fulkro"


def _pytest_en_subproceso(objetivo: str, *extra: str) -> subprocess.CompletedProcess:
    entorno = dict(os.environ)
    for clave in ("DATABASE_URL", "DATABASE_URL_SYNC", "DATABASE_MIGRATE_URL"):
        entorno[clave] = _PUERTO_MUERTO
    # sin la reescritura a fulkro_test, para que la URL sea exactamente esa
    entorno["FULKRO_USE_LIVE_DB"] = "1"
    return subprocess.run(
        [
            sys.executable, "-m", "pytest", objetivo, "-q", "--no-header",
            "-p", "no:cacheprovider", *extra,
        ],
        cwd=_RAIZ, env=entorno, capture_output=True, text=True, timeout=600,
    )


def test_sin_base_de_datos_los_requires_db_se_saltan():
    r = _pytest_en_subproceso(
        "backend/tests/audit_fixes/test_el_simulacro_se_guarda_de_verdad.py"
    )
    salida = r.stdout + r.stderr
    assert r.returncode == 0, (
        "pytest deberia terminar en 0 saltando, no fallando. Salida:\n" + salida
    )
    assert "skipped" in salida, salida
    assert " error" not in salida.lower().replace("errors=0", ""), salida
    assert "ConnectionRefusedError" not in salida, (
        "la traza de conexion es exactamente lo que este arreglo elimina:\n" + salida
    )


def test_el_motivo_del_salto_dice_que_falta_y_como_arreglarlo():
    """Un skip sin motivo accionable es casi tan malo como la traza."""
    r = _pytest_en_subproceso(
        "backend/tests/audit_fixes/test_el_simulacro_se_guarda_de_verdad.py", "-rs",
    )
    salida = r.stdout + r.stderr
    assert "PostgreSQL no alcanzable" in salida, salida
    assert "127.0.0.1:1" in salida, "tiene que decir QUE destino intento:\n" + salida
    assert "make demo" in salida, "y como levantarlo:\n" + salida


def test_la_bateria_sin_base_de_datos_no_deja_ni_un_error_de_coleccion():
    """Los `requires_db` de un directorio entero se saltan, no revientan."""
    r = _pytest_en_subproceso("backend/tests/audit_fixes")
    salida = r.stdout + r.stderr
    assert r.returncode == 0, salida
    assert "ConnectionRefusedError" not in salida, salida
