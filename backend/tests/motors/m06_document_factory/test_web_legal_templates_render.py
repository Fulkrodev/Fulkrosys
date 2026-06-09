"""Integration tests WEB-LEGAL templates LW-001 + LW-002 + LW-003 · sub-lote 1.B.8.C.

Adyacencia normativa NO-ENS (LSSI Ley 34/2002 + RGPD + Guia AEPD Cookies)
para sitio web corporativo del cliente.

Codigos LW-001 (politica privacidad web · policies/) + LW-002 (politica
cookies · policies/) + LW-003 (aviso legal LSSI art. 10 · policies/)
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

WEB_LEGAL_TEMPLATES = ["LW-001", "LW-002", "LW-003"]


@pytest.fixture
def web_legal_context() -> dict:
    """Context para render LW-001 + LW-002 + LW-003 · cliente con dominio web.

    Activa ramas:
      - cliente.tiene_transferencias_internacionales=True (LW-001 sec 5)
      - cliente.cookies_detail con 2 entries (LW-002 sec 4 branch loop)
      - cliente.datos_registrales custom (LW-003 sec 1)
      - cliente.proposito_sitio_web custom (LW-003 sec 3)
    """
    return {
        "cliente": {
            "razon_social": "Test Web Legal SL",
            "nif": "B72500000",
            "domicilio": "Calle Web 10, 28001 Madrid",
            "dominio_web": "www.test-web-legal.example",
            "telefono": "+34 910 555 000",
            "tiene_transferencias_internacionales": True,
            "datos_registrales": (
                "Reg. Mercantil Madrid · Tomo 9999 · Folio 1 · Hoja M-12345"
            ),
            "proposito_sitio_web": (
                "presentar la actividad de consultoria en seguridad de la informacion"
            ),
            "cookies_detail": [
                {
                    "nombre": "session_id",
                    "tipo": "tecnica propia",
                    "propietario": "Test Web Legal SL",
                    "finalidad": "Mantener sesion del usuario",
                    "duracion": "Sesion",
                },
                {
                    "nombre": "_ga",
                    "tipo": "analitica tercero",
                    "propietario": "Google Analytics",
                    "finalidad": "Medicion uso anonima del sitio",
                    "duracion": "2 anios",
                },
            ],
            "contacto_compliance": {
                "email": "compliance@test-web-legal.example",
            },
            "contacto_general": {
                "email": "info@test-web-legal.example",
            },
        },
        "proyecto": {
            "version_actual": "1.0",
            "fecha_aprobacion_inicial": "2026-05-18",
        },
        "responsables": {
            "delegado_proteccion_datos": {
                "nombre": "DPO Test",
                "cargo": "DPO",
                "email": "dpo@test-web-legal.example",
            },
        },
    }


@pytest.mark.parametrize("codigo", WEB_LEGAL_TEMPLATES)
def test_web_legal_template_renders_without_placeholder_leak(
    codigo, tmp_path, web_legal_context,
):
    template_path = VAR_TEMPLATES / f"{codigo}.docx"
    assert template_path.exists(), f"Missing precompiled template: {template_path}"

    output_path = tmp_path / f"{codigo}_test.docx"
    render_docx(template_path, web_legal_context, output_path)

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
    # razon_social aparece en H1 upper-cased · validacion anchor
    assert "TEST WEB LEGAL SL" in text, (
        f"{codigo} missing cliente.razon_social en H1 (upper)"
    )


def test_lw001_renders_rgpd_rights_aepd_and_transferencias_branch(
    tmp_path, web_legal_context,
):
    """LW-001 con tiene_transferencias_internacionales=True debe activar branch
    afirmativo (garantias arts. 44-49 RGPD). Validacion ademas: marco normativo
    RGPD + LOPDGDD + LSSI + 8 derechos interesado + AEPD + DPO + referencias
    LW-002 cookies."""
    template_path = VAR_TEMPLATES / "LW-001.docx"
    output_path = tmp_path / "LW-001_semantic.docx"
    render_docx(template_path, web_legal_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Branch tiene_transferencias_internacionales=True (afirmativa)
    assert "44 a 49 del RGPD" in text or "44 a 49" in text, (
        "LW-001 falta branch afirmativo transferencias (arts. 44-49 RGPD)"
    )
    assert "no realiza transferencias internacionales" not in text, (
        "LW-001 NO debe contener branch negativo cuando transferencias=True"
    )
    # Marco normativo core
    assert "RGPD" in text, "LW-001 falta RGPD"
    assert "LOPDGDD" in text, "LW-001 falta LOPDGDD"
    # 8 derechos interesado (art. 15-22 RGPD + revocacion consentimiento)
    derechos = [
        "Acceso", "Rectificación", "Supresión",
        "Limitación", "Portabilidad", "Oposición",
    ]
    for d in derechos:
        assert d in text, f"LW-001 falta derecho RGPD: {d}"
    # AEPD reclamacion
    assert "AEPD" in text or "Agencia Española de Protección de Datos" in text, (
        "LW-001 falta AEPD"
    )
    assert "sedeaepd.gob.es" in text, "LW-001 falta sede AEPD"
    # DPO presente
    assert "DPO Test" in text, "LW-001 falta nombre DPO"
    assert "dpo@test-web-legal.example" in text, "LW-001 falta email DPO"
    # Referencia documento hermano LW-002
    assert "LW-002" in text, "LW-001 falta referencia documento cookies LW-002"
    # Dominio web custom
    assert "www.test-web-legal.example" in text, "LW-001 falta dominio_web custom"


def test_lw002_renders_lssi_22_2_aepd_guide_cookies_detail_loop(
    tmp_path, web_legal_context,
):
    """LW-002 con cookies_detail (2 entries) debe activar branch loop (no else
    generico). Validacion ademas: LSSI art. 22.2 + Guia AEPD Cookies + 4 tipos
    finalidad + banner consentimiento + plazo conservacion 2 anios."""
    template_path = VAR_TEMPLATES / "LW-002.docx"
    output_path = tmp_path / "LW-002_semantic.docx"
    render_docx(template_path, web_legal_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # LSSI art 22.2 core
    assert "22.2" in text, "LW-002 falta articulo 22.2 LSSI"
    assert "Ley 34/2002" in text or "LSSI" in text, "LW-002 falta LSSI"
    # Guia AEPD Cookies referencia
    assert "AEPD" in text, "LW-002 falta AEPD"
    # Branch cookies_detail loop (2 entries especificos)
    assert "session_id" in text, "LW-002 falta cookies_detail entry 1 (session_id)"
    assert "_ga" in text, "LW-002 falta cookies_detail entry 2 (_ga)"
    assert "Google Analytics" in text, "LW-002 falta propietario tercero"
    # NO debe activar else generico cuando cookies_detail presente
    assert "Cookies analíticas (cuando el usuario las acepta)" not in text, (
        "LW-002 NO debe activar branch else cuando cookies_detail presente"
    )
    # 4 tipos cookies segun finalidad
    tipos_finalidad = [
        "técnicas", "preferencias", "analíticas", "publicidad",
    ]
    for tipo in tipos_finalidad:
        assert tipo in text.lower(), f"LW-002 falta tipo finalidad cookie: {tipo}"
    # Banner consentimiento mecanismo
    assert "banner" in text.lower(), "LW-002 falta mecanismo banner cookies"
    # Plazo conservacion registro 2 anios
    assert "dos (2) años" in text, "LW-002 falta plazo conservacion 2 anios"
    # Navegadores enlaces
    assert "Chrome" in text, "LW-002 falta enlace navegador Chrome"
    assert "Firefox" in text, "LW-002 falta enlace navegador Firefox"


def test_lw003_renders_lssi_art10_identification_and_cross_refs(
    tmp_path, web_legal_context,
):
    """LW-003 debe renderizar identificacion LSSI art. 10 completa (incluyendo
    datos_registrales custom + telefono + proposito_sitio_web custom) +
    referencias cruzadas LW-001 + LW-002 + apartados propiedad intelectual y
    ley aplicable."""
    template_path = VAR_TEMPLATES / "LW-003.docx"
    output_path = tmp_path / "LW-003_semantic.docx"
    render_docx(template_path, web_legal_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # LSSI art 10 + Ley 34/2002 core
    assert "Ley 34/2002" in text, "LW-003 falta Ley 34/2002"
    assert "artículo 10" in text or "LSSI" in text, "LW-003 falta LSSI art 10"
    # Identificacion (art 10 LSSI) campos custom
    assert "B72500000" in text, "LW-003 falta NIF cliente"
    assert "Calle Web 10" in text, "LW-003 falta domicilio cliente"
    assert "M-12345" in text, "LW-003 falta datos_registrales custom"
    assert "consultoria en seguridad" in text, (
        "LW-003 falta proposito_sitio_web custom"
    )
    assert "+34 910 555 000" in text, "LW-003 falta telefono"
    # contacto_general.email rama (no contacto_compliance)
    assert "info@test-web-legal.example" in text, (
        "LW-003 falta contacto_general email"
    )
    # Propiedad intelectual e industrial seccion 5
    assert "propiedad intelectual" in text.lower(), (
        "LW-003 falta seccion propiedad intelectual"
    )
    # LSSI art 16 limitacion responsabilidad
    assert "artículo 16 LSSI" in text or "art. 16" in text or "16 LSSI" in text, (
        "LW-003 falta art 16 LSSI limitacion responsabilidad"
    )
    # Referencias cruzadas LW-001 + LW-002 (integracion 3 documentos)
    assert "LW-001" in text, "LW-003 falta referencia LW-001 privacidad"
    assert "LW-002" in text, "LW-003 falta referencia LW-002 cookies"
    # Ley aplicable + jurisdiccion seccion 10
    assert "legislación española" in text, "LW-003 falta ley aplicable española"
    assert "consumidor" in text.lower(), (
        "LW-003 falta criterio consumidor jurisdiccion"
    )
