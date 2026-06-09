"""Tests for retainer DOCX report renderer · MB-7.bis atom 7.bis.4."""
import io
import uuid
from datetime import date

import pytest
from docx import Document
from sqlalchemy import text

from backend.app.motors.m23_retainer.report_renderer import (
    render_annual_report_docx,
    render_quarterly_report_docx,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed_retainer_with_report(
    db, *, period_start: str = "2026-01-01",
) -> tuple[uuid.UUID, uuid.UUID, str]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    retainer_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'AcmeCorp SA', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects "
            "(id, client_id, nombre, fase, categoria_objetivo, created_at) "
            "VALUES (:id, :cid, 'ENS Project', 'retainer_cierre', 'MEDIA', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO retainer_contracts "
            "(id, client_id, project_id, modalidad, precio_mensual, "
            " perfil, estado, inicio, created_at) "
            "VALUES (:id, :cid, :pid, 'mensual', 700, 'R_STD', 'activo', "
            " '2026-01-01', now())"
        ), {
            "id": str(retainer_id),
            "cid": str(client_id),
            "pid": str(project_id),
        })
        await db.execute(text(
            "INSERT INTO retainer_quarterly_reports "
            "(id, retainer_contract_id, project_id, period_type, "
            " period_start, period_end, activities_completed, "
            " activities_pending, activities_overdue, incidents_detected, "
            " normativa_changes_relevant, vulns_critical, rag_overall, "
            " admin_curation_status, schema_version, created_at, updated_at) "
            "VALUES (:id, :rid, :pid, 'quarterly', "
            " :ps, :pe, "
            " 8, 2, 1, 3, 5, 0, 'amber', 'draft', '1.0', now(), now())"
        ), {
            "id": str(uuid.uuid4()),
            "rid": str(retainer_id),
            "pid": str(project_id),
            "ps": date.fromisoformat(period_start),
            "pe": date(2026, 3, 31),
        })
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(client_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(project_id)},
    )
    await db.flush()
    return client_id, retainer_id, period_start


async def test_render_quarterly_report_produces_valid_docx(db):
    _, retainer_id, period_start = await _seed_retainer_with_report(db)

    blob = await render_quarterly_report_docx(db, retainer_id, period_start)
    assert isinstance(blob, bytes)
    assert len(blob) > 1000  # DOCX should be at least ~1KB

    # Round-trip parse to verify it's a valid DOCX
    doc = Document(io.BytesIO(blob))
    text_concat = "\n".join(p.text for p in doc.paragraphs)
    assert "AcmeCorp SA" in text_concat
    assert "Informe Trimestral Retainer" in text_concat
    # KV table should include R_STD perfil
    table_text = " ".join(
        c.text for tbl in doc.tables for row in tbl.rows for c in row.cells
    )
    assert "R_STD" in table_text


async def test_render_annual_report_aggregates_quarters(db):
    _, retainer_id, _ = await _seed_retainer_with_report(
        db, period_start="2026-04-01",
    )
    # Add Q2 same year
    project_id = (await db.execute(text(
        "SELECT project_id FROM retainer_contracts WHERE id = :r"
    ), {"r": str(retainer_id)})).scalar()

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO retainer_quarterly_reports "
            "(id, retainer_contract_id, project_id, period_type, "
            " period_start, period_end, activities_completed, "
            " activities_pending, activities_overdue, incidents_detected, "
            " normativa_changes_relevant, vulns_critical, rag_overall, "
            " admin_curation_status, schema_version, created_at, updated_at) "
            "VALUES (:id, :rid, :pid, 'quarterly', "
            " :ps, :pe, 10, 1, 0, 1, 3, 0, 'green', "
            " 'draft', '1.0', now(), now())"
        ), {
            "id": str(uuid.uuid4()),
            "rid": str(retainer_id),
            "pid": str(project_id),
            "ps": date(2026, 7, 1),
            "pe": date(2026, 9, 30),
        })
    await db.flush()

    blob = await render_annual_report_docx(db, retainer_id, 2026)
    assert isinstance(blob, bytes)
    doc = Document(io.BytesIO(blob))
    table_text = " ".join(
        c.text for tbl in doc.tables for row in tbl.rows for c in row.cells
    )
    # Aggregated totals · 8 + 10 = 18 completadas, 1 + 0 = 1 vencidas
    assert "18" in table_text
    # Worst RAG between amber (Q2) and green (Q3) is amber
    assert "Ámbar" in table_text or "amber" in table_text.lower()


async def test_render_quarterly_report_unknown_retainer_raises(db):
    with pytest.raises(ValueError):
        await render_quarterly_report_docx(db, uuid.uuid4(), "2026-01-01")
