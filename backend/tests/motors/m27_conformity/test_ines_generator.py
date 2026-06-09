"""Tests INES Annual Report generator · SAN-C.MB-10.4."""
from __future__ import annotations

import io
import uuid
import zipfile

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m27_conformity.ines_generator import (
    INES_SCHEMA_VERSION,
    InesYearReport,
    collect_ines_data,
    generate_ines_docx,
    generate_ines_json,
)
from backend.tests.conftest import _admin_setup


def _sample_report() -> InesYearReport:
    return InesYearReport(
        organization_name="Ayuntamiento Test",
        organization_cif="P12345678",
        year=2026,
        today="2026-12-31",
        systems=[{
            "system_id": str(uuid.uuid4()),
            "name": "Sede electrónica",
            "category": "MEDIA",
            "lifecycle_phase": "conformidad",
            "target_certification_date": "2026-09-30",
        }],
        incidents_summary={"BAJA": 5, "MEDIA": 2, "ALTA": 1, "CRITICA": 0},
        maturity_avg=2.8,
        investment_eur=45000.0,
        rseg_name="Ana RSEG",
        plan_year_next=[
            "Renovar auditoría externa Q3 2027",
            "Implantar SIEM corporativo",
        ],
    )


def test_generate_ines_json_canonical_schema():
    report = _sample_report()
    payload = generate_ines_json(report)
    assert payload["@schema"] == INES_SCHEMA_VERSION
    assert payload["organization"]["name"] == "Ayuntamiento Test"
    assert payload["organization"]["cif"] == "P12345678"
    assert payload["year"] == 2026
    assert payload["incidents_summary"]["ALTA"] == 1
    assert payload["maturity_avg_cmm"] == 2.8
    assert payload["investment_security_eur"] == 45000.0
    assert len(payload["systems_in_scope"]) == 1
    assert len(payload["next_year_plan"]) == 2


def test_generate_ines_docx_valid():
    report = _sample_report()
    bio = generate_ines_docx(report)
    assert isinstance(bio, io.BytesIO)
    data = bio.getvalue()
    assert len(data) > 1500
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert "word/document.xml" in zf.namelist()
        doc_xml = zf.read("word/document.xml").decode("utf-8")
        assert "Ayuntamiento Test" in doc_xml
        assert "Sede electr" in doc_xml  # encoding tolerant
        assert "MEDIA" in doc_xml
        assert "Ana RSEG" in doc_xml
        assert "2026" in doc_xml


@pytest.mark.asyncio
async def test_collect_ines_data_with_real_org(db: AsyncSession):
    """collect_ines_data agrega datos cross-motor para una org real."""
    from backend.app.database import set_tenant_context

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"P{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:cid, :nombre, :cif, 'publico', now())"
            ),
            {"cid": str(client_id), "nombre": "INES Test Ayto", "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:pid, :cid, 'Sistema INES test', 'conformidad', now())"
            ),
            {"pid": str(project_id), "cid": str(client_id)},
        )

    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    report = await collect_ines_data(db, client_id, 2026)

    assert report.organization_name == "INES Test Ayto"
    assert report.year == 2026
    assert any(s["name"] == "Sistema INES test" for s in report.systems)
