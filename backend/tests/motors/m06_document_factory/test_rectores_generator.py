"""Tests Manual SGSI + Plan Director generators · SAN-C.MB-9.4.

4 cases:

1. ``test_template_e160_exists`` — Manual SGSI MD canónico existe.
2. ``test_template_e170_exists`` — Plan Director MD canónico existe.
3. ``test_generate_manual_sgsi_docx_valid`` — DOCX OOXML válido con
   contenido esperado.
4. ``test_generate_plan_director_docx_valid`` — DOCX OOXML válido con
   secciones canónicas.
"""
from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path


from backend.app.motors.m06_document_factory.rectores_generator import (
    RectoresContext,
    generate_manual_sgsi_docx,
    generate_plan_director_docx,
)


_TEMPLATES_DIR = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "motors"
    / "m06_document_factory"
    / "templates"
    / "policies"
)


def test_template_e160_exists():
    """Manual SGSI E-160 template MD canónico existe."""
    template_path = _TEMPLATES_DIR / "E160_manual_sgsi.md"
    assert template_path.exists()
    body = template_path.read_text(encoding="utf-8")
    assert "Manual del Sistema de Gestión de Seguridad" in body
    assert "Roles y responsabilidades" in body
    assert "CCN-STIC 801" in body
    assert "4 niveles" in body
    assert "RSEG" in body and "RSIS" in body


def test_template_e170_exists():
    """Plan Director Seguridad E-170 template MD canónico existe."""
    template_path = _TEMPLATES_DIR / "E170_plan_director.md"
    assert template_path.exists()
    body = template_path.read_text(encoding="utf-8")
    assert "Plan Director de Seguridad" in body
    assert "Misión" in body or "misión" in body
    assert "trianual" in body.lower()
    assert "CCN-STIC 815" in body or "KPIs" in body


def _ctx_minimal() -> RectoresContext:
    return RectoresContext(
        project_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        client_name="Acme Pública S.A.",
        system_name="Sede electrónica",
        system_category="MEDIA",
        today="2026-05-05",
        services_summary="Tramitación electrónica + sede digital",
        assets_essential_count=12,
        roles_table=[
            {
                "role_name": "Responsable Seguridad",
                "person": "Ana Ruiz",
                "email": "ana@acme.es",
                "functions": "CISO ENS",
            },
            {
                "role_name": "Responsable Sistema",
                "person": "Bob Pérez",
                "email": "bob@acme.es",
                "functions": "Sysadmin",
            },
        ],
        sponsor_name="Carlos Director",
        rseg_name="Ana Ruiz",
        comite_chair="Diego Comité",
    )


def test_generate_manual_sgsi_docx_valid():
    """Manual SGSI DOCX es zip OOXML válido con contenido esperado."""
    ctx = _ctx_minimal()
    bio = generate_manual_sgsi_docx(ctx)
    assert isinstance(bio, io.BytesIO)
    data = bio.getvalue()
    assert len(data) > 1500

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert "word/document.xml" in zf.namelist()
        doc_xml = zf.read("word/document.xml").decode("utf-8")
        assert "Acme Pública S.A." in doc_xml
        assert "Sede electrónica" in doc_xml
        assert "MEDIA" in doc_xml
        assert "Ana Ruiz" in doc_xml
        assert "RSEG" in doc_xml or "Responsable Seguridad" in doc_xml
        assert "CCN-STIC 805" in doc_xml or "4 niveles" in doc_xml


def test_generate_plan_director_docx_valid():
    """Plan Director DOCX es zip OOXML válido con secciones canónicas."""
    ctx = _ctx_minimal()
    bio = generate_plan_director_docx(ctx)
    assert isinstance(bio, io.BytesIO)
    data = bio.getvalue()
    assert len(data) > 1500

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert "word/document.xml" in zf.namelist()
        doc_xml = zf.read("word/document.xml").decode("utf-8")
        assert "Plan Director de Seguridad" in doc_xml
        assert "Acme Pública S.A." in doc_xml
        assert "trianual" in doc_xml.lower()
        assert "Carlos Director" in doc_xml or "Sponsor" in doc_xml
        assert "CCN-STIC 815" in doc_xml or "KPI" in doc_xml
