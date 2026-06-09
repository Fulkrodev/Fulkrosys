"""Integration tests WHISTLEBLOWING templates W-001 + W-002 · sub-lote 1.B.8.B.

Adyacencia normativa NO-ENS (Ley 2/2023 reguladora proteccion personas que
informan sobre infracciones · transposicion Directiva UE 2019/1937).

Codigos W-001 (politica · policies/) + W-002 (procedimiento · procedures/)
segregados del rango E-1XX/E-2XX por clara separacion normativa
(AMEND-016 v2 + LECCION-OPS-032 test aplicabilidad target).

Reglas duras sostenidas (LECCION-OPS-020 / 021 / 027 / 028 / 030).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from backend.app.motors.m06_document_factory.rendering import render_docx

VAR_TEMPLATES = Path(__file__).resolve().parents[4] / "var" / "templates_docx"
PLACEHOLDER_PATTERN = re.compile(r"\{\{|\{%|%\}|\}\}")

WHISTLEBLOWING_TEMPLATES = ["W-001", "W-002"]


@pytest.fixture
def whistleblowing_context() -> dict:
    """Context para render W-001 + W-002 · empresa privada tramo 50-249 emp."""
    return {
        "cliente": {
            "razon_social": "Test Whistleblowing SL",
            "nif": "B80000000",
            # 120 dispara branch obligacion_aplica=True + tramo 50-249
            "numero_empleados": 120,
            "sector_actividad": "Servicios profesionales · consultoria",
            "organo_aprobador_politicas": "Comite de Direccion Test",
            "canal_denuncias_url": "https://canal-denuncias.test-wb.example",
        },
        "proyecto": {
            "version_actual": "1.0",
            "fecha_aprobacion_inicial": "2026-05-18",
        },
        "responsables": {
            "responsable_compliance": {
                "nombre": "RC Test",
                "cargo": "Compliance Officer",
            },
            "responsable_sii": {
                "nombre": "RSII Test",
                "cargo": "Compliance Officer · Responsable SII",
                "fecha_designacion": "2026-01-15",
                "mandato_min_3_anios": True,
            },
            "delegado_proteccion_datos": {
                "nombre": "DPO Test",
                "cargo": "DPO",
                "email": "dpo@test-wb.example",
            },
        },
    }


@pytest.mark.parametrize("codigo", WHISTLEBLOWING_TEMPLATES)
def test_whistleblowing_template_renders_without_placeholder_leak(
    codigo, tmp_path, whistleblowing_context,
):
    template_path = VAR_TEMPLATES / f"{codigo}.docx"
    assert template_path.exists(), f"Missing precompiled template: {template_path}"

    output_path = tmp_path / f"{codigo}_test.docx"
    render_docx(template_path, whistleblowing_context, output_path)

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
    # razon_social aparece en H1 upper-cased + en cuerpo · al menos uppercase
    assert "TEST WHISTLEBLOWING SL" in text, (
        f"{codigo} missing cliente.razon_social en H1 (upper)"
    )


def test_w001_renders_50_employee_threshold_branch(tmp_path, whistleblowing_context):
    """W-001 con numero_empleados=120 debe activar branch obligacion_aplica=True
    + tramo 50-249 (mostrando fecha limite 17 diciembre 2023 vs 1 diciembre 2023
    si >249). Validacion ademas: cita Ley 2/2023 + Directiva UE 2019/1937 +
    AAI + plazo conservacion 10 anios + sancion 1.000.000 EUR."""
    template_path = VAR_TEMPLATES / "W-001.docx"
    output_path = tmp_path / "W-001_semantic.docx"
    render_docx(template_path, whistleblowing_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Branch obligacion_aplica (>=50 empleados)
    assert "120 personas empleadas" in text, (
        "W-001 falta numero_empleados en branch obligacion"
    )
    assert "obligada" in text, "W-001 falta texto 'obligada' branch >=50"
    # Branch tramo 50-249 (NO 1 diciembre)
    assert "17 de diciembre de 2023" in text, (
        "W-001 falta fecha tramo 50-249 (17 dic 2023)"
    )
    # NO debe contener fecha tramo >249 con esta config
    assert "1 de diciembre de 2023" not in text, (
        "W-001 NO debe contener fecha tramo >249 con 120 empleados"
    )
    # Marco normativo core
    assert "Ley 2/2023" in text, "W-001 falta Ley 2/2023"
    assert "Directiva (UE) 2019/1937" in text or "2019/1937" in text, (
        "W-001 falta Directiva UE 2019/1937"
    )
    assert "Autoridad Independiente de Protección al Informante" in text or "AAI" in text, (
        "W-001 falta AAI"
    )
    # Plazo conservacion + sancion
    assert "diez (10) años" in text or "10) años" in text, (
        "W-001 falta plazo conservacion 10 años"
    )
    assert "1.000.000" in text or "un millón" in text.lower(), (
        "W-001 falta sancion 1M EUR"
    )
    # Responsable SII presente
    assert "RSII Test" in text, "W-001 falta responsable_sii.nombre"


def test_w002_renders_procedure_phases(tmp_path, whistleblowing_context):
    """W-002 debe renderizar 6 fases procedimiento (Recepcion + Analisis +
    Decision admision + Investigacion + Decision medidas + Cierre) +
    plazos Ley 2/2023 + DPO role + indicadores operativos."""
    template_path = VAR_TEMPLATES / "W-002.docx"
    output_path = tmp_path / "W-002_semantic.docx"
    render_docx(template_path, whistleblowing_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # 6 fases procedimiento (acepta mayuscula o minuscula)
    fases_phrases = [
        "Recepción", "Análisis preliminar", "admisión",
        "Investigación", "medidas correctivas", "Cierre",
    ]
    for phrase in fases_phrases:
        assert phrase in text, f"W-002 falta fase procedimiento: {phrase}"
    # Plazos Ley 2/2023
    assert "siete (7) días naturales" in text, "W-002 falta plazo 7 dias acuse"
    assert "tres (3) meses" in text, "W-002 falta plazo 3 meses investigacion"
    # DPO role
    assert "DPO Test" in text, "W-002 falta DPO"
    assert "Delegado de Protección de Datos" in text, "W-002 falta DPO rol completo"
    # Indicadores operativos table
    assert "Indicador" in text or "INDICADOR" in text.upper(), (
        "W-002 falta tabla indicadores"
    )
    assert "100%" in text, "W-002 falta objetivo 100% indicadores"
    # Marco Ley 2/2023 + RGPD
    assert "Ley 2/2023" in text, "W-002 falta Ley 2/2023"
    assert "RGPD" in text, "W-002 falta RGPD"
    # Politica madre W-001 referenciada
    assert "W-001" in text, "W-002 falta referencia politica madre W-001"
