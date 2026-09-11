"""N1 · una dimension no afectada no se adscribe a ningun nivel, y no arrastra medidas.

CITA LITERAL, Anexo I punto 3 del RD 311/2022:
    "Cada dimension de seguridad afectada se adscribira a uno de los siguientes
     niveles de seguridad: BAJO, MEDIO o ALTO. Si una dimension de seguridad no
     se ve afectada, no se adscribira a ningun nivel."

Lo que habia antes: `max_per_dim` arrancaba las CINCO dimensiones en "BAJO"
(m01_categorization/service.py) y `grep -i no_afectada backend/app` devolvia 0.
Una dimension que nadie valoro se convertia en BAJO en silencio, y BAJO arrastra
medidas que la norma no exige.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.motors.m01_categorization.aplicabilidad import medidas_aplicables
from backend.app.motors.m01_categorization.service import ImpactLevel

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/anexo2_boe_verificado.json"

TODAS_BAJO = {"D": "BAJO", "I": "BAJO", "C": "BAJO", "A": "BAJO", "T": "BAJO"}


# ── el enumerado ──────────────────────────────────────────────────────
def test_existe_el_estado_no_afectada():
    assert ImpactLevel.NO_AFECTADA.value == "NO_AFECTADA"


def test_no_afectada_ordena_por_debajo_de_bajo():
    assert ImpactLevel.NO_AFECTADA.numeric < ImpactLevel.BAJO.numeric


# ── la funcion pura ───────────────────────────────────────────────────
def test_la_funcion_es_pura_y_no_pide_base_de_datos():
    r = medidas_aplicables("BASICA", TODAS_BAJO)
    assert isinstance(r, dict) and r


def test_cada_medida_aplicable_trae_su_motivo():
    for codigo, motivo in medidas_aplicables("MEDIA", TODAS_BAJO).items():
        assert motivo.eje in ("categoria", "dimension"), codigo
        if motivo.eje == "dimension":
            assert motivo.dimension in {"D", "I", "C", "A", "T"}
            assert motivo.nivel in ("BAJO", "MEDIO", "ALTO")
        else:
            assert motivo.categoria in ("BASICA", "MEDIA", "ALTA")


def test_categoria_basica_con_todo_bajo_da_las_52_del_boe():
    """Las 52 de BASICA son las de eje categoria + las de dimension que aplican en BAJO."""
    boe = {m["codigo"]: m for m in json.loads(FIXTURE.read_text("utf-8"))["medidas"]}
    esperadas = {c for c, m in boe.items() if m["aplica_basica"]}
    assert set(medidas_aplicables("BASICA", TODAS_BAJO)) == esperadas


# ── el corazon de N1 ──────────────────────────────────────────────────
def test_trazabilidad_no_afectada_produce_MENOS_medidas_que_trazabilidad_bajo():
    con_bajo = medidas_aplicables("BASICA", TODAS_BAJO)
    sin_t = medidas_aplicables("BASICA", {**TODAS_BAJO, "T": "NO_AFECTADA"})
    assert set(sin_t) < set(con_bajo), (
        "una dimension NO AFECTADA no puede producir el mismo conjunto que una "
        "dimension en BAJO: el Anexo I dice que no se adscribe a ningun nivel"
    )
    # op.exp.8 "Registro de la actividad" se exige por T y aplica ya en BAJO.
    diferencia = set(con_bajo) - set(sin_t)
    assert "op.exp.8" in diferencia


def test_una_dimension_no_afectada_nunca_aparece_como_motivo():
    r = medidas_aplicables("ALTA", {**TODAS_BAJO, "C": "NO_AFECTADA"})
    for codigo, motivo in r.items():
        if motivo.eje == "dimension":
            assert motivo.dimension != "C", (
                f"{codigo} se justifica por confidencialidad, que no esta afectada"
            )


def test_todas_no_afectadas_no_es_categorizable():
    with pytest.raises(ValueError):
        medidas_aplicables("BASICA", dict.fromkeys("DICAT", "NO_AFECTADA"))


def test_la_categorizacion_obliga_a_decidir_las_cinco():
    with pytest.raises(ValueError):
        medidas_aplicables("BASICA", {"D": "BAJO", "I": "BAJO"})


# ── contraste contra la fuente verificada en N0 ───────────────────────
def test_el_catalogo_lleva_el_eje_y_coincide_con_el_boe():
    from backend.app.motors.m03_dda.anexo2_rd311_2022 import EJE_Y_DIMENSIONES

    boe = {m["codigo"]: m for m in json.loads(FIXTURE.read_text("utf-8"))["medidas"]}
    assert set(EJE_Y_DIMENSIONES) == set(boe)
    dif = []
    for c, (eje, dims) in sorted(EJE_Y_DIMENSIONES.items()):
        # Las iniciales son un CONJUNTO ("CITA" y "ATIC" dicen lo mismo); se
        # guardan en el orden del BOE por fidelidad, se comparan como conjunto.
        esperado = (boe[c]["eje"], set(boe[c].get("dimensiones_iniciales", "")))
        if (eje, set(dims)) != esperado:
            dif.append(f"{c}: catalogo={(eje, set(dims))} BOE={esperado}")
    assert not dif, "el eje del catalogo no cuadra con el BOE:\n" + "\n".join(dif)


# ── test dorado congelado ─────────────────────────────────────────────
ORO = Path(__file__).resolve().parents[2] / "fixtures/aplicabilidad_oro.json"


def test_dorado_congelado():
    """Seis categorizaciones con su lista esperada, derivada de la fuente de N0.

    Si esto cambia, o cambio el RD 311/2022 o se rompio la funcion. No se
    regenera el fixture para que pase: se mira cual de las dos es.
    """
    oro = json.loads(ORO.read_text("utf-8"))
    fallos = []
    for caso in oro["casos"]:
        obtenido = medidas_aplicables(caso["categoria"], caso["niveles"])
        if sorted(obtenido) != caso["medidas"]:
            faltan = set(caso["medidas"]) - set(obtenido)
            sobran = set(obtenido) - set(caso["medidas"])
            fallos.append(f"{caso['nombre']}: faltan={sorted(faltan)} sobran={sorted(sobran)}")
        for codigo, (eje, dim, nivel, cat) in caso["motivos"].items():
            m = obtenido.get(codigo)
            if m is None:
                continue
            if (m.eje, m.dimension, m.nivel, m.categoria) != (eje, dim, nivel, cat):
                fallos.append(f"{caso['nombre']}/{codigo}: motivo cambio")
    assert not fallos, "\n".join(fallos)


def test_dorado_cubre_el_caso_de_dimension_no_afectada():
    oro = json.loads(ORO.read_text("utf-8"))
    con_no_afectada = [c for c in oro["casos"]
                       if "NO_AFECTADA" in c["niveles"].values()]
    assert len(con_no_afectada) >= 3


def test_alta_sin_disponibilidad_pierde_las_10_medidas_de_D():
    """Comprobacion independiente del dorado: las D-indexadas son 10."""
    from backend.app.motors.m03_dda.anexo2_rd311_2022 import EJE_Y_DIMENSIONES

    solo_d = {c for c, (eje, ini) in EJE_Y_DIMENSIONES.items()
              if eje == "dimension" and set(ini) == {"D"}}
    assert len(solo_d) == 10
    todo = medidas_aplicables("ALTA", dict.fromkeys("DICAT", "ALTO"))
    sin_d = medidas_aplicables("ALTA", {**dict.fromkeys("DICAT", "ALTO"),
                                        "D": "NO_AFECTADA"})
    assert set(todo) - set(sin_d) == solo_d


# ── la columna vieja se queda sin lectores ────────────────────────────
def test_ningun_lector_del_atributo_orm_dimensiones_aplicables():
    """N1 · `ens_measures.dimensiones_aplicables` estaba mal en 4 de 12 medidas.

    Se le quitan los lectores. Este test congela el cero: si alguien vuelve a
    leer `<algo>.dimensiones_aplicables` fuera del modelo, falla aqui.
    """
    import re

    raiz = Path(__file__).resolve().parents[3]
    patron = re.compile(r"\b\w+\.dimensiones_aplicables\b")
    culpables = []
    for carpeta in ("app", "scripts"):
        for py in (raiz / carpeta).rglob("*.py"):
            if py.name == "ens.py" and py.parent.name == "models":
                continue  # el modelo puede declararla
            for n, linea in enumerate(py.read_text("utf-8").splitlines(), 1):
                sin_comentario = linea.split("#", 1)[0]
                if patron.search(sin_comentario):
                    culpables.append(f"{py.relative_to(raiz)}:{n}: {linea.strip()}")
    assert not culpables, "lectores del atributo ORM:\n" + "\n".join(culpables)
