"""Tests M15 Billing Engine.

Cubre:
- Correlativo fiscal FULKRO-{año}-{NNNN} secuencial
- IVA 21% + IRPF 15% retención
- Verifactu hash chain (encadenado por año)
- Estados: pendiente → pagada / vencida / anulada
- Rectificativas
- Generación desde hito de contrato
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.motors.m15_billing.billing_service import (
    BillingError,
    BillingService,
)
from backend.tests.conftest import _admin_setup, setup_test_project


BASE_CMR = "/api/v1/commercial"
BASE_CTR = "/api/v1/contracts"
BASE = "/api/v1/billing"


# =================== Helpers ===================

async def _setup_tenant(db):
    """setup_test_project + set_tenant_context para tests de service directo."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


async def _create_lead(db) -> str:
    lead_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, created_at) "
            "VALUES (:id, 'Billing Lead', now())"
        ), {"id": str(lead_id)})
    await db.flush()
    return str(lead_id)


async def _generate_plain_invoice(async_client, project_id: str, client_id: str,
                                  precio: float = 1000.0, aplicar_irpf: bool = False):
    return await async_client.post(
        f"{BASE}/projects/{project_id}/invoices/generate",
        json={
            "client_id": client_id,
            "concepto": "Test",
            "lineas": [{"descripcion": "Servicio", "cantidad": 1, "precio_unitario": precio}],
            "aplicar_irpf": aplicar_irpf,
        },
    )


# =================== Service-level ===================

@pytest.mark.asyncio
async def test_generate_invoice_correlative_format(db):
    client_id, project_id = await _setup_tenant(db)
    inv = await BillingService().generate_invoice(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
        contract_id=None,
        concepto="Proyecto Q1",
        lineas=[{"descripcion": "Fase 1", "cantidad": 1, "precio_unitario": 5000}],
    )
    year = date.today().year
    assert inv.numero_correlativo.startswith(f"FULKRO-{year}-")
    # Extraer número y verificar 4 dígitos
    tail = inv.numero_correlativo.rsplit("-", 1)[-1]
    assert len(tail) == 4
    assert tail.isdigit()


@pytest.mark.asyncio
async def test_correlative_sequential_per_tenant(db):
    client_id, project_id = await _setup_tenant(db)
    svc = BillingService()
    inv1 = await svc.generate_invoice(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        contract_id=None, concepto="A",
        lineas=[{"descripcion": "S", "cantidad": 1, "precio_unitario": 100}],
    )
    inv2 = await svc.generate_invoice(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        contract_id=None, concepto="B",
        lineas=[{"descripcion": "S", "cantidad": 1, "precio_unitario": 200}],
    )
    n1 = int(inv1.numero_correlativo.rsplit("-", 1)[-1])
    n2 = int(inv2.numero_correlativo.rsplit("-", 1)[-1])
    assert n2 == n1 + 1


@pytest.mark.asyncio
async def test_iva_21_calculation(db):
    client_id, project_id = await _setup_tenant(db)
    inv = await BillingService().generate_invoice(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        contract_id=None, concepto="Test",
        lineas=[{"descripcion": "X", "cantidad": 1, "precio_unitario": 1000}],
    )
    # base 1000, IVA 21% = 210, total 1210
    assert float(inv.base_imponible) == 1000.0
    assert float(inv.iva_importe) == 210.0
    assert float(inv.total) == 1210.0


@pytest.mark.asyncio
async def test_irpf_retention(db):
    client_id, project_id = await _setup_tenant(db)
    inv = await BillingService().generate_invoice(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        contract_id=None, concepto="Test IRPF",
        lineas=[{"descripcion": "Serv", "cantidad": 1, "precio_unitario": 1000}],
        aplicar_irpf=True,
    )
    # base 1000, IVA 210, IRPF 150 (15%) → total = 1000 + 210 - 150 = 1060
    assert float(inv.irpf_importe) == 150.0
    assert float(inv.total) == 1060.0


@pytest.mark.asyncio
async def test_verifactu_first_of_year_genesis(db):
    client_id, project_id = await _setup_tenant(db)
    inv = await BillingService().generate_invoice(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        contract_id=None, concepto="Genesis",
        lineas=[{"descripcion": "X", "cantidad": 1, "precio_unitario": 100}],
    )
    assert inv.verifactu_hash is not None
    assert len(inv.verifactu_hash) == 64
    assert all(c in "0123456789abcdef" for c in inv.verifactu_hash)


@pytest.mark.asyncio
async def test_verifactu_hash_chain(db):
    client_id, project_id = await _setup_tenant(db)
    svc = BillingService()
    inv1 = await svc.generate_invoice(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        contract_id=None, concepto="#1",
        lineas=[{"descripcion": "A", "cantidad": 1, "precio_unitario": 100}],
    )
    inv2 = await svc.generate_invoice(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        contract_id=None, concepto="#2",
        lineas=[{"descripcion": "B", "cantidad": 1, "precio_unitario": 200}],
    )
    # Hashes distintos — la segunda encadena la anterior
    assert inv1.verifactu_hash != inv2.verifactu_hash


@pytest.mark.asyncio
async def test_mark_paid(db):
    client_id, project_id = await _setup_tenant(db)
    svc = BillingService()
    inv = await svc.generate_invoice(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        contract_id=None, concepto="Pay",
        lineas=[{"descripcion": "X", "cantidad": 1, "precio_unitario": 500}],
    )
    assert inv.estado_pago == "pendiente"
    paid = await svc.mark_paid(db, inv.id)
    assert paid.estado_pago == "pagada"


@pytest.mark.asyncio
async def test_cancel_generates_rectificativa(db):
    client_id, project_id = await _setup_tenant(db)
    svc = BillingService()
    inv = await svc.generate_invoice(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        contract_id=None, concepto="Orig",
        lineas=[{"descripcion": "X", "cantidad": 1, "precio_unitario": 1000}],
    )
    original, rectificativa = await svc.cancel_invoice(db, inv.id)
    assert original.estado_pago == "anulada"
    assert rectificativa.tipo == "rectificativa"
    assert float(rectificativa.total) < 0
    assert rectificativa.numero_correlativo != original.numero_correlativo


@pytest.mark.asyncio
async def test_generate_from_milestone(async_client, db):
    _, project_id = await setup_test_project(db)

    # 1. Proposal "won" sembrada DIRECTAMENTE vía modelo.
    #    RADAR/COMERCIAL DESACTIVADO Batch 2: el endpoint
    #    /api/v1/commercial/proposals/* está dormido. Billing es código que SE
    #    QUEDA y debe seguir verificado → desacoplamos su fixture del router m13
    #    sembrando la Proposal por SQL (modelos intactos · misma sesión `db` que
    #    ve async_client, igual que _create_lead). hitos_pago replica basica_fijo
    #    (total 6500 · anticipo 30% = 1950, que es lo que el test factura/asserta).
    lead_id = await _create_lead(db)
    pid = str(uuid.uuid4())
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO proposals "
            "(id, lead_id, project_id, pricing_model_id, categoria_objetivo, "
            " importe_total, hitos_pago, estado, version, superseded, "
            " created_at, updated_at) "
            "VALUES (:id, :lead, :proj, 'basica_fijo', 'BASICA', 6500, "
            " CAST(:hitos AS jsonb), 'won', 1, false, now(), now())"
        ), {
            "id": pid, "lead": lead_id, "proj": project_id,
            "hitos": (
                '{"hitos": [{"nombre": "anticipo", "importe": 1950.0}, '
                '{"nombre": "final", "importe": 4550.0}]}'
            ),
        })
    await db.flush()

    # 2. Contract
    r2 = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/generate",
        json={
            "proposal_id": pid,
            "plantilla_id": "C-001",
            "cliente_firmante_nombre": "Marcos",
            "cliente_firmante_cargo": "CEO",
        },
    )
    cid = r2.json()["id"]

    # 3. Invoice from milestone "anticipo" (basica_fijo tiene ese hito)
    r3 = await async_client.post(
        f"{BASE}/projects/{project_id}/invoices/from-milestone",
        json={"contract_id": cid, "hito": "anticipo"},
    )
    assert r3.status_code == 201, r3.text
    data = r3.json()
    # basica_fijo: total 6500, anticipo 30% = 1950
    assert float(data["base_imponible"]) == 1950.0


@pytest.mark.asyncio
async def test_generate_reminder_valid_days(db):
    client_id, project_id = await _setup_tenant(db)
    svc = BillingService()
    inv = await svc.generate_invoice(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        contract_id=None, concepto="X",
        lineas=[{"descripcion": "X", "cantidad": 1, "precio_unitario": 100}],
    )
    reminder = await svc.generate_reminder(db, inv.id, 30)
    assert reminder.dias_vencida == 30
    assert reminder.template_usado == "recordatorio_firme"
    with pytest.raises(BillingError):
        await svc.generate_reminder(db, inv.id, 17)


# =================== API ===================

@pytest.mark.asyncio
async def test_api_generate_invoice(async_client, db):
    client_id, project_id = await setup_test_project(db)
    r = await _generate_plain_invoice(async_client, project_id, client_id, precio=2500)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["numero_correlativo"].startswith("FULKRO-")
    assert data["base_imponible"] == 2500
    assert data["iva_importe"] == 525.0
    assert data["total"] == 3025.0
    assert data["estado_pago"] == "pendiente"


@pytest.mark.asyncio
async def test_api_invoice_detail_includes_lineas(async_client, db):
    client_id, project_id = await setup_test_project(db)
    r = await _generate_plain_invoice(async_client, project_id, client_id, precio=100)
    iid = r.json()["id"]

    r2 = await async_client.get(f"{BASE}/projects/{project_id}/invoices/{iid}")
    assert r2.status_code == 200
    data = r2.json()
    assert len(data["lineas"]) == 1
    assert data["lineas"][0]["subtotal"] == 100


@pytest.mark.asyncio
async def test_api_billing_summary(async_client, db):
    client_id, project_id = await setup_test_project(db)
    await _generate_plain_invoice(async_client, project_id, client_id, precio=1000)
    await _generate_plain_invoice(async_client, project_id, client_id, precio=500)

    r = await async_client.get(f"{BASE}/projects/{project_id}/billing/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_invoices"] == 2
    # 2 invoices × 1.21 = 1210 + 605 = 1815 pendiente
    assert data["pendiente"] == 1815.0
    assert data["cobrado"] == 0
