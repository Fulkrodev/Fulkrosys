"""Guardia: el arbol de migraciones tiene UNA sola cabeza.

Por que existe. Con varias cabezas, ``alembic upgrade head`` —en singular, que
es lo que escribe todo el mundo y lo que dice la documentacion de Alembic—
falla con "Multiple head revisions are present"; solo funciona ``upgrade
heads``. Es un tropiezo garantizado para quien clone el repositorio y siga el
INSTALL, y no avisa hasta que alguien intenta migrar.

Que este test PASE hoy no lo hace inutil: el repositorio YA tuvo tres cabezas a
la vez, y por eso existe ``sub_atom_5b_magerit_child_rls_001``, cuyo
``down_revision`` es una tupla de tres. Se convergieron a mano. Esto es lo que
impide que vuelvan a abrirse sin que nadie se entere, que es como se abrieron.

No necesita base de datos: lee el arbol de ficheros de migracion.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


_BACKEND = Path(__file__).resolve().parents[1]


def _directorio_de_scripts() -> ScriptDirectory:
    cfg = Config(str(_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND / "migrations"))
    return ScriptDirectory.from_config(cfg)


def test_una_sola_cabeza():
    """Exactamente una hoja en el arbol de revisiones."""
    scripts = _directorio_de_scripts()
    cabezas = sorted(scripts.get_heads())
    assert len(cabezas) == 1, (
        f"el arbol de migraciones tiene {len(cabezas)} cabezas: {cabezas}. "
        "Con mas de una, `alembic upgrade head` falla y solo funciona "
        "`upgrade heads`, que es justo lo que nadie escribe. Converge con "
        "`alembic merge -m \"...\" " + " ".join(cabezas) + "`."
    )


def test_la_cabeza_alcanza_todas_las_revisiones():
    """Ninguna migracion queda colgando fuera de la cadena de la cabeza.

    Una sola cabeza no basta: un fichero con un ``down_revision`` que apunta a
    una revision inexistente, o una rama huerfana, dejan migraciones que
    `upgrade head` nunca aplica. Alembic las ve al recorrer el arbol.
    """
    scripts = _directorio_de_scripts()
    (cabeza,) = scripts.get_heads()
    alcanzables = {rev.revision for rev in scripts.walk_revisions("base", cabeza)}
    todas = {rev.revision for rev in scripts.walk_revisions()}
    huerfanas = sorted(todas - alcanzables)
    assert not huerfanas, (
        f"hay revisiones que `upgrade head` no aplicaria nunca: {huerfanas}"
    )


def test_el_numero_de_ficheros_de_migracion_coincide_con_el_arbol():
    """Cada .py de versions es una revision que el arbol conoce, y al reves."""
    scripts = _directorio_de_scripts()
    del_arbol = {rev.revision for rev in scripts.walk_revisions()}
    ficheros = [
        p for p in (_BACKEND / "migrations/versions").glob("*.py")
        if p.name != "__init__.py"
    ]
    assert len(ficheros) == len(del_arbol), (
        f"{len(ficheros)} ficheros en versions/ pero {len(del_arbol)} revisiones "
        "en el arbol: sobra un fichero que Alembic no ve, o falta uno que si."
    )


def test_una_cabeza_nueva_rompe_este_test(tmp_path):
    """Demuestra que la guardia detecta de verdad una segunda cabeza.

    Un test que pasa desde el primer dia no prueba nada por si solo: podria
    estar mirando donde no es. Aqui se monta una copia del arbol con una
    revision huerfana anadida y se comprueba que la deteccion salta.
    """
    import shutil

    copia = tmp_path / "migrations"
    shutil.copytree(_BACKEND / "migrations", copia)
    (copia / "versions" / "zz_cabeza_de_prueba.py").write_text(
        'revision = "zz_cabeza_de_prueba"\n'
        'down_revision = "no_afectada_cabe_001"\n'
        "branch_labels = None\ndepends_on = None\n"
        "def upgrade() -> None: ...\n"
        "def downgrade() -> None: ...\n",
        encoding="utf-8",
    )
    cfg = Config(str(_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(copia))
    cabezas = ScriptDirectory.from_config(cfg).get_heads()
    assert len(cabezas) == 2, (
        "la copia con una revision huerfana deberia tener dos cabezas; si no, "
        "este fichero no esta midiendo lo que dice medir"
    )


@pytest.mark.parametrize(
    "fichero",
    ["infra/docker/provision-entrypoint.sh", ".github/workflows/ci.yml"],
)
def test_el_aprovisionamiento_usa_head_en_singular(fichero):
    """Si alguien vuelve a `upgrade heads`, es que el arbol se abrio otra vez."""
    ruta = _BACKEND.parent / fichero
    assert ruta.is_file(), f"{fichero} no existe"
    texto = ruta.read_text(encoding="utf-8")
    assert "upgrade head" in texto
    assert "upgrade heads" not in texto, (
        f"{fichero} usa `alembic upgrade heads` (plural). Eso solo hace falta "
        "con el arbol abierto en varias cabezas, y lo que toca entonces es "
        "converger, no cambiar el comando."
    )
