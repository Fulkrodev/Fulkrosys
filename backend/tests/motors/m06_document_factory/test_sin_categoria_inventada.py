"""O1 · ningun entregable firmable declara una categoria que nadie decidio.

EL DEFECTO
    `categoria_por_regla_del_maximo` devuelve None A PROPOSITO cuando no hay
    ninguna dimension afectada: el Anexo I punto 3 dice que sin dimension
    adscrita no hay categoria que proyectar. Cuatro generadores de documentos
    convertian ese None en "BASICA":

        acta_e012_generator.py:84     nivel = _max_categoria(dimensiones) or "BASICA"
        alcance_generator.py:173      categoria = ... or _max_categoria(...) or "BASICA"
        informe_final_generator.py:209 categoria = categoria_objetivo or "BASICA"
        rectores_generator.py:94      system_category = cat[0] if cat else "BASICA"

    Son el acta de categorizacion (E-012), el documento de alcance (E-155), el
    informe final de adecuacion (E-040) y los documentos rectores. Los cuatro se
    FIRMAN. Un sistema sin categorizar salia declarado BASICA en un documento
    firmado, que es exactamente el bug de la regla del maximo saliendo por la
    puerta de los entregables.

QUE SE HACE
    Fallar. Un documento que declara una categoria tiene que tener una: si no la
    hay, lo que corresponde es negarse a generarlo y decir que falta la
    categorizacion, no rellenar el hueco con la categoria mas baja.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
M06 = RAIZ / "backend/app/motors/m06_document_factory"

# `or "BASICA"`, `else "BASICA"`, `, "BASICA")` como valor por defecto.
DEFECTO_SILENCIOSO = re.compile(
    r'(\bor\s+"BASICA"|\belse\s+"BASICA"|\.get\([^)]*,\s*"BASICA"\))'
)


def test_ningun_generador_rellena_la_categoria_con_BASICA():
    ficheros = list(M06.rglob("*.py"))
    assert len(ficheros) > 20, (
        f"solo {len(ficheros)} ficheros barridos: la ruta esta mal"
    )
    culpables = []
    for py in ficheros:
        for i, linea in enumerate(py.read_text("utf-8", errors="ignore").splitlines(), 1):
            sin_com = linea.split("#", 1)[0]
            if DEFECTO_SILENCIOSO.search(sin_com):
                culpables.append(f"{py.relative_to(RAIZ)}:{i}: {linea.strip()[:90]}")
    assert not culpables, (
        "entregables que inventan la categoria cuando no la hay:\n"
        + "\n".join(culpables)
    )


def test_existe_el_error_que_se_levanta_en_su_lugar():
    from backend.app.motors.m06_document_factory.errores import (
        CategoriaNoDeterminadaError,
    )

    assert issubclass(CategoriaNoDeterminadaError, Exception)
    # El mensaje tiene que decir QUE falta y QUE hacer, no solo que fallo.
    e = CategoriaNoDeterminadaError("E-012")
    texto = str(e)
    assert "categoriz" in texto.lower()
    assert "E-012" in texto
