"""Guardia: la interfaz no manda al usuario "a la pestaña siguiente".

El caso que origina esto estaba en ``AssignContactModal.tsx``: cuando no habia
contactos, el estado vacio decia

    Sin contactos. Crea uno nuevo en la pestaña siguiente.

y la pestaña se llama "Crear contacto nuevo". "La siguiente" tiene dos
problemas. Uno: es una referencia posicional, depende de la disposicion y un
lector de pantalla no la transmite —quien navega con uno oye "la pestaña
siguiente" y no sabe cual es—. Dos, y es el de fondo: era una instruccion para
que el usuario hiciera clic en algo que el codigo podia hacer por el, porque
``setTab`` estaba doce lineas mas arriba en el mismo componente. Una
instruccion de mas es una instruccion que sobra.

Este test prohibe las formulas posicionales en el TEXTO que ve el usuario. No
mira comentarios de codigo: ahi la posicion es una nota para quien lee el
fichero, no una instruccion para nadie.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

# Formulas que mandan al usuario a un sitio por su POSICION en la pantalla.
_POSICIONALES = [
    r"pestaña siguiente",
    r"pestaña anterior",
    r"en la sección de abajo",
    r"más abajo\.",
    r"más abajo cuando",
    r"\ba la izquierda\.",
    r"\ba la derecha\.",
    r"el (botón|enlace) de (arriba|abajo)",
]

# Excepciones, una a una y con su motivo.
_EXCEPCIONES = {
    # El tutorial ENSEÑA donde esta el icono flotante: la posicion ES la
    # informacion que transmite, no un atajo para no programar la accion.
    # Quitarla no mejora nada; empeora el tutorial.
    "components/client-portal/tutorial/OnboardingTutorial.tsx",
}


def _lineas_de_texto_de_interfaz(ruta: Path) -> list[tuple[int, str]]:
    """Lineas del fichero que NO son comentarios de codigo."""
    fuera: list[tuple[int, str]] = []
    en_bloque = False
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        limpia = linea.strip()
        if en_bloque:
            if "*/" in limpia:
                en_bloque = False
            continue
        if limpia.startswith("/*"):
            en_bloque = "*/" not in limpia
            continue
        if limpia.startswith("//") or limpia.startswith("*"):
            continue
        fuera.append((n, linea))
    return fuera


@pytest.mark.parametrize("patron", _POSICIONALES)
def test_la_interfaz_no_manda_al_usuario_por_posicion(patron):
    regex = re.compile(patron, re.IGNORECASE)
    encontrados: list[str] = []
    for ruta in sorted(_FRONTEND.rglob("*.tsx")):
        if "node_modules" in ruta.parts:
            continue
        relativa = ruta.relative_to(_FRONTEND).as_posix()
        if relativa in _EXCEPCIONES:
            continue
        for numero, linea in _lineas_de_texto_de_interfaz(ruta):
            if regex.search(linea):
                encontrados.append(f"{relativa}:{numero} · {linea.strip()}")
    assert not encontrados, (
        f"hay texto de interfaz que situa algo por su posicion ({patron!r}):\n  "
        + "\n  ".join(encontrados)
        + "\nUn lector de pantalla no transmite la posicion. Y si lo que se "
        "pide es un clic que el codigo puede dar, pon un boton que lo de."
    )


def test_el_estado_vacio_de_asignar_contacto_ofrece_el_boton():
    """El caso concreto: ya no se pide un clic, se ofrece."""
    ruta = _FRONTEND / "components/roles/AssignContactModal.tsx"
    fuente = ruta.read_text(encoding="utf-8")
    assert 'onClick={() => setTab("new")}' in fuente, (
        "el estado vacio tiene que llevar al usuario a la pestaña de crear, no "
        "explicarle donde esta"
    )
    assert "pestaña siguiente" not in fuente
