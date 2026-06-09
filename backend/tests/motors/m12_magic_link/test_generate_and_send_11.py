"""#11 · botón manual: generar magic link + ENVIAR por email en un paso.

Hasta #11 la plataforma generaba el enlace + renderizaba el email pero Marcos lo
enviaba a mano. El endpoint /generate-and-send dispara el envío real vía
EmailSender (mock en test · captura in-memory). Verifica: 201 + enlace generado +
email_sent True + email capturado al destinatario. El token plano sólo existe al
generar, por eso el envío ocurre aquí (no como reenvío por id).
"""
from __future__ import annotations

import pytest

from backend.app.core.email.sender import (
    get_captured_emails,
    reset_captured_emails,
    reset_email_sender,
)
from backend.tests.conftest import setup_test_project

BASE = "/api/v1/magic-links"


@pytest.mark.asyncio
async def test_generate_and_send_emits_email_mock(async_client, db):
    reset_email_sender()  # re-lee settings.email_backend (mock por defecto)
    reset_captured_emails()
    _, project_id = await setup_test_project(db)

    r = await async_client.post(
        f"{BASE}/generate-and-send",
        json={
            "project_id": project_id,
            "purpose": "portal_remediacion",
            "recipient_email": "cliente11@example.com",
            "max_uses": 3,
            "ttl_hours": 168,
        },
    )
    assert r.status_code == 201, f"{r.status_code} {r.text}"
    data = r.json()

    # enlace realmente generado
    assert data["magic_link_id"]
    assert data["url"].startswith("http")
    assert data["purpose"] == "portal_remediacion"

    # email enviado (backend mock) + sin error
    assert data["email_sent"] is True, data
    assert data["email_backend"] == "mock"
    assert data["email_error"] is None
    assert data["recipient_email"] == "cliente11@example.com"

    # capturado in-memory por el backend mock
    captured = get_captured_emails(to="cliente11@example.com")
    assert len(captured) >= 1
    assert captured[-1]["subject"]
    assert len(captured[-1]["html_body"]) > 0


@pytest.mark.asyncio
async def test_otp_never_embedded_in_link_email(async_client, db):
    """#11 HIGH fix · para purposes con OTP, el OTP se devuelve en la response
    (relay canal aparte) pero NUNCA viaja en el email del enlace (no anula 2FA)."""
    reset_email_sender()
    reset_captured_emails()
    _, project_id = await setup_test_project(db)

    r = await async_client.post(
        f"{BASE}/generate-and-send",
        json={
            "project_id": project_id,
            "purpose": "firma_documento",  # requires_otp=True
            "recipient_email": "firmante11@example.com",
        },
    )
    assert r.status_code == 201, f"{r.status_code} {r.text}"
    data = r.json()
    # OTP presente en la response (para canal separado)
    assert data["otp"] is not None
    assert len(data["otp"]) == 6 and data["otp"].isdigit()
    assert data["email_sent"] is True

    # CRÍTICO: el OTP NO aparece en el email del enlace
    cap = get_captured_emails(to="firmante11@example.com")
    assert len(cap) >= 1
    html = cap[-1]["html_body"]
    assert data["otp"] not in html, "OTP filtrado en el email del enlace"
    # coherencia de copy: el email NO promete un código embebido que ya no existe
    assert "al final de este mensaje" not in html
    assert "código de un solo uso adjunto" not in html


@pytest.mark.asyncio
async def test_cc_emails_delivered(async_client, db):
    """#11 LOW fix · cc_emails se entrega de verdad (antes se persistía sin enviar)."""
    reset_email_sender()
    reset_captured_emails()
    _, project_id = await setup_test_project(db)

    r = await async_client.post(
        f"{BASE}/generate-and-send",
        json={
            "project_id": project_id,
            "purpose": "portal_remediacion",
            "recipient_email": "cli11@example.com",
            "cc_emails": ["legal11@example.com", "compras11@example.com"],
            "max_uses": 3,
            "ttl_hours": 168,
        },
    )
    assert r.status_code == 201, f"{r.status_code} {r.text}"
    cap = get_captured_emails(to="cli11@example.com")
    assert len(cap) >= 1
    assert "legal11@example.com" in cap[-1]["cc"]
    assert "compras11@example.com" in cap[-1]["cc"]


@pytest.mark.asyncio
async def test_generate_and_send_nonexistent_project_404(async_client, db):
    import uuid

    r = await async_client.post(
        f"{BASE}/generate-and-send",
        json={
            "project_id": str(uuid.uuid4()),
            "purpose": "portal_remediacion",
            "recipient_email": "x@example.com",
        },
    )
    assert r.status_code == 404
