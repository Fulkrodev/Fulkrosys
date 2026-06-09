"""Batch B diagnóstico previo · plantilla del cuestionario del lead (commit 1).

Verifica que la plantilla dedicada carga en el motor m16 existente, que el campo
INTERNO internal_tag solo marca la pregunta RGPD (principio "captura, no
categoriza"), que ninguna pregunta revela la categoría ENS al lead, y que el
sector sintético PRECLIENTE se EXCLUYE del catálogo admin sin romper
find_template_for de los sectores reales.
"""
from __future__ import annotations

import pytest

from backend.app.motors.m16_onboarding.catalog_loader import (
    find_template_for,
    get_template_by_id,
    reload_templates,
)
from backend.app.motors.m16_onboarding.enums import QuestionType, Role, Sector

TEMPLATE_ID = "onb-precliente-sponsor-v1"
CATALOG = "/api/v1/onboarding/catalog"


def test_precliente_template_loads_and_validates():
    reload_templates()  # revalida todos los JSON con Pydantic (incl. el nuevo)
    t = get_template_by_id(TEMPLATE_ID)
    assert t is not None, "la plantilla precliente no carga"
    assert t.sector == Sector.PRECLIENTE
    assert t.role == Role.SPONSOR
    # Las 17 preguntas enumeradas por Marcos (5 bloques).
    assert len(t.questions) == 17, f"esperaba 17 preguntas · hay {len(t.questions)}"
    # 5 bloques = 5 secciones.
    sections = list(dict.fromkeys(q.section for q in t.questions))
    assert sections == [
        "empresa", "sector_publico", "situacion_actual", "tecnologia", "cierre",
    ]


def test_precliente_template_mixes_select_and_free_text():
    t = get_template_by_id(TEMPLATE_ID)
    types = {q.type for q in t.questions}
    assert QuestionType.SINGLE_SELECT in types
    assert QuestionType.LONG_TEXT in types
    assert QuestionType.TEXT in types


def test_internal_tag_only_on_rgpd_question():
    """internal_tag es INTERNO (no se muestra al lead) · solo la pregunta de
    datos personales lo lleva, con valor contexto_rgpd (marco RGPD ≠ dimensión ENS)."""
    t = get_template_by_id(TEMPLATE_ID)
    tagged = {q.id: q.internal_tag for q in t.questions if q.internal_tag is not None}
    assert tagged == {"q-datos_personales": "contexto_rgpd"}


def test_no_question_reveals_ens_category_to_lead():
    """Principio rector: ninguna label/opción le dice al lead su categoría ENS."""
    t = get_template_by_id(TEMPLATE_ID)
    forbidden = ["categoría", "categoria", "básica", "basica", "nivel medio",
                 "nivel alto", "nivel de seguridad", "ens medio", "ens alto",
                 "ens básico", "ens basico"]
    blobs = []
    for q in t.questions:
        blobs.append(q.label.lower())
        for opt in (q.options or []):
            blobs.append(opt.label.lower())
    haystack = " || ".join(blobs)
    hits = [w for w in forbidden if w in haystack]
    assert not hits, f"copy revela categoría ENS al lead: {hits}"


def test_optional_questions_are_not_required():
    t = get_template_by_id(TEMPLATE_ID)
    by_id = {q.id: q for q in t.questions}
    assert by_id["q-algo_mas"].validation.required is False
    # proveedor de nube: opcional + skip_if cuando es 'local'.
    prov = by_id["q-proveedor_nube"]
    assert prov.validation.required is False
    assert prov.skip_if is not None
    assert prov.skip_if.question_id == "q-nube_local"


def test_find_template_for_no_regression_real_sectors():
    """El sector sintético NO contamina la resolución de sectores reales."""
    generico = find_template_for(Sector.GENERICO, Role.SPONSOR)
    assert generico is not None
    assert generico.id == "onb-generico-sponsor-v1"
    precliente = find_template_for(Sector.PRECLIENTE, Role.SPONSOR)
    assert precliente is not None
    assert precliente.id == TEMPLATE_ID


@pytest.mark.asyncio
async def test_catalog_admin_excludes_precliente(async_client):
    r = await async_client.get(CATALOG)
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(t["sector"] != "precliente" for t in body["templates"]), \
        "la plantilla precliente NO debe aparecer en el catálogo admin"
    assert "precliente" not in body["available_sectors"]
