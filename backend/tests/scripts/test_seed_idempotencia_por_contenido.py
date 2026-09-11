"""N2 · el sembrador se reconcilia por CONTENIDO, no por un contador de filas.

QUE HABIA
    `seed_all_fulkro.py` decidia si sembrar con `if existing >= 73: skip`. Un
    contador no sabe QUE hay dentro. Consecuencias reales, las dos:

      1. Una base sembrada con el catalogo viejo tiene 79 filas, seis de ellas
         con codigos que NO EXISTEN en el RD 311/2022 (mp.com.9, mp.if.9,
         mp.per.9, mp.s.8, mp.s.9, op.exp.11). 79 >= 73, asi que el sembrador
         nuevo se salta el paso y las seis se quedan ahi para siempre.
      2. El parche era una lista negra en el propio sembrador (`_NON_OFFICIAL`)
         que las filtraba al insertar. Filtrar en el consumidor lo que sobra en
         la fuente deja la fuente mintiendo: el YAML seguia declarando 79.

QUE HAY AHORA
    Las seis fuera del YAML, la lista negra fuera del sembrador, y un plan de
    reconciliacion que compara contra la fuente verificada en N0 y dice que hay
    que insertar, que actualizar y QUE BORRAR.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from backend.app.motors.m03_dda.reconciliacion import reconciliar_catalogo

RAIZ = Path(__file__).resolve().parents[3]
YAML_CATALOGO = RAIZ / "docs/catalogs/ens_measures_catalog_v1.yaml"
FIXTURE_BOE = RAIZ / "backend/tests/fixtures/anexo2_boe_verificado.json"

LAS_SEIS_INEXISTENTES = {
    "mp.com.9", "mp.if.9", "mp.per.9", "mp.s.8", "mp.s.9", "op.exp.11",
}


def _codigos_boe() -> set[str]:
    return {m["codigo"] for m in json.loads(FIXTURE_BOE.read_text("utf-8"))["medidas"]}


# ── la fuente deja de declarar lo que no existe ───────────────────────
def test_el_yaml_ya_no_trae_las_seis_inexistentes():
    data = yaml.safe_load(YAML_CATALOGO.read_text("utf-8"))
    codigos = {m["codigo"] for m in data["medidas"]}
    assert codigos & LAS_SEIS_INEXISTENTES == set(), (
        "el catalogo sigue declarando codigos que no estan en el RD 311/2022: "
        f"{sorted(codigos & LAS_SEIS_INEXISTENTES)}"
    )


def test_el_yaml_trae_exactamente_las_73_del_boe():
    data = yaml.safe_load(YAML_CATALOGO.read_text("utf-8"))
    codigos = {m["codigo"] for m in data["medidas"]}
    assert codigos == _codigos_boe()


def test_el_sembrador_ya_no_lleva_lista_negra():
    """Si la fuente esta bien, el parche que la tapaba sobra."""
    fuente = (RAIZ / "backend/scripts/seed_all_fulkro.py").read_text("utf-8")
    assert "_NON_OFFICIAL" not in fuente
    for codigo in LAS_SEIS_INEXISTENTES:
        assert codigo not in fuente, f"{codigo} sigue citado en el sembrador"


def test_el_sembrador_no_decide_por_contador():
    fuente = (RAIZ / "backend/scripts/seed_all_fulkro.py").read_text("utf-8")
    assert "existing >= 73" not in fuente, (
        "el sembrador sigue decidiendo si sembrar contando filas"
    )


# ── el plan de reconciliacion ─────────────────────────────────────────
def test_base_con_el_catalogo_viejo_borra_las_seis():
    """EL CASO QUE IMPORTA: 79 filas viejas -> las seis salen del plan de borrado."""
    en_bd = _codigos_boe() | LAS_SEIS_INEXISTENTES  # 79, como una base vieja
    plan = reconciliar_catalogo(en_bd, _codigos_boe())
    assert plan.borrar == LAS_SEIS_INEXISTENTES
    assert plan.insertar == set()
    assert plan.hay_cambios is True


def test_base_al_dia_no_toca_nada():
    plan = reconciliar_catalogo(_codigos_boe(), _codigos_boe())
    assert plan.insertar == set() and plan.borrar == set()
    assert plan.hay_cambios is False


def test_base_vacia_inserta_las_73():
    plan = reconciliar_catalogo(set(), _codigos_boe())
    assert plan.insertar == _codigos_boe()
    assert plan.borrar == set()


def test_base_incompleta_con_mas_de_73_filas_igual_se_reconcilia():
    """El contador decia 79 >= 73 y se saltaba el paso. Faltando org.1."""
    en_bd = (_codigos_boe() - {"org.1"}) | LAS_SEIS_INEXISTENTES  # 78 filas
    plan = reconciliar_catalogo(en_bd, _codigos_boe())
    assert "org.1" in plan.insertar
    assert plan.borrar == LAS_SEIS_INEXISTENTES
