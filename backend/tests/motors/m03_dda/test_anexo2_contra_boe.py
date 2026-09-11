"""Contrasta el catalogo del Anexo II contra el PDF del BOE, no contra si mismo.

POR QUE ESTE TEST Y NO EL DE AL LADO
    `test_anexo2_rd311_authoritative.py` ya "blindaba" el catalogo, pero se
    comprueba contra constantes que viven en EL MISMO modulo que valida
    (APLICA_BASICA, TOTAL_MEDIDAS...). Si alguien cambiara a la vez la tabla y
    la constante, pasaria en verde. Es un espejo, no un contraste.

    Este test compara contra `anexo2_boe_verificado.json`, extraido del PDF
    oficial del BOE por `backend/scripts/extraer_anexo2_boe.py`, que ademas
    valida el PDF antes de leerlo (que sea PDF, que tenga capa de texto y no sea
    un escaneo, paginas, y que aparezcan literalmente ANEXO II / org.1 /
    op.pl.1 / mp.s.2) y registra su sha256.

RESULTADO DEL CONTRASTE (bloque N, 2026-09-11): diferencial VACIO.
    73 de 73 codigos coinciden, 0 discrepancias de aplicabilidad por nivel.
    El catalogo estaba bien. Lo que NO tenia era el eje de dimensiones, que la
    tabla del BOE si trae y este fixture ahora conserva.
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.app.motors.m03_dda.anexo2_rd311_2022 import ANEXO_II_RD311

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/anexo2_boe_verificado.json"
SHA256_PDF_BOE = "07a74608dce3a146890f444c73ef8f2ee04f49c101114e2e2642941e53a92211"


def _boe() -> dict[str, dict]:
    datos = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {m["codigo"]: m for m in datos["medidas"]}


def test_el_fixture_viene_del_pdf_que_se_verifico():
    """Si el fixture se regenera de otro PDF, que se sepa aqui."""
    datos = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert datos["_sha256_pdf"] == SHA256_PDF_BOE
    assert "boe.es" in datos["_fuente"]
    assert datos["total_medidas"] == 73


def test_mismo_conjunto_de_codigos_que_el_boe():
    boe, cod = set(_boe()), set(ANEXO_II_RD311)
    assert cod - boe == set(), f"codigos en el catalogo que NO estan en el BOE: {sorted(cod - boe)}"
    assert boe - cod == set(), f"codigos del BOE que faltan en el catalogo: {sorted(boe - cod)}"


def test_aplicabilidad_por_nivel_identica_al_boe():
    """Convencion del punto 5.c del Anexo II: n.a. = no exigible; el resto aplica."""
    boe = _boe()
    dif = []
    for codigo, (_nombre, basica, media, alta) in sorted(ANEXO_II_RD311.items()):
        b = boe[codigo]
        esperado = (b["aplica_basica"], b["aplica_media"], b["aplica_alta"])
        if (basica, media, alta) != esperado:
            dif.append(f"{codigo}: catalogo={(basica, media, alta)} BOE={esperado} "
                       f"celdas={b['celdas_boe']}")
    assert not dif, "discrepancias contra el BOE:\n" + "\n".join(dif)


def test_el_boe_indexa_28_medidas_por_dimension_y_45_por_categoria():
    boe = _boe()
    por_dim = [c for c, m in boe.items() if m["eje"] == "dimension"]
    por_cat = [c for c, m in boe.items() if m["eje"] == "categoria"]
    assert (len(por_dim), len(por_cat)) == (28, 45)


def test_las_272_filas_de_ens_measure_dimensiones_salen_de_la_norma():
    """45 medidas por categoria x 5 dimensiones ('Todas') + 47 pares = 272.

    Cuadra con el recuento de `ens_measure_dimensiones`, lo que verifica esa
    tabla contra la norma sin necesidad de levantar la base de datos.
    """
    boe = _boe()
    por_cat = sum(1 for m in boe.values() if m["eje"] == "categoria")
    pares = sum(len(m["dimensiones"]) for m in boe.values() if m["eje"] == "dimension")
    assert por_cat * 5 + pares == 272
