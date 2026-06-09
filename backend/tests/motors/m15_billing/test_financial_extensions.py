"""Tests M15 Financial Extensions · ADR-046 v3 SAN-E.MB-3.F."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project


BASE = "/api/v1/projects"


@pytest.mark.asyncio
async def test_financial_summary_empty(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/financial-summary")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == project_id
    assert body["totals"]["invoiced"] == 0.0
    assert body["totals"]["paid"] == 0.0
    assert body["totals"]["outstanding"] == 0.0
    assert body["invoices_count"] == 0


@pytest.mark.asyncio
async def test_financial_summary_aggregates_invoices(async_client, db):
    client_id, project_id = await setup_test_project(db)
    # Insertar 3 facturas: 1 pagada · 1 pendiente · 1 anulada
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO invoices (client_id, project_id, total, estado_pago, created_at) "
            "VALUES (:clid, :pid, 1000.00, 'pagada', now()), "
            "(:clid, :pid, 500.00, 'pendiente', now()), "
            "(:clid, :pid, 200.00, 'anulada', now())"
        ), {"clid": client_id, "pid": project_id})
    await db.commit()

    r = await async_client.get(f"{BASE}/{project_id}/financial-summary")
    assert r.status_code == 200, r.text
    body = r.json()
    # invoiced = 1000 + 500 = 1500 (anulada excluida)
    assert body["totals"]["invoiced"] == 1500.0
    assert body["totals"]["paid"] == 1000.0
    assert body["totals"]["outstanding"] == 500.0
    assert body["invoices_count"] == 3
    assert body["invoices_paid_count"] == 1
    assert body["invoices_pending_count"] == 1


@pytest.mark.asyncio
async def test_financial_summary_current_phase_index(async_client, db):
    """#45 E0 · current_phase_index = ordinal canónico de projects.fase (NO el
    milestone_index secuencial · base correcta del timeline)."""
    _, project_id = await setup_test_project(db)
    async with _admin_setup(db):
        await db.execute(text(
            "UPDATE projects SET fase = 'adecuacion' WHERE id = :pid"
        ), {"pid": project_id})
    await db.commit()

    r = await async_client.get(f"{BASE}/{project_id}/financial-summary")
    assert r.status_code == 200, r.text
    # adecuacion = ordinal 4 en WorkflowPhase.ordered() (pre_venta=0 … retainer_cierre=9)
    assert r.json()["current_phase_index"] == 4


@pytest.mark.asyncio
async def test_aapp_billing_status_no_aapp_invoice(async_client, db):
    """Cuando no hay factura AAPP · placeholder graceful."""
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/aapp-billing/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_active_aapp_invoice"] is False
    assert body["stage_facturae_xades"] == "n/a"
    assert body["stage_face"] == "n/a"
    assert body["stage_verifactu"] == "n/a"


@pytest.mark.asyncio
async def test_send_invoice_marks_sent_at(async_client, db):
    client_id, project_id = await setup_test_project(db)
    invoice_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO invoices (id, client_id, project_id, total, estado_pago, created_at) "
            "VALUES (:id, :clid, :pid, 100.00, 'pendiente', now())"
        ), {"id": str(invoice_id), "clid": client_id, "pid": project_id})
    await db.commit()

    r = await async_client.post(f"{BASE}/{project_id}/invoices/{invoice_id}/send")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sent_at"] is not None
    assert body["estado_pago"] == "pendiente"


@pytest.mark.asyncio
async def test_send_invoice_anulada_409(async_client, db):
    client_id, project_id = await setup_test_project(db)
    invoice_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO invoices (id, client_id, project_id, total, estado_pago, created_at) "
            "VALUES (:id, :clid, :pid, 100.00, 'anulada', now())"
        ), {"id": str(invoice_id), "clid": client_id, "pid": project_id})
    await db.commit()

    r = await async_client.post(f"{BASE}/{project_id}/invoices/{invoice_id}/send")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_send_invoice_unknown_404(async_client, db):
    _, project_id = await setup_test_project(db)
    fake_id = str(uuid.uuid4())
    r = await async_client.post(f"{BASE}/{project_id}/invoices/{fake_id}/send")
    assert r.status_code == 404
