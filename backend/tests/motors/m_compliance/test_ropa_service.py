"""RoPA Service tests (atom 9.bis.3).

5 tests covering:
- 10 seed treatments present + ordered by code
- Excel export produces a valid XLSX with the expected sheets/columns
- list_treatments returns all rows
- mark_reviewed updates last_reviewed_at
- update_treatment validates allowed fields
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from openpyxl import load_workbook

from backend.app.motors.m_compliance.ropa_service import RoPAService


@pytest.mark.asyncio
async def test_seed_10_treatments_present(db) -> None:
    svc = RoPAService(db)
    rows = await svc.list_treatments()
    codes = [r.treatment_code for r in rows]
    assert codes == [f"T{i:03d}" for i in range(1, 11)]
    # Sub-processor count from seed: T001/T002/T003/T004/T008.
    sub_count = await svc.count_sub_processors()
    assert sub_count == 5


@pytest.mark.asyncio
async def test_excel_export_aepd_format(db) -> None:
    svc = RoPAService(db)
    buf = await svc.export_aepd_excel()
    assert isinstance(buf, BytesIO)
    wb = load_workbook(buf)
    assert "RoPA" in wb.sheetnames
    assert "Metadatos" in wb.sheetnames

    ws = wb["RoPA"]
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    assert "Código" in headers
    assert "Finalidad (Art. 30.1.b)" in headers
    assert "Base jurídica (Art. 6)" in headers
    # 10 data rows + 1 header.
    assert ws.max_row == 11

    meta = wb["Metadatos"]
    meta_labels = [meta.cell(row=i, column=1).value for i in range(1, meta.max_row + 1)]
    assert "Email DPO" in meta_labels
    assert "Base regulatoria" in meta_labels


@pytest.mark.asyncio
async def test_list_treatments_returns_all(db) -> None:
    rows = await RoPAService(db).list_treatments()
    assert len(rows) == 10
    # Every treatment carries a regulatory basis.
    for r in rows:
        assert r.legal_basis
        assert r.retention_period
        assert r.security_measures


@pytest.mark.asyncio
async def test_mark_reviewed_updates_timestamp(db) -> None:
    svc = RoPAService(db)
    before = await svc.get_treatment("T001")
    assert before is not None
    original = before.last_reviewed_at
    # Move the original timestamp back so the update is observable even on
    # fast hardware where two NOW() calls produce identical timestamps.
    before.last_reviewed_at = original - timedelta(days=1)
    await db.flush()

    updated = await svc.mark_reviewed("T001")
    assert updated.last_reviewed_at > original - timedelta(days=1)


@pytest.mark.asyncio
async def test_update_treatment_rejects_invalid_fields(db) -> None:
    svc = RoPAService(db)
    with pytest.raises(ValueError) as excinfo:
        await svc.update_treatment(
            "T001",
            {"not_a_real_field": "anything"},
        )
    assert "not updatable" in str(excinfo.value)

    # And rejects missing treatments.
    with pytest.raises(KeyError):
        await svc.update_treatment("T999", {"treatment_name": "x"})

    # Happy path: valid field update succeeds.
    row = await svc.update_treatment(
        "T002",
        {"retention_period": "Test override 6 months"},
    )
    assert row.retention_period == "Test override 6 months"
