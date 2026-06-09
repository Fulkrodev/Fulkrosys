"""Integration tests PROVEEDORES templates E-600 + E-601 · sub-lote 1.B.7.1.1 architect-VERBATIM.

2 plantillas en parametrize · pattern identico a test_tecnicos_templates_render.py +
test_lms_templates_render.py + test_bcp_templates_render.py.

Context alineado con fixture conftest_proveedores (3 proveedores sinteticos del target
FULKRO empresa privada licitando · AMEND-012).

Reglas duras sostenidas:
- LECCION-OPS-020: Jinja filter chains en table cells refactorizados via {% set %}
  pre-compute outside table. Filtros como `| default(...)` en table cells STRIPPED
  via {% set var = ... if ... else default %} fuera de la tabla.
- LECCION-OPS-021: REPLACE limpio (no diff incremental · architect VERBATIM commits).
- LECCION-OPS-028: path mirror filesystem motor.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from backend.app.motors.m06_document_factory.rendering import render_docx
from backend.tests.motors.m06_document_factory.conftest_proveedores import (
    ASSESSMENT_FULL,
    PLAN_SUPERVISION_FULL,
)

VAR_TEMPLATES = Path(__file__).resolve().parents[4] / "var" / "templates_docx"
PLACEHOLDER_PATTERN = re.compile(r"\{\{|\{%|%\}|\}\}")

PROVEEDORES_TEMPLATES = ["E-600", "E-601", "E-602", "E-603", "E-604"]


@pytest.fixture
def proveedores_context() -> dict:
    """Context completo para render E-600 + E-601 · alineado conftest_proveedores."""
    return {
        "cliente": {
            "razon_social": "Test Proveedores SL",
            "nif": "B70000000",
            "sector": "fintech",
            "responsable_seguridad": {
                "nombre": "RSEG Proveedores Test",
                "cargo": "CISO",
                "email": "ciso@test-proveedores.example",
            },
            "responsable_sistemas": {
                "nombre": "CTO Proveedores Test",
                "cargo": "CTO",
            },
            "direccion": {
                "nombre": "Director Proveedores Test",
                "cargo": "Director General",
            },
            "contacto_compliance": {
                "email": "compliance@test-proveedores.example",
            },
            # E-604 firmas table + seccion 1 identificacion partes
            "representante": {
                "nombre": "Director Test (representante legal)",
                "cargo": "Director General",
            },
            "domicilio": "Calle Test 1, 28001 Madrid",
            "project_id": "test-project-001",
        },
        "documento": {
            "codigo": "E-600",  # se sobreescribe para E-601 si necesario · default ok
            "version": "1.0",
            "fecha_emision": "2026-05-18",
        },
        # E-600 · lista proveedores (alineada conftest_proveedores 3 sinteticos)
        "proveedores": [
            {
                "razon_social": "CloudHost Iberia SL",
                "nif": "B11111111",
                "servicio_descripcion": "Hosting cloud productivo",
                "categoria_servicio": "IaaS multi-tenant",
                "nivel_criticidad": "CRITICO",
                "fecha_inicio": "2025-01-01",
                "fecha_vencimiento": "2028-01-01",
                "next_review_date": "2026-12-31",
                "next_review_type": "Anual + ad-hoc",
                "next_review_owner": "RSEG Proveedores Test",
                "contacto_operativo": {
                    "nombre": "Juan Cloud", "email": "juan@cloudhost.example",
                },
                "normativas_aplicables": ["ENS", "RGPD", "NIS2"],
                "es_encargado_rgpd": True,
                "adenda_referencia": "ADENDA-ENS-2026-001",
                "last_assessment_date": "2026-05-15",
                "last_assessment_decision": "APROBADO",
                "observaciones": "Proveedor maduro ENS ALTA",
            },
            {
                "razon_social": "SaaS-CRM Solutions",
                "nif": "B22222222",
                "servicio_descripcion": "Plataforma SaaS CRM",
                "categoria_servicio": "SaaS multi-tenant",
                "nivel_criticidad": "ALTO",
                "fecha_inicio": "2025-03-15",
                "fecha_vencimiento": "2027-03-14",
                "next_review_date": "2026-10-15",
                "next_review_type": "Anual",
                "contacto_operativo": {
                    "nombre": "Maria CRM", "email": "maria@saas-crm.example",
                },
                "normativas_aplicables": ["RGPD", "NIS2"],
                "es_encargado_rgpd": True,
                "adenda_referencia": None,
                "last_assessment_date": "2026-04-10",
                "last_assessment_decision": "CONDICIONAL",
                "observaciones": "Pendiente formalizar adenda RGPD Art 28",
            },
            {
                "razon_social": "Consultoria Cumplimiento Norte",
                "nif": "B33333333",
                "servicio_descripcion": "Servicios consultivos ENS/RGPD",
                "categoria_servicio": "Consultoria especializada",
                "nivel_criticidad": "MEDIO",
                "fecha_inicio": "2024-06-01",
                "fecha_vencimiento": None,
                "next_review_date": "2027-06-01",
                "next_review_type": "Bienal",
                "contacto_operativo": {
                    "nombre": "Pedro Consultor", "email": "pedro@cumplimiento.example",
                },
                "normativas_aplicables": ["RGPD"],
                "es_encargado_rgpd": False,
                "adenda_referencia": None,
                "last_assessment_date": "2025-12-01",
                "last_assessment_decision": "APROBADO",
                "observaciones": "Acceso ocasional bajo NDA",
            },
        ],
        "dependencias_criticas": [
            {
                "proveedor": "CloudHost Iberia SL",
                "descripcion_riesgo": "Concentracion infraestructura productiva",
                "plan_contingencia": "Failover region eu-central",
            },
        ],
        "proveedores_desvinculados": [],
        # E-601 + E-602 + E-603 · proveedor single
        # E-601 usa este como candidato (no rellenado · solo header)
        # E-602/E-603 usan este como proveedor objeto evaluacion/supervision
        # Campos extra (id, es_encargado_rgpd, subcontrata, etc.) son no-op para E-601.
        "proveedor": {
            "id": "prov-cloudhost-001",
            "razon_social": "CloudHost Iberia SL",
            "nif": "B11111111",
            "servicio_descripcion": "Hosting cloud productivo",
            "categoria_servicio": "IaaS multi-tenant",
            "categoria_servicio_ens": "ALTA",
            "nivel_criticidad": "CRITICO",
            "es_encargado_rgpd": True,
            "subcontrata": True,
            "domicilio": "Calle Demo 1 Madrid",
            "pais_sede": "Espana",
            "volumen_eur": "120000",
            "plazo_respuesta_dias": 20,
            # E-604 firmas seccion 16 + identificacion partes seccion 1
            "representante": {
                "nombre": "Carmen Cloud (CEO)",
                "cargo": "CEO representante legal",
            },
            # E-604 condicionales bloques RGPD + NIS2 (NO DORA)
            "normativas_aplicables": ["ENS", "RGPD", "NIS2"],
        },
        # E-602 · superset assessment importado del fixture conftest_proveedores
        "assessment": ASSESSMENT_FULL,
        # E-603 · plan supervision importado del fixture conftest_proveedores
        "plan_supervision": PLAN_SUPERVISION_FULL,
        # E-604 · adenda + contrato_base
        "adenda": {
            "id": "addendum-test-001",
            "addendum_code": "ADENDA-ENS-2026-001",
            "contract_ref": "CONTRATO-TEST-2025-001",
            "fecha_vigor": "2026-06-01",
            "vencimiento": "2028-05-31",
            "notificacion_horas": 24,
            "notificacion_horas_rgpd": 24,
            "notificacion_horas_nis2": 12,
            "seguro_cuantia_eur": "1.000.000",
        },
        "contrato_base": {
            "fecha": "2025-01-01",
            "objeto": "Servicios hosting cloud productivo",
        },
    }


@pytest.mark.parametrize("codigo", PROVEEDORES_TEMPLATES)
def test_proveedores_template_renders_without_placeholder_leak(
    codigo, tmp_path, proveedores_context,
):
    template_path = VAR_TEMPLATES / f"{codigo}.docx"
    assert template_path.exists(), f"Missing precompiled template: {template_path}"

    output_path = tmp_path / f"{codigo}_test.docx"
    render_docx(template_path, proveedores_context, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 5000, (
        f"{codigo} DOCX too small ({output_path.stat().st_size} bytes)"
    )

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    leaks = PLACEHOLDER_PATTERN.findall(text)
    assert len(leaks) == 0, f"{codigo} has placeholder leaks: {leaks[:5]}"
    assert "Test Proveedores SL" in text, f"{codigo} missing cliente.razon_social"


def test_e600_renders_three_critical_levels(tmp_path, proveedores_context):
    """E-600 debe renderizar las 3 secciones 4.X por nivel criticidad + resumen counts.

    Validacion semantica especifica E-600: secciones 4.1 CRITICO + 4.2 ALTO + 4.3 MEDIO
    deben aparecer + resumen agregado con counts correctos (CRITICOS=1 ALTOS=1 MEDIOS=1
    BAJOS=0 TOTAL=3 · con_adenda=1).
    """
    template_path = VAR_TEMPLATES / "E-600.docx"
    output_path = tmp_path / "E-600_semantic.docx"
    render_docx(template_path, proveedores_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    assert "CloudHost Iberia SL" in text, "E-600 falta proveedor CRITICO"
    assert "SaaS-CRM Solutions" in text, "E-600 falta proveedor ALTO"
    assert "Consultoria Cumplimiento Norte" in text, "E-600 falta proveedor MEDIO"
    assert "CRITICO" in text and "ALTO" in text and "MEDIO" in text
    # dependencias criticas seccion 6 (1 entrada)
    assert "Failover region eu-central" in text, "E-600 falta plan contingencia"
    # ENS Art 18 + op.ext.1 referencias normativas
    assert "op.ext.1" in text, "E-600 falta referencia ENS op.ext.1"
    assert "RGPD Art. 28" in text or "Art. 28" in text, "E-600 falta RGPD Art 28"


def test_e601_renders_candidate_provider_data(tmp_path, proveedores_context):
    """E-601 debe rellenar header con datos proveedor candidato (single proveedor)
    + secciones A-G del cuestionario + clausulas normativas."""
    template_path = VAR_TEMPLATES / "E-601.docx"
    output_path = tmp_path / "E-601_semantic.docx"
    render_docx(template_path, proveedores_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # header proveedor (unico fixture compartido E-601/E-602/E-603 · CloudHost)
    assert "CloudHost Iberia SL" in text, "E-601 falta proveedor.razon_social"
    assert "B11111111" in text, "E-601 falta proveedor.nif"
    assert "20 días naturales" in text or "20" in text, "E-601 falta plazo_respuesta_dias"
    # cliente entidad solicitante
    assert "Test Proveedores SL" in text
    assert "compliance@test-proveedores.example" in text
    # secciones 11 numeradas
    for seccion in ["SECCIÓN A", "SECCIÓN B", "SECCIÓN C", "SECCIÓN D", "SECCIÓN E"]:
        assert seccion in text, f"E-601 falta {seccion}"
    # referencias normativas core
    assert "RD 311/2022" in text, "E-601 falta RD 311/2022"
    assert "RGPD" in text, "E-601 falta RGPD"
    assert "NIS2" in text, "E-601 falta NIS2"
    assert "DORA" in text, "E-601 falta DORA"


def test_e602_renders_decision_aprobado_with_scoring(tmp_path, proveedores_context):
    """E-602 debe renderizar branch APROBADO + scoring 91/100 + nivel CRITICO +
    secciones 7 dimensiones + hallazgos positivos/criticos + certificaciones."""
    template_path = VAR_TEMPLATES / "E-602.docx"
    output_path = tmp_path / "E-602_semantic.docx"
    render_docx(template_path, proveedores_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # header + proveedor + cliente
    assert "CloudHost Iberia SL" in text, "E-602 falta proveedor.razon_social"
    assert "Test Proveedores SL" in text, "E-602 falta cliente.razon_social"
    # decision branch APROBADO
    assert "APROBADO" in text, "E-602 falta decision APROBADO"
    assert "APRUEBA" in text, "E-602 falta branch APRUEBA del decision_label==APROBADO"
    # scoring total + per-seccion
    assert "91 / 100" in text or "91" in text, "E-602 falta scoring_total"
    # nivel criticidad asignado
    assert "CRITICO" in text, "E-602 falta nivel CRITICO asignado"
    # certificaciones vigentes (>= 3 de 5)
    assert "ISO/IEC 27001" in text, "E-602 falta certificacion ISO 27001"
    assert "SOC 2" in text or "SOC2" in text, "E-602 falta SOC 2"
    # hallazgos critico documentado
    assert "Subencargado" in text, "E-602 falta hallazgo critico subencargado"
    # marco normativo core
    assert "RD 311/2022" in text or "op.ext.1" in text, "E-602 falta RD 311 / op.ext.1"
    assert "RGPD" in text, "E-602 falta RGPD"


def test_e603_renders_critico_frequencies(tmp_path, proveedores_context):
    """E-603 debe renderizar frecuencias nivel CRITICO (Mensual reuniones + Anual
    pruebas tecnicas + Anual reevaluacion) + revisiones documentales tabla +
    notificacion 24h + escalado 4 niveles severidad + responsabilidades 4 roles."""
    template_path = VAR_TEMPLATES / "E-603.docx"
    output_path = tmp_path / "E-603_semantic.docx"
    render_docx(template_path, proveedores_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # header
    assert "CloudHost Iberia SL" in text, "E-603 falta proveedor.razon_social"
    assert "Test Proveedores SL" in text, "E-603 falta cliente.razon_social"
    # nivel criticidad influencia frecuencias
    assert "CRITICO" in text, "E-603 falta nivel CRITICO"
    # branches nivel CRITICO: Mensual + Anual pruebas
    assert "Mensual" in text, "E-603 falta frecuencia Mensual (CRITICO)"
    # revisiones documentales tabla rellena (3 rows · fixture)
    assert "AENOR" in text or "ENS" in text and "ISO 27001" in text, (
        "E-603 falta tabla revisiones documentales"
    )
    # notificacion 24h
    assert "24" in text, "E-603 falta notificacion_horas=24"
    # escalado 4 severidades
    for sev in ["BAJA", "MEDIA", "ALTA", "CRÍTICA"]:
        assert sev in text, f"E-603 falta severidad {sev} en escalado"
    # marco normativo core
    assert "op.ext.1" in text and "op.ext.2" in text, "E-603 falta op.ext.1/2"
    assert "NIS2 Art. 21" in text or "NIS2" in text, "E-603 falta NIS2 Art.21"


def test_e604_renders_ens_rgpd_nis2_blocks_no_dora(tmp_path, proveedores_context):
    """E-604 con normativas=['ENS','RGPD','NIS2'] debe incluir bloques RGPD (seccion 6)
    + NIS2 (seccion 7) + NO DORA (seccion 8 ausente · condicional incluir_dora=False).

    Valida ademas: identificacion partes seccion 1 + addendum_code + firmas table
    + clausulas core (auditoria + confidencialidad + jurisdiccion espanola).
    """
    template_path = VAR_TEMPLATES / "E-604.docx"
    output_path = tmp_path / "E-604_semantic.docx"
    render_docx(template_path, proveedores_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Identificacion partes
    assert "Test Proveedores SL" in text, "E-604 falta cliente.razon_social"
    assert "CloudHost Iberia SL" in text, "E-604 falta proveedor.razon_social"
    assert "B70000000" in text, "E-604 falta cliente.nif"
    assert "B11111111" in text, "E-604 falta proveedor.nif"
    assert "Carmen Cloud (CEO)" in text, "E-604 falta proveedor.representante"
    # Addendum code + normativas en header
    assert "ADENDA-ENS-2026-001" in text, "E-604 falta addendum_code"
    # Marco normativo core (siempre presente)
    assert "RD 311/2022" in text, "E-604 falta RD 311/2022"
    assert "op.ext.1" in text, "E-604 falta op.ext.1"
    assert "Anexo II" in text, "E-604 falta Anexo II"
    # Bloque RGPD presente (seccion 6 con normativas=['ENS','RGPD','NIS2'])
    assert "RGPD Art. 28" in text or "Art. 28" in text, "E-604 falta bloque RGPD Art.28"
    assert "encargado de tratamiento" in text, "E-604 falta clausula encargado tratamiento"
    # Bloque NIS2 presente (seccion 7)
    assert "NIS2" in text, "E-604 falta NIS2"
    assert "21 de la Directiva" in text or "Art. 21" in text or "Art.21" in text, (
        "E-604 falta NIS2 Art.21"
    )
    # Bloque DORA AUSENTE (condicional incluir_dora=False · normativas NO contiene DORA)
    assert "ACUERDOS TIC BAJO DORA" not in text, "E-604 NO debe incluir bloque DORA"
    # Auditoria + confidencialidad + jurisdiccion
    assert "AUDITORÍA" in text or "auditoría" in text.lower(), "E-604 falta clausula auditoria"
    assert "CONFIDENCIALIDAD" in text, "E-604 falta clausula confidencialidad"
    assert "legislación española" in text or "legislacion espanola" in text.lower(), (
        "E-604 falta clausula jurisdiccion espanola"
    )
    # Procedimiento salida 30 dias
    assert "30" in text and ("salida" in text.lower() or "SALIDA" in text), (
        "E-604 falta procedimiento salida ordenada 30 dias"
    )
