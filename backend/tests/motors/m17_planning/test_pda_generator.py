"""Tests Plan de Adecuación CCN-STIC 806 generator · SAN-C.MB-9.3.

3 cases:

1. ``test_template_e150_exists`` — sanity check del template MD canónico.
2. ``test_generate_pda_docx_minimal`` — generador produce DOCX válido
   con context sintético mínimo.
3. ``test_pda_context_with_real_project`` — build_pda_context contra
   proyecto sintético (categorización + DdA stub).
"""
from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m17_planning.pda_generator import (
    PDA_DOCUMENT_KIND,
    PdaContext,
    build_pda_context,
    generate_pda_docx,
)
from backend.tests.conftest import _admin_setup


def test_template_e150_exists():
    """Template MD canónico CCN-STIC 806 existe en M06 templates/policies/."""
    template_path = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "motors"
        / "m06_document_factory"
        / "templates"
        / "policies"
        / "E150_plan_adecuacion.md"
    )
    assert template_path.exists(), f"Missing template: {template_path}"
    body = template_path.read_text(encoding="utf-8")
    assert "Plan de Adecuación" in body
    assert "Política de Seguridad aprobada" in body
    assert "Análisis de Riesgos" in body
    assert "RSEG" in body


def test_generate_pda_docx_minimal():
    """Generator produce un DOCX válido (zip OOXML) con context mínimo."""
    ctx = PdaContext(
        project_id=uuid.uuid4(),
        client_name="Acme S.L.",
        system_name="Sede electrónica municipal",
        system_category="MEDIA",
        today="2026-05-05",
        psi_version="1.0",
        dimensions=[
            {
                "code": "C",
                "name": "Confidencialidad",
                "level": "MEDIO",
                "justification": "Datos personales art.9 RGPD"
            },
        ],
        dda_total=73,
        dda_aplicables=68,
        dda_con_refuerzos=24,
        dda_no_aplica=5,
        risk_scenarios_count=42,
        gap_summary=[
            {
                "family": "org",
                "aplicables": 4,
                "conformes": 1,
                "no_conformes": 3,
                "pct_conformidad": 25.0,
            },
        ],
        plan_tasks=[
            {
                "code": "WBS-001",
                "title": "Aprobar PSI",
                "description": "Aprobación formal Direccion",
                "ens_measure": "org.1",
                "responsible_role": "RSEG",
                "priority": "alta",
                "effort_hours": 16,
                "target_date": "2026-06-01",
                "cost_eur": 1200,
            },
        ],
    )

    bio = generate_pda_docx(ctx)
    assert isinstance(bio, io.BytesIO)
    data = bio.getvalue()
    assert len(data) > 1000, "DOCX should have substantial content"

    # Verify it's a valid OOXML zip with document.xml
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        assert "word/document.xml" in names
        doc_xml = zf.read("word/document.xml").decode("utf-8")
        assert "Acme S.L." in doc_xml
        assert "Sede electrónica municipal" in doc_xml
        assert "MEDIA" in doc_xml
        assert "WBS-001" in doc_xml
        assert "Aprobar PSI" in doc_xml
        assert PDA_DOCUMENT_KIND in doc_xml


@pytest.mark.asyncio
async def test_pda_context_with_real_project(db: AsyncSession):
    """build_pda_context devuelve PdaContext válido para proyecto sintético."""
    from backend.app.database import set_tenant_context

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:cid, :nombre, :cif, 'publico', now())"
            ),
            {"cid": str(client_id), "nombre": f"Test PdA {cif}", "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:pid, :cid, :nombre, 'adecuacion', now())"
            ),
            {
                "pid": str(project_id),
                "cid": str(client_id),
                "nombre": "Proyecto PdA Test",
            },
        )

    # build_pda_context queries as fulkro_app · necesita tenant_context para RLS
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    ctx = await build_pda_context(db, project_id)
    assert ctx.project_id == project_id
    assert "Test PdA" in ctx.client_name
    assert ctx.system_name == "Proyecto PdA Test"
    assert ctx.system_category in ("BASICA", "MEDIA", "ALTA")
    # Categorización no creada → default BASICA
    assert ctx.system_category == "BASICA"
    # 5 dimensiones CIDAT siempre listadas (nivel default)
    assert len(ctx.dimensions) == 5
    assert {d["code"] for d in ctx.dimensions} == {"D", "I", "C", "A", "T"}
