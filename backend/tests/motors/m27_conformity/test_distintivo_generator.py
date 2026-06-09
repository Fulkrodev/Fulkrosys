"""Tests Distintivo + Declaración Conformidad CCN-STIC 809 · SAN-C.MB-9.2.

5 cases:

1. ``test_template_e180_exists`` — template MD canónico Declaración existe.
2. ``test_derive_cert_id_idempotent`` — uuid5 determinístico desde project_id.
3. ``test_generate_distintivo_svg_valid`` — SVG canónico con cert_id +
   categoría + cliente embebidos.
4. ``test_generate_declaration_docx_valid`` — DOCX OOXML válido E-180.
5. ``test_svg_xml_escapes_special_chars`` — escape correcto de & < > " en
   client_name (defensa XSS si se sirve embebido).
"""
from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path

import pytest

from backend.app.motors.m27_conformity.distintivo_generator import (
    DECLARATION_DOCUMENT_KIND,
    DEFAULT_VALIDITY_YEARS,
    DistintivoContext,
    derive_cert_id,
    generate_declaration_docx,
    generate_distintivo_svg,
)


_TEMPLATES_DIR = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "motors"
    / "m06_document_factory"
    / "templates"
    / "policies"
)


def test_template_e180_exists():
    """Template E-180 Declaración Conformidad MD existe en M06."""
    template_path = _TEMPLATES_DIR / "E180_declaracion_conformidad.md"
    assert template_path.exists()
    body = template_path.read_text(encoding="utf-8")
    assert "Declaración de Conformidad" in body
    assert "CCN-STIC 809" in body
    # #2 Ola 7 · la Declaración la firma la Dirección (no el RSeg).
    assert "Dirección" in body
    assert "art. 33" in body or "art. 31" in body


def test_derive_cert_id_idempotent():
    """uuid5 derivado de project_id es estable (idempotente)."""
    project_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    cert_a = derive_cert_id(project_id)
    cert_b = derive_cert_id(project_id)
    assert cert_a == cert_b
    # Distintos project_id producen distintos cert_id
    other = uuid.UUID("11111111-2222-3333-4444-555555555556")
    assert derive_cert_id(other) != cert_a


def _ctx_minimal() -> DistintivoContext:
    return DistintivoContext(
        project_id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        cert_id=derive_cert_id(uuid.UUID("11111111-2222-3333-4444-555555555555")),
        client_name="Acme S.L.",
        client_cif="B12345678",
        client_domicilio="Calle Mayor 1, Madrid",
        system_name="Sede electrónica",
        system_category="BASICA",
        today="2026-05-05",
        expiry_date="2028-05-05",
        public_badge_url="https://example.com/api/v1/public/conformity/badge/x/badge.svg",
        services_summary="Tramitación electrónica",
        information_summary="Datos personales",
        assets_essential_count=8,
        dda_total=73,
        dda_aplicables=68,
        dda_con_refuerzos=12,
        dda_no_aplica=5,
        conformes_count=66,
        no_conformes_count=14,
        pct_conformidad=82.5,
        rseg_name="Ana Ruiz",
        rseg_email="ana@acme.es",
        # #2 Ola 7 · firmante de la Declaración = Dirección (sponsor).
        sponsor_name="Ana Ruiz",
        sponsor_email="ana@acme.es",
    )


def test_generate_distintivo_svg_valid():
    """SVG canónico con cert_id + categoría + cliente embebidos."""
    ctx = _ctx_minimal()
    svg = generate_distintivo_svg(ctx)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "ESQUEMA NACIONAL DE SEGURIDAD" in svg
    assert "BASICA" in svg
    assert "Acme S.L." in svg
    assert "Sede electrónica" in svg
    assert str(ctx.cert_id)[:8] in svg
    assert "2026" in svg


def test_distintivo_uses_canonical_pantone_color_all_categories():
    """F-14-06 (Ejecutable 8 Pasada 16): el distintivo usa Pantone Orange 021C
    (#FE5000) por CCN-STIC 809 · ÚNICO para todas las categorías, NO verde/azul/
    violeta por categoría. Fuente: CCN-STIC 809 + fulkro_identity."""
    import dataclasses
    from backend.app.fulkro_identity import (
        FULKRO_DISTINTIVO_COLOR_PANTONE_ORANGE_021C as PANTONE,
    )
    for cat in ("BASICA", "MEDIA", "ALTA"):
        svg = generate_distintivo_svg(
            dataclasses.replace(_ctx_minimal(), system_category=cat),
        )
        assert PANTONE in svg, f"{cat}: falta color canónico {PANTONE}"
        # Colores por categoría antiguos ausentes
        for old in ("#15803D", "#1D4ED8", "#7C3AED"):
            assert old not in svg, f"{cat}: color obsoleto {old} presente"


def test_generate_declaration_docx_valid():
    """Declaración DOCX OOXML válido con secciones canónicas E-180."""
    ctx = _ctx_minimal()
    bio = generate_declaration_docx(ctx)
    assert isinstance(bio, io.BytesIO)
    data = bio.getvalue()
    assert len(data) > 1500

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert "word/document.xml" in zf.namelist()
        doc_xml = zf.read("word/document.xml").decode("utf-8")
        assert "Declaración de Conformidad" in doc_xml
        assert "Acme S.L." in doc_xml
        assert "B12345678" in doc_xml
        assert "BASICA" in doc_xml
        assert str(ctx.cert_id) in doc_xml
        assert "Ana Ruiz" in doc_xml
        assert DECLARATION_DOCUMENT_KIND in doc_xml
        assert f"{DEFAULT_VALIDITY_YEARS} años" in doc_xml


def test_svg_xml_escapes_special_chars():
    """SVG escapa correctamente <, >, &, " (defensa contra inyección XML)."""
    ctx = _ctx_minimal()
    ctx.client_name = "Acme & <Sons> S.L."
    svg = generate_distintivo_svg(ctx)
    assert "<Sons>" not in svg
    assert "&lt;Sons&gt;" in svg
    assert "&amp;" in svg
