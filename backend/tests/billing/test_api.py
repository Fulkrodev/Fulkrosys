"""Tests API endpoints AutoBilling + reconciliation (MB-18.3 ADR-040)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from backend.app.auth.crypto import hash_password
from backend.app.billing.milestone_factory import MilestoneFactory
from backend.app.models.billing_milestones import ContractMilestone
from backend.app.models.client_portal import ClientUser
from backend.tests.conftest import _admin_setup


async def _bootstrap_admin_data(db) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    contract_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'API Test', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, "
                "created_at) "
                "VALUES (:id, :cid, 'P-API', 'adecuacion', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
        await db.execute(
            text(
                "INSERT INTO contracts (id, project_id, estado, "
                "parametros_xyzpr, created_at) "
                "VALUES (:id, :pid, 'firmado', "
                "'{\"pricing\": {\"categoria\": \"BASICA\", "
                "\"total\": 3000}}'::jsonb, now())"
            ),
            {"id": str(contract_id), "pid": str(project_id)},
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    return client_id, project_id, contract_id


async def _make_client_with_user(db) -> ClientUser:
    """Crea Client + ClientUser sintéticos para tests API cliente."""
    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'API-Cli', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        user = ClientUser(
            client_id=client_id,
            email=f"api-cli-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestP@ssw0rd123!"),
            full_name="Cliente API",
            must_change_password=False,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    return user


@pytest.fixture
async def client_user_authed(async_client, db):
    user = await _make_client_with_user(db)
    from backend.app.main import app
    from backend.app.auth.dependencies import require_client_user

    async def override():
        return user

    app.dependency_overrides[require_client_user] = override
    yield async_client, user
    app.dependency_overrides.pop(require_client_user, None)


@pytest.mark.asyncio
async def test_admin_finance_kpis_endpoint(async_client):
    response = await async_client.get("/api/v1/admin/finance/kpis")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "billed_this_month_eur" in data
    assert "paid_this_month_eur" in data
    assert "pending_total_eur" in data
    assert "overdue_count" in data


@pytest.mark.asyncio
async def test_admin_pending_payments_lists_invoice_issued(async_client, db):
    _, project_id, contract_id = await _bootstrap_admin_data(db)
    factory = MilestoneFactory(db)
    await factory.create_milestones_for_contract(
        contract_id=contract_id,
        project_id=project_id,
        categoria="BASICA",
        contract_total=Decimal("3000"),
    )
    rows = await db.execute(
        text(
            "UPDATE contract_milestones SET status = 'invoice_issued', "
            "billed_at = NOW() WHERE contract_id = :cid"
        ),
        {"cid": str(contract_id)},
    )
    await db.flush()

    response = await async_client.get(
        "/api/v1/admin/finance/pending-payments"
    )
    assert response.status_code == 200, response.text
    items = response.json()
    matching = [
        i for i in items if i["project_id"] == str(project_id)
    ]
    assert len(matching) == 3
    assert all("amount_eur" in i for i in matching)


@pytest.mark.asyncio
async def test_admin_mark_paid_endpoint(async_client, db):
    _, project_id, contract_id = await _bootstrap_admin_data(db)
    m = ContractMilestone(
        contract_id=contract_id,
        project_id=project_id,
        milestone_index=0,
        milestone_name="hito_test_paid",
        workflow_phase_index=4,
        amount_eur=Decimal("500"),
        percent_of_total=Decimal("17"),
        status="invoice_issued",
        billed_at=datetime.now(timezone.utc),
        blocking_next_phase=True,
    )
    db.add(m)
    await db.flush()
    await db.refresh(m)

    response = await async_client.post(
        f"/api/v1/admin/finance/milestones/{m.id}/mark-paid",
        json={
            "payment_reference": "REF-API-TEST",
            "payment_notes": "Test API",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "paid"
    assert data["payment_reference"] == "REF-API-TEST"
    assert data["workflow_advanced_to_phase"] == 5


@pytest.mark.asyncio
async def test_admin_mark_paid_not_found_returns_404(async_client):
    response = await async_client.post(
        f"/api/v1/admin/finance/milestones/{uuid.uuid4()}/mark-paid",
        json={},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_mark_paid_invalid_iso_400(async_client, db):
    _, project_id, contract_id = await _bootstrap_admin_data(db)
    m = ContractMilestone(
        contract_id=contract_id,
        project_id=project_id,
        milestone_index=0,
        milestone_name="x",
        workflow_phase_index=4,
        amount_eur=Decimal("100"),
        percent_of_total=Decimal("10"),
        status="invoice_issued",
    )
    db.add(m)
    await db.flush()
    await db.refresh(m)

    response = await async_client.post(
        f"/api/v1/admin/finance/milestones/{m.id}/mark-paid",
        json={"paid_at": "not-iso"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_regenerate_milestones(async_client, db):
    _, project_id, contract_id = await _bootstrap_admin_data(db)
    response = await async_client.post(
        f"/api/v1/admin/contracts/{contract_id}/milestones/regenerate"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["created"] == 3
    assert data["skipped"] == 0

    # Idempotente
    response2 = await async_client.post(
        f"/api/v1/admin/contracts/{contract_id}/milestones/regenerate"
    )
    data2 = response2.json()
    assert data2["created"] == 0
    assert data2["skipped"] == 3


@pytest.mark.asyncio
async def test_admin_regenerate_contract_not_found_404(async_client):
    response = await async_client.post(
        f"/api/v1/admin/contracts/{uuid.uuid4()}/milestones/regenerate"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_regenerate_contract_no_pricing_400(async_client, db):
    project_id = uuid.uuid4()
    contract_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'NoPricing', :cif, now())"
            ),
            {"id": str(uuid.uuid4()), "cif": cif},
        )
        cif2 = f"B{uuid.uuid4().hex[:8].upper()}"
        cid2 = uuid.uuid4()
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'X2', :cif, now())"
            ),
            {"id": str(cid2), "cif": cif2},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P-NoP', now())"
            ),
            {"id": str(project_id), "cid": str(cid2)},
        )
        await db.execute(
            text(
                "INSERT INTO contracts (id, project_id, estado, created_at) "
                "VALUES (:id, :pid, 'draft', now())"
            ),
            {"id": str(contract_id), "pid": str(project_id)},
        )
    response = await async_client.post(
        f"/api/v1/admin/contracts/{contract_id}/milestones/regenerate"
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_client_billing_invoices_lists_own(client_user_authed, db):
    client, user = client_user_authed
    invoice_id = uuid.uuid4()
    project_id = uuid.uuid4()
    contract_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P-Bill', now())"
            ),
            {"id": str(project_id), "cid": str(user.client_id)},
        )
        await db.execute(
            text(
                "INSERT INTO contracts (id, project_id, estado, created_at) "
                "VALUES (:id, :pid, 'firmado', now())"
            ),
            {"id": str(contract_id), "pid": str(project_id)},
        )
        await db.execute(
            text(
                "INSERT INTO invoices (id, client_id, project_id, "
                "contract_id, numero_correlativo, total, "
                "estado_pago, concepto, fecha_emision, created_at) "
                "VALUES (:iid, :cid, :pid, :coid, "
                "'FACT-API-001', 1500, 'pendiente', "
                "'Hito Test', NOW(), now())"
            ),
            {
                "iid": str(invoice_id),
                "cid": str(user.client_id),
                "pid": str(project_id),
                "coid": str(contract_id),
            },
        )

    response = await client.get("/api/v1/portal/billing/invoices")
    assert response.status_code == 200, response.text
    items = response.json()
    matching = [i for i in items if i["invoice_id"] == str(invoice_id)]
    assert len(matching) == 1
    inv = matching[0]
    assert inv["invoice_number"] == "FACT-API-001"
    assert inv["estado_pago"] == "pendiente"


@pytest.mark.asyncio
async def test_client_billing_invoices_iban_info_mode(
    client_user_authed, db, monkeypatch,
):
    """Pending invoice incluye bloque IBAN info-mode · NO link · NO clipboard."""
    client, user = client_user_authed
    monkeypatch.setenv("MARCOS_BANK_IBAN", "ES1212345678901234567890")
    from backend.app.config import get_settings
    get_settings.cache_clear()

    invoice_id = uuid.uuid4()
    project_id = uuid.uuid4()
    contract_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P-IBAN', now())"
            ),
            {"id": str(project_id), "cid": str(user.client_id)},
        )
        await db.execute(
            text(
                "INSERT INTO contracts (id, project_id, estado, created_at) "
                "VALUES (:id, :pid, 'firmado', now())"
            ),
            {"id": str(contract_id), "pid": str(project_id)},
        )
        await db.execute(
            text(
                "INSERT INTO invoices (id, client_id, project_id, "
                "contract_id, numero_correlativo, total, "
                "estado_pago, fecha_emision, created_at) "
                "VALUES (:iid, :cid, :pid, :coid, 'FACT-IBAN-001', "
                "750, 'pendiente', NOW(), now())"
            ),
            {
                "iid": str(invoice_id),
                "cid": str(user.client_id),
                "pid": str(project_id),
                "coid": str(contract_id),
            },
        )

    response = await client.get("/api/v1/portal/billing/invoices")
    assert response.status_code == 200
    items = response.json()
    pending = next(i for i in items if i["invoice_id"] == str(invoice_id))
    assert pending["bank_instructions_html"]
    assert "ES12 1234 5678 9012 3456 7890" in pending["bank_instructions_html"]
    # Directiva: NO link · NO clipboard · NO botón
    assert "<a " not in pending["bank_instructions_html"]
    assert "clipboard" not in pending["bank_instructions_html"]
    assert "onclick=" not in pending["bank_instructions_html"]
    assert "FACT-IBAN-001" in pending["bank_instructions_text"]
    get_settings.cache_clear()


# ──────────── #45 · vista implementación × pagos (endpoints HTTP) ────────────


@pytest.mark.asyncio
async def test_admin_implementation_payments_endpoint(async_client, db):
    """#45 admin · cruza fases × hitos de cobro (detalle completo)."""
    _, project_id, contract_id = await _bootstrap_admin_data(db)
    await MilestoneFactory(db).create_milestones_for_contract(
        contract_id=contract_id,
        project_id=project_id,
        categoria="BASICA",
        contract_total=Decimal("3000"),
    )
    await db.flush()

    response = await async_client.get(
        f"/api/v1/admin/finance/projects/{project_id}/implementation-payments"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["found"] is True
    assert data["project_id"] == str(project_id)
    assert len(data["milestones"]) >= 1
    m0 = data["milestones"][0]
    # campos del cruce presentes
    for key in ("phase_label", "payment_state", "phase_reached", "is_overdue",
                "amount_with_vat_eur", "scheduled_date"):
        assert key in m0, f"falta {key} en milestone"
    assert m0["payment_state"] in ("paid", "due", "upcoming")
    # totales coherentes
    t = data["totals"]
    assert Decimal(t["total_eur"]) == Decimal(t["paid_eur"]) + Decimal(t["pending_eur"])


@pytest.mark.asyncio
async def test_client_implementation_payments_endpoint(client_user_authed, db):
    """#45 cliente · resumen amable (R29) de hitos y pagos del propio proyecto."""
    client, user = client_user_authed
    project_id = uuid.uuid4()
    contract_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:id, :cid, 'P-45-CLI', 'implantacion', now())"
            ),
            {"id": str(project_id), "cid": str(user.client_id)},
        )
        await db.execute(
            text(
                "INSERT INTO contracts (id, project_id, estado, created_at) "
                "VALUES (:id, :pid, 'firmado', now())"
            ),
            {"id": str(contract_id), "pid": str(project_id)},
        )
    # RLS contract_milestones es por current_project_id · fijarlo antes del factory
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await MilestoneFactory(db).create_milestones_for_contract(
        contract_id=contract_id,
        project_id=project_id,
        categoria="BASICA",
        contract_total=Decimal("3000"),
    )
    await db.flush()

    response = await client.get(
        "/api/v1/portal/billing/implementation-payments"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["project_name"]
    assert len(data["hitos"]) >= 1
    h0 = data["hitos"][0]
    # forma friendly (sin códigos internos · estado en español)
    for key in ("concepto", "fase", "importe_eur", "estado", "payment_state"):
        assert key in h0, f"falta {key} en hito cliente"
    assert h0["estado"] in ("Pagado", "Pendiente de pago", "Próximo")
    assert "milestone_index" not in h0  # nada de jerga interna
