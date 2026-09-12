"""La justificación de exclusión de la DdA tiene que decir la verdad.

QUE DEFECTO CONGELA
    La DdA es un documento FIRMABLE: es el texto que lee el auditor para
    aceptar que una medida del Anexo II queda fuera del alcance. Hasta el
    bloque Q ese texto salía de una plantilla fija que citaba siempre el eje
    "categoría", con el dato tomado de ``ens_measures.categoria_minima`` — una
    columna denormalizada que NO es la que decide la aplicabilidad.

    Medido sobre el proyecto MEDIA del demo (13 exclusiones): 12 eran medidas
    de eje "dimensión" y la frase les atribuía un motivo de categoría falso;
    en cuatro de ellas ``categoria_minima`` coincidía con la categoría del
    sistema, de modo que el documento decía que la medida no aplica PORQUE
    aplica.

QUE COMPRUEBA
    1. Las dos funciones PARTICIONAN el Anexo II: ninguna medida queda sin
       clasificar y ninguna cae en las dos.
    2. Para toda combinación categoría × niveles, el texto emitido nombra el
       eje REAL de la medida, y nunca el otro.
    3. El texto nunca afirma que una medida no aplica por una categoría que es
       la del propio sistema.
    4. La frase del defecto no vuelve al código.
"""
from __future__ import annotations

import itertools
import re
from pathlib import Path

import pytest

from backend.app.motors.m03_dda.anexo2_rd311_2022 import (
    ANEXO_II_RD311,
    EJE_Y_DIMENSIONES,
)


def _sujeto():
    """Importa el sujeto DENTRO del test, a proposito.

    En el commit padre ``medidas_no_aplicables`` no existe: importandolo arriba,
    el fichero entero aborta en coleccion y pytest reporta un ERROR, que es mas
    facil de pasar por alto que un FAILED. Asi cada test sale en rojo con su
    motivo escrito.
    """
    from backend.app.motors.m01_categorization.aplicabilidad import (
        medidas_aplicables,
        medidas_no_aplicables,
    )
    from backend.app.motors.m03_dda.templates import (
        render_no_aplica_justification,
    )
    return medidas_aplicables, medidas_no_aplicables, render_no_aplica_justification

_NIVELES = ("BAJO", "MEDIO", "ALTO", "NO_AFECTADA")
_DIMS = ("D", "I", "C", "A", "T")
_NOMBRE_DIM = {
    "D": "disponibilidad", "I": "integridad", "C": "confidencialidad",
    "A": "autenticidad", "T": "trazabilidad",
}


def _escenarios():
    """Una muestra cruzada: 3 categorías × 12 vectores de dimensión."""
    vectores = [dict(zip(_DIMS, v)) for v in itertools.islice(
        itertools.product(_NIVELES, repeat=5), 0, None, 85,
    )]
    # Y los tres extremos, que son los que rompen: todo NO_AFECTADA, todo BAJO,
    # todo ALTO.
    vectores += [
        dict.fromkeys(_DIMS, "NO_AFECTADA"),
        dict.fromkeys(_DIMS, "BAJO"),
        dict.fromkeys(_DIMS, "ALTO"),
    ]
    for cat in ("BASICA", "MEDIA", "ALTA"):
        for niveles in vectores:
            yield cat, niveles


def test_aplicables_y_no_aplicables_particionan_el_anexo_ii():
    medidas_aplicables, medidas_no_aplicables, _ = _sujeto()
    total = set(ANEXO_II_RD311)
    assert len(total) == 73, f"el Anexo II debe traer 73 medidas, trae {len(total)}"
    escenarios = list(_escenarios())
    assert len(escenarios) >= 30, (
        f"solo {len(escenarios)} escenarios: la generación está mal y este test "
        "no está comprobando casi nada"
    )
    for cat, niveles in escenarios:
        si = medidas_aplicables(cat, niveles, exigir_alguna_afectada=False)
        no = medidas_no_aplicables(cat, niveles, exigir_alguna_afectada=False)
        assert set(si) & set(no) == set(), f"{cat}/{niveles}: solapan"
        assert set(si) | set(no) == total, f"{cat}/{niveles}: falta clasificar"


def test_el_texto_nombra_el_eje_real_de_cada_medida():
    """Si la medida se excluye por dimensión, el texto NO puede citar categoría."""
    _, medidas_no_aplicables, render_no_aplica_justification = _sujeto()
    comprobadas = 0
    for cat, niveles in _escenarios():
        no = medidas_no_aplicables(cat, niveles, exigir_alguna_afectada=False)
        for codigo, motivo in no.items():
            nombre = ANEXO_II_RD311[codigo][0]
            texto = render_no_aplica_justification(
                codigo=codigo, nombre=nombre, system_category=cat, motivo=motivo,
            )
            eje_real = EJE_Y_DIMENSIONES[codigo][0]
            assert motivo.eje == eje_real, (
                f"{codigo}: el motivo dice eje {motivo.eje} y el Anexo II dice "
                f"{eje_real}"
            )
            if eje_real == "dimension":
                assert "por la categoría del sistema" not in texto, (
                    f"{codigo} ({cat}): se excluye por dimensión y el texto "
                    f"culpa a la categoría · {texto}"
                )
                dims = EJE_Y_DIMENSIONES[codigo][1]
                for inicial in dims:
                    assert _NOMBRE_DIM[inicial] in texto, (
                        f"{codigo}: el texto no nombra la dimensión {inicial} "
                        f"que motiva la exclusión · {texto}"
                    )
            else:
                assert "por la categoría del sistema" in texto, (
                    f"{codigo} ({cat}): se excluye por categoría y el texto no "
                    f"lo dice · {texto}"
                )
            comprobadas += 1
    assert comprobadas > 500, (
        f"solo {comprobadas} justificaciones renderizadas: los escenarios no "
        "están produciendo exclusiones y este test no comprueba nada"
    )


def test_nunca_dice_que_no_aplica_por_la_categoria_que_el_sistema_tiene():
    """El caso literal del defecto: «no aplica porque aplica»."""
    _, medidas_no_aplicables, render_no_aplica_justification = _sujeto()
    for cat, niveles in _escenarios():
        no = medidas_no_aplicables(cat, niveles, exigir_alguna_afectada=False)
        for codigo, motivo in no.items():
            texto = render_no_aplica_justification(
                codigo=codigo, nombre=ANEXO_II_RD311[codigo][0],
                system_category=cat, motivo=motivo,
            )
            assert f"aplica exclusivamente a sistemas de categoría {cat}" not in texto
            # La forma general: afirmar que la exige otra categoría cuando la
            # medida ni siquiera se decide por categoría.
            if EJE_Y_DIMENSIONES[codigo][0] == "dimension":
                assert not re.search(r"categor[íi]a (BASICA|MEDIA|ALTA)[^.]*exig", texto)


def test_la_frase_del_defecto_no_vuelve_al_codigo():
    raiz = Path(__file__).resolve().parents[4]
    ficheros = list((raiz / "backend" / "app").rglob("*.py"))
    assert len(ficheros) > 500, (
        f"solo {len(ficheros)} ficheros barridos: la ruta está mal y este test "
        "no está comprobando nada"
    )
    culpables = [
        f for f in ficheros
        if "aplica exclusivamente a sistemas de categoría" in f.read_text(
            encoding="utf-8", errors="ignore")
    ]
    assert not culpables, (
        "vuelve la plantilla que atribuye toda exclusión al eje categoría: "
        f"{[str(f) for f in culpables]}"
    )


def test_render_exige_motivo_derivado_de_la_tabla():
    """Sin motivo no hay texto: es lo que permitía inventarse la causa."""
    *_, render_no_aplica_justification = _sujeto()
    with pytest.raises(TypeError):
        render_no_aplica_justification(
            codigo="op.pl.4", nombre="X", system_category="MEDIA", motivo=None,
        )
