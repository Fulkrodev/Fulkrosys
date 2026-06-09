"""Tests M14 Contracts Engine.

Cubre:
- Templates C-001..C-005
- Ciclo: draft → firmado_marcos → sent → firmado_cliente → vigente
- Integración magic link M12 FIRMA_DOCUMENTO
- Commitments XYZPR
- Hash SHA-256 inmutable
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m14_contracts.contract_service import (
    CONTRACT_TEMPLATES,
    XYZPR_DEFAULTS,
    ContractService,
)
from backend.tests.conftest import _admin_setup, setup_test_project


BASE_CMR = "/api/v1/commercial"
BASE_CTR = "/api/v1/contracts"


# ============ Helpers ============

async def _won_proposal(async_client, db, project_id: str) -> str:
    """COSA 1 (b) · crea la propuesta 'won' por INSERT DIRECTO en DB.

    El endpoint m13 ``/commercial/proposals/generate`` está DORMIDO en Batch 2
    ("RADAR DESACTIVADO · reversible" · radar mid-rebuild en ``radar-v3-rebuild``
    · NO se toca). El INSERT directo mantiene VIVA la cobertura de contratos m14
    sin depender del router dormido ni tocar el linaje radar. ``proposals
    .project_id`` NULL → legible bajo cualquier contexto (RLS project_isolation
    OR null).
    """
    lead_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, estado, created_at) "
            "VALUES (:id, 'Test Client SL', 'calificado', now())"
        ), {"id": str(lead_id)})
        await db.execute(text(
            "INSERT INTO proposals (id, lead_id, version, categoria_objetivo, "
            "importe_total, estado, created_at) "
            "VALUES (:id, :lid, 1, 'MEDIA', 11500, 'won', now())"
        ), {"id": str(proposal_id), "lid": str(lead_id)})
    await db.flush()
    return str(proposal_id)


# ============ Unit tests ============

def test_list_templates_returns_5():
    assert len(CONTRACT_TEMPLATES) == 5
    assert set(CONTRACT_TEMPLATES.keys()) == {"C-001", "C-002", "C-003", "C-004", "C-005"}


def test_xyzpr_defaults_have_5_params():
    # x, y (dos subparams), z, p, r
    assert "x_horas_sponsor_mes" in XYZPR_DEFAULTS
    assert "y_horas_ti_f1" in XYZPR_DEFAULTS
    assert "z_tope_paron_eur" in XYZPR_DEFAULTS
    assert "p_dias_pausa_max" in XYZPR_DEFAULTS
    assert "r_dias_resolucion_max" in XYZPR_DEFAULTS


def test_templates_list_via_service():
    tpls = ContractService.list_templates()
    assert len(tpls) == 5
    assert all("plantilla_id" in t and "nombre" in t for t in tpls)


# ============ API tests ============

@pytest.mark.asyncio
async def test_api_list_templates(async_client):
    r = await async_client.get(f"{BASE_CTR}/templates")
    assert r.status_code == 200
    data = r.json()
    assert len(data["templates"]) == 5


@pytest.mark.asyncio
async def test_generate_contract_requires_won_proposal(async_client, db):
    _, project_id = await setup_test_project(db)
    # COSA 1 (b) · propuesta DRAFT por INSERT directo (router m13 dormido · ver
    # _won_proposal). Generar contrato desde una propuesta no-won debe dar 400.
    lead_id = uuid.uuid4()
    draft_pid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, created_at) "
            "VALUES (:id, 'Draft Client', now())"
        ), {"id": str(lead_id)})
        await db.execute(text(
            "INSERT INTO proposals (id, lead_id, version, categoria_objetivo, "
            "importe_total, estado, created_at) "
            "VALUES (:id, :lid, 1, 'BASICA', 3900, 'draft', now())"
        ), {"id": str(draft_pid), "lid": str(lead_id)})
    await db.flush()

    # Intentar contrato desde draft → 400
    r2 = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/generate",
        json={
            "proposal_id": str(draft_pid),
            "plantilla_id": "C-001",
            "cliente_firmante_nombre": "Alice",
            "cliente_firmante_cargo": "CEO",
        },
    )
    assert r2.status_code == 400
    assert "won" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_contract_from_won_proposal(async_client, db):
    _, project_id = await setup_test_project(db)
    won_pid = await _won_proposal(async_client, db, project_id)

    r = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/generate",
        json={
            "proposal_id": won_pid,
            "plantilla_id": "C-001",
            "cliente_firmante_nombre": "Alice Gomez",
            "cliente_firmante_cargo": "CEO",
            "parametros_xyzpr": {"x_horas_sponsor_mes": 4},
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["estado"] == "draft"
    assert data["plantilla_id"] == "C-001"
    assert data["hash_sha256"] is not None
    assert len(data["hash_sha256"]) == 64
    # XYZPR override merged with defaults
    assert data["parametros_xyzpr"]["x_horas_sponsor_mes"] == 4
    assert data["parametros_xyzpr"]["z_tope_paron_eur"] == 3000


@pytest.mark.asyncio
async def test_sign_marcos_updates_status(async_client, db):
    _, project_id = await setup_test_project(db)
    won_pid = await _won_proposal(async_client, db, project_id)
    r = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/generate",
        json={
            "proposal_id": won_pid,
            "plantilla_id": "C-001",
            "cliente_firmante_nombre": "Bob",
            "cliente_firmante_cargo": "CTO",
        },
    )
    cid = r.json()["id"]
    original_hash = r.json()["hash_sha256"]

    r2 = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/{cid}/sign-marcos"
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["estado"] == "firmado_marcos"
    assert data["firmado_marcos_at"] is not None
    # Hash recomputed on sign (contenido no cambió pero se recalcula)
    assert data["hash_sha256"] == original_hash


@pytest.mark.asyncio
async def test_send_client_creates_magic_link(async_client, db):
    _, project_id = await setup_test_project(db)
    won_pid = await _won_proposal(async_client, db, project_id)
    r = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/generate",
        json={
            "proposal_id": won_pid,
            "plantilla_id": "C-001",
            "cliente_firmante_nombre": "Carla",
            "cliente_firmante_cargo": "CTO",
        },
    )
    cid = r.json()["id"]
    await async_client.post(f"{BASE_CTR}/projects/{project_id}/contracts/{cid}/sign-marcos")

    r3 = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/{cid}/send-client",
        json={"recipient_email": "client@example.com"},
    )
    assert r3.status_code == 200, r3.text
    data = r3.json()
    # #43 · send-client REDIRIGIDO al flujo autoritativo m13 (FIRMA_CONTRATO +
    # canvas): congela documento_sha256, crea el SigningIntent y genera el
    # magic-link con OTP. estado "sent" preservado (equivalencia UI · #7.2).
    assert data["contract"]["estado"] == "sent"
    assert data["contract"]["firmado_cliente_link_id"] is not None
    assert data["magic_link"]["magic_link_id"] is not None
    assert data["magic_link"]["signing_intent_id"] is not None
    assert data["magic_link"]["otp"] is not None  # FIRMA_CONTRATO requires_otp


# #43 · `test_register_client_signature_transitions_to_vigente` ELIMINADO: el
# endpoint register-client-signature (callback timestamp del flujo FIRMA_DOCUMENTO)
# se retiró. La transición a "vigente" ahora ocurre vía canvas Ed25519 en
# ContractSigningFlow.confirm_signing · cubierto por test_contract_signing_canvas
# (SEND→SIGN end-to-end + atomicidad + idempotencia).


@pytest.mark.asyncio
async def test_add_and_list_commitments(async_client, db):
    _, project_id = await setup_test_project(db)
    won_pid = await _won_proposal(async_client, db, project_id)
    r = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/generate",
        json={
            "proposal_id": won_pid,
            "plantilla_id": "C-001",
            "cliente_firmante_nombre": "Ana",
            "cliente_firmante_cargo": "CEO",
        },
    )
    cid = r.json()["id"]

    r2 = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/{cid}/commitments",
        json={
            "tipo": "recurso_sponsor",
            "descripcion": "Sponsor disponible 2h/mes",
            "parametro": "horas_mes",
            "valor_esperado": "2",
        },
    )
    assert r2.status_code == 201, r2.text

    r3 = await async_client.get(
        f"{BASE_CTR}/projects/{project_id}/contracts/{cid}/commitments"
    )
    assert r3.status_code == 200
    assert len(r3.json()["commitments"]) == 1


@pytest.mark.asyncio
async def test_check_commitments_marks_status(async_client, db):
    _, project_id = await setup_test_project(db)
    won_pid = await _won_proposal(async_client, db, project_id)
    r = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/generate",
        json={
            "proposal_id": won_pid,
            "plantilla_id": "C-003",
            "cliente_firmante_nombre": "Ana",
            "cliente_firmante_cargo": "CEO",
        },
    )
    cid = r.json()["id"]

    await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/{cid}/commitments",
        json={"tipo": "plazo_respuesta", "parametro": "dias", "valor_esperado": "5"},
    )

    r3 = await async_client.post(
        f"{BASE_CTR}/projects/{project_id}/contracts/{cid}/check-commitments"
    )
    assert r3.status_code == 200
    results = r3.json()["results"]
    assert len(results) == 1
    # Sin valor_actual → cumplido = None
    assert results[0]["cumplido"] is None
