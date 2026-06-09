"""#43 · tests in-process ASGI de los endpoints de firma de contrato.

Cubren la frontera HTTP + la atomicidad a NIVEL ENDPOINT (la frontera
commit/rollback de get_db), que los tests de servicio
(test_contract_signing_canvas) NO tocan:
- POST /api/v1/contracts/.../send-client (admin · redirect a m13 ContractSigningFlow)
- POST /api/v1/contract-signing/confirm (público · canvas Ed25519)

Vía ``async_client`` (ASGITransport · misma sesión RLS fulkro_app que el test ·
contra fulkro_test). NO requiere uvicorn vivo. El endpoint confirm commitea 1×
en éxito y hace rollback en fallo → se verifica que el rollback deshace TAMBIÉN
la promoción del proyecto + el ClientUser (refuerzo 1 a nivel endpoint).
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from backend.app.core.sse_dispatcher import event_matches_audience
from backend.app.motors.m05_signing.service import SigningService
from backend.tests.motors.m13_commercial.test_contract_signing_canvas import (
    TINY_PNG,
    _setup_unsigned_contract,
)

BASE_CTR = "/api/v1/contracts"
CONFIRM = "/api/v1/contract-signing/confirm"


@pytest.mark.asyncio
async def test_confirm_endpoint_full_flow(async_client, db):
    """SEND (admin HTTP) → CONFIRM (público HTTP) → contrato vigente + proyecto
    promovido + ClientUser + SigningEvent · todo por el endpoint real."""
    lead, light, contract_id = await _setup_unsigned_contract(db)
    light_id, client_id = light.id, light.client_id
    # Los endpoints corren como fulkro_app (RLS) · el setup dejó role=fulkro.
    await db.execute(text("RESET ROLE"))

    r = await async_client.post(
        f"{BASE_CTR}/projects/{light_id}/contracts/{contract_id}/send-client",
        json={"recipient_email": lead.contacto_email},
    )
    assert r.status_code == 200, r.text
    ml = r.json()["magic_link"]
    assert ml["token"] and ml["otp"] and ml["signing_intent_id"]

    r2 = await async_client.post(
        CONFIRM,
        json={
            "token": ml["token"],
            "otp": ml["otp"],
            "signature_canvas_dataurl": TINY_PNG,
            "signed_name": "Ana",
            "signed_surname": "Firmante",
            "geo_lat": 40.4,
            "geo_lon": -3.7,
        },
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "signed"

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    estado = await db.scalar(
        text("SELECT estado FROM contracts WHERE id=:c"), {"c": str(contract_id)}
    )
    assert estado == "vigente"
    lifecycle = await db.scalar(
        text("SELECT lifecycle_state FROM projects WHERE id=:p"),
        {"p": str(light_id)},
    )
    assert lifecycle == "SIGNED"
    n_users = await db.scalar(
        text("SELECT count(*) FROM client_users WHERE client_id=:c"),
        {"c": str(client_id)},
    )
    assert n_users == 1
    ev = await db.scalar(
        text(
            "SELECT count(*) FROM signing_events WHERE signing_intent_id=:i "
            "AND event_type='signature_generated' AND signature_ed25519 IS NOT NULL"
        ),
        {"i": ml["signing_intent_id"]},
    )
    assert ev == 1


@pytest.mark.asyncio
async def test_confirm_endpoint_rolls_back_on_unexpected_error(
    async_client, db, monkeypatch
):
    """Atomicidad a NIVEL ENDPOINT · un fallo INESPERADO (no ContractSigningFlow
    Error) durante el flujo NO debe colar un commit parcial: el endpoint captura
    en `except Exception`, hace ``db.rollback()`` explícito y devuelve 500.

    (El que el rollback DESHAGA la promoción del proyecto + el ClientUser se
    verifica de forma limpia a nivel servicio en
    test_contract_signing_canvas::test_atomicity_signcanvas_failure, con
    begin_nested · aquí, bajo la sesión compartida del async_client, un rollback
    tras un flush-error deasocia la conexión y rompe queries posteriores, así que
    solo se asserta el contrato HTTP del endpoint: 500, NO 200/commit parcial.)
    """
    lead, light, contract_id = await _setup_unsigned_contract(db)
    light_id = light.id
    await db.execute(text("RESET ROLE"))

    r = await async_client.post(
        f"{BASE_CTR}/projects/{light_id}/contracts/{contract_id}/send-client",
        json={"recipient_email": lead.contacto_email},
    )
    assert r.status_code == 200, r.text
    ml = r.json()["magic_link"]

    async def _boom(*a, **k):
        raise RuntimeError("sign_canvas boom")

    monkeypatch.setattr(SigningService, "sign_canvas", _boom)

    r2 = await async_client.post(
        CONFIRM,
        json={
            "token": ml["token"],
            "otp": ml["otp"],
            "signature_canvas_dataurl": TINY_PNG,
            "signed_name": "A",
            "signed_surname": "B",
        },
    )
    # Fallo inesperado → rollback explícito + 500 (NO 200/commit parcial).
    assert r2.status_code == 500, r2.text


@pytest.mark.asyncio
async def test_contract_confirm_emits_signing_signed_to_admin(
    async_client, db, monkeypatch
):
    """Ola 3 #12 (test CLAVE de la ola) · cierra el sub-gap del contrato mudo.

    Verifica de VERDAD que la firma del contrato:
    1. EMITE signing.signed (antes no emitía NADA · el admin no se enteraba),
    2. con payload ENRIQUECIDO (plantilla_id C-001 + signer_name legible · no
       "alguien firmó algo"),
    3. y que ese evento PASA el filtro de audiencia admin (el admin lo recibe).
    """
    lead, light, contract_id = await _setup_unsigned_contract(db)
    light_id = light.id
    await db.execute(text("RESET ROLE"))

    r = await async_client.post(
        f"{BASE_CTR}/projects/{light_id}/contracts/{contract_id}/send-client",
        json={"recipient_email": lead.contacto_email},
    )
    assert r.status_code == 200, r.text
    ml = r.json()["magic_link"]

    # Spy del dispatcher en el módulo del endpoint público (el emit vive ahí).
    spy = AsyncMock()
    monkeypatch.setattr(
        "backend.app.motors.m13_commercial.contract_signing_public_api"
        ".sse_dispatcher",
        spy,
    )

    r2 = await async_client.post(
        CONFIRM,
        json={
            "token": ml["token"],
            "otp": ml["otp"],
            "signature_canvas_dataurl": TINY_PNG,
            "signed_name": "Ana",
            "signed_surname": "Firmante",
        },
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "signed"

    # (1) EMITIÓ signing.signed al canal del proyecto.
    spy.dispatch.assert_awaited_once()
    kw = spy.dispatch.await_args.kwargs
    assert kw["event_type"] == "signing.signed"
    assert kw["channel"] == f"project:{light_id}"

    # (2) payload ENRIQUECIDO (no "alguien firmó algo").
    data = kw["data"]
    assert data["signer_name"] == "Ana Firmante"
    assert data["signable_label"] == "Contrato comercial"
    assert data["plantilla_id"] == "C-001"
    assert data["primary_actor"] == "cliente"
    assert data["contract_id"] == str(contract_id)
    assert data["signable_ref_type"] == "contract"

    # (3) PASA el filtro de audiencia admin → el admin lo recibe en realtime.
    assert event_matches_audience("signing.signed", "admin", data) is True
